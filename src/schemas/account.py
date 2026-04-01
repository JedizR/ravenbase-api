# src/schemas/account.py
from pydantic import BaseModel


class AccountDeleteResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = (
        "Account deletion queued. All data will be permanently removed within 60 seconds."
    )


class ModelPreferenceUpdate(BaseModel):
    preferred_model: str


class NotificationPreferencesUpdate(BaseModel):
    notify_welcome: bool | None = None
    notify_low_credits: bool | None = None
    notify_ingestion_complete: bool | None = None
