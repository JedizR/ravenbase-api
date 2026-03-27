# tests/unit/test_user_model_id_type.py
from src.models.user import User


def test_user_id_accepts_clerk_string():
    """User.id must accept Clerk-format string IDs, not just UUIDs."""
    user = User(id="user_2vKdE5KqDemoClerkId", email="test@example.com")
    assert user.id == "user_2vKdE5KqDemoClerkId"
