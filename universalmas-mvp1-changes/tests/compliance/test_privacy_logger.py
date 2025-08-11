from universal_framework.compliance import PrivacySafeLogger


def test_privacy_safe_session_logging(caplog):
    caplog.set_level("INFO")
    logger = PrivacySafeLogger()
    metadata = {
        "user_email": "john.doe@example.com",
        "phone": "555-123-4567",
        "message": "Please help with my account",
    }

    logger.log_session_event("session_123", "user_message", metadata)

    captured = "".join(record.message for record in caplog.records)
    assert "[EMAIL_REDACTED]" in captured
    assert "[PHONE_REDACTED]" in captured
    assert "session_hash_" in captured
    assert "john.doe@example.com" not in captured
