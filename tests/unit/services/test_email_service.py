# tests/unit/services/test_email_service.py
from unittest.mock import MagicMock, patch
import pytest
from src.services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_warning_calls_resend(mocker):
    mocker.patch("src.services.email_service.settings", RESEND_API_KEY="re_test_key")
    mock_resend = MagicMock()
    mock_resend.Emails.send = MagicMock(return_value={"id": "email_123"})

    with patch.dict("sys.modules", {"resend": mock_resend}):
        result = await EmailService().send_account_deletion_warning(
            to_email="alice@example.com",
            display_name="Alice",
            user_id="user_abc",
        )

    assert result is True
    call_args = mock_resend.Emails.send.call_args[0][0]
    assert call_args["to"] == ["alice@example.com"]
    assert "30 days" in call_args["text"]
    assert "Alice" in call_args["text"]


@pytest.mark.asyncio
async def test_send_warning_returns_false_on_failure(mocker):
    mocker.patch("src.services.email_service.settings", RESEND_API_KEY="re_test_key")
    mock_resend = MagicMock()
    mock_resend.Emails.send = MagicMock(side_effect=Exception("rate limit"))

    with patch.dict("sys.modules", {"resend": mock_resend}):
        result = await EmailService().send_account_deletion_warning(
            to_email="bob@example.com",
            display_name=None,
            user_id="user_bbb",
        )

    assert result is False


@pytest.mark.asyncio
async def test_send_warning_uses_email_prefix_when_no_display_name(mocker):
    mocker.patch("src.services.email_service.settings", RESEND_API_KEY="re_test_key")
    mock_resend = MagicMock()
    mock_resend.Emails.send = MagicMock(return_value={"id": "email_456"})

    with patch.dict("sys.modules", {"resend": mock_resend}):
        await EmailService().send_account_deletion_warning(
            to_email="charlie@example.com",
            display_name=None,
            user_id="user_ccc",
        )

    text = mock_resend.Emails.send.call_args[0][0]["text"]
    assert "charlie" in text
