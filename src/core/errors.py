from fastapi import HTTPException


class ErrorCode:
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    INGESTION_FAILED = "INGESTION_FAILED"
    CONFLICT_NOT_FOUND = "CONFLICT_NOT_FOUND"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    MISSING_AUTH = "MISSING_AUTH"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"


def raise_404(code: str, detail: str) -> None:
    raise HTTPException(status_code=404, detail={"code": code, "message": detail})


def raise_422(code: str, detail: str) -> None:
    raise HTTPException(status_code=422, detail={"code": code, "message": detail})


def raise_429(code: str, detail: str) -> None:
    raise HTTPException(status_code=429, detail={"code": code, "message": detail})
