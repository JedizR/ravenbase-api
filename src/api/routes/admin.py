# src/api/routes/admin.py
from fastapi import APIRouter

from src.api.dependencies.admin import require_admin  # noqa: F401 — imported for dependency_overrides

router = APIRouter(prefix="/v1/admin", tags=["admin"])
