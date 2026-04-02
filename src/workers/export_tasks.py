# src/workers/export_tasks.py
"""ARQ task for data export — generate_user_export."""

from __future__ import annotations

import json as json_lib

import structlog

from src.api.dependencies.db import async_session_factory
from src.services.export_service import ExportService

logger = structlog.get_logger()


async def generate_user_export(
    ctx: dict,  # type: ignore[type-arg]
    *,
    user_id: str,
    format: str,
) -> dict:  # type: ignore[type-arg]
    """ARQ task: package and export all user data.

    AC-1: Enqueued via POST /v1/account/export (returns 202)
    AC-2: Rate limit checked in route handler before enqueuing
    AC-3: Collects from Postgres, Neo4j, Storage
    AC-4: ZIP uploaded to exports/{user_id}/{timestamp}.zip
    AC-5: Pre-signed URL generated with 72-hour expiry
    AC-6: Completion email sent via EmailService
    AC-9: Partial failures produce PARTIAL_EXPORT.txt (job does NOT fail)
    """
    log = logger.bind(user_id=user_id, format=format, job="generate_user_export")
    log.info("export_task.started")

    try:
        async with async_session_factory() as session:
            export_svc = ExportService()
            result = await export_svc.export_for_user(
                db=session,
                user_id=user_id,
                export_format=format,
            )

        # Update JobStatus with result
        async with async_session_factory() as session:
            from sqlmodel import select  # noqa: PLC0415

            from src.models.job_status import JobStatus  # noqa: PLC0415

            job_id = ctx.get("job_id", f"export:{user_id}")
            result_db = await session.exec(
                select(JobStatus).where(
                    JobStatus.user_id == user_id,
                    JobStatus.id == job_id,
                )
            )
            job_status = result_db.first()
            if job_status:
                job_status.status = result["status"]
                job_status.message = json_lib.dumps(
                    {
                        "download_url": result.get("download_url"),
                        "progress": result.get("progress", 0),
                        "error": result.get("error"),
                    }
                )
                session.add(job_status)
                await session.commit()

        # Send completion email (AC-6)
        if result["status"] == "ready" and result.get("download_url"):
            try:
                from src.models.user import User  # noqa: PLC0415
                from src.services.email_service import EmailService  # noqa: PLC0415

                email_svc = EmailService()
                async with async_session_factory() as session:
                    user = await session.get(User, user_id)
                    if user and user.notify_ingestion_complete:
                        await email_svc.send_export_complete(
                            email=user.email,
                            download_url=result["download_url"],
                        )
                        log.info("export_task.email_sent", user_id=user_id)
            except Exception as email_exc:
                log.warning("export_task.email_failed", error=str(email_exc))
                # Non-fatal — export is still complete

        # Set rate limit key (24h TTL) — AC-2
        try:
            redis = ctx["redis"]
            cooldown_key = f"export:cooldown:{user_id}"
            await redis.set(cooldown_key, "1", ex=86400)  # 24h
            log.info("export_task.rate_limit_set", user_id=user_id)
        except Exception as redis_exc:
            log.warning("export_task.redis_set_failed", error=str(redis_exc))

        log.info("export_task.completed", status=result["status"])
        return result

    except Exception as exc:
        log.error("export_task.failed", error=str(exc), exc_info=True)
        return {"status": "failed", "error": str(exc)}
