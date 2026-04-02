# src/schemas/export.py
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"


class ExportRequest(BaseModel):
    format: ExportFormat = ExportFormat.ZIP


class ExportQueuedResponse(BaseModel):
    job_id: str
    status: str = "queued"


class ExportStatusResponse(BaseModel):
    status: str  # idle | queued | preparing | ready | failed
    job_id: str
    download_url: str | None = None
    progress: int = 0  # 0-100
    error: str | None = None
