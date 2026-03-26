# Re-export all SQLModel table classes.
# These imports also register each table's metadata with SQLModel.metadata,
# which is required for Alembic autogenerate to detect all tables.

from src.models.conflict import Conflict, ConflictStatus
from src.models.credit import CreditTransaction
from src.models.job_status import JobStatus
from src.models.meta_document import MetaDocument
from src.models.profile import SystemProfile
from src.models.source import Source, SourceAuthorityWeight, SourceStatus
from src.models.user import User

__all__ = [
    "User",
    "SystemProfile",
    "Source",
    "SourceAuthorityWeight",
    "SourceStatus",
    "Conflict",
    "ConflictStatus",
    "MetaDocument",
    "CreditTransaction",
    "JobStatus",
]
