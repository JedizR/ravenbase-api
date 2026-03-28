# src/schemas/account.py
from pydantic import BaseModel


class AccountDeleteResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = (
        "Account deletion queued. All data will be permanently removed within 60 seconds."
    )
