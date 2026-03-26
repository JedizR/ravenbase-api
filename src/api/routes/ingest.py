from fastapi import APIRouter, Depends, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.ingest import UploadResponse
from src.services.ingestion_service import IngestionService

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_file(
    request: Request,
    file: UploadFile,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadResponse:
    """Enqueue a file for background ingestion. Returns job_id immediately."""
    content = await file.read()
    svc = IngestionService()
    return await svc.handle_upload(
        content=content,
        filename=file.filename or "upload",
        tenant_id=user["user_id"],
        tier=user.get("tier", "free"),
        arq_pool=request.app.state.arq_pool,
        db=db,
    )
