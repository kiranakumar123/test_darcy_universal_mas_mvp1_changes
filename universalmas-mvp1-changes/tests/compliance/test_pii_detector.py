from universal_framework.compliance import PIIDetector, RedactionConfig


def test_nested_metadata_redaction():
    detector = PIIDetector(RedactionConfig())
    complex_metadata = {
        "user_profile": {
            "contact": {
                "email": "admin@company.com",
                "backup_emails": ["user1@test.com", "user2@test.com"],
            },
            "preferences": {"notification_phone": "555-987-6543"},
        }
    }
    redacted = detector.redact_metadata(complex_metadata)
    redacted_str = str(redacted)
    assert "[EMAIL_REDACTED]" in redacted_str
    assert "[PHONE_REDACTED]" in redacted_str
    assert "admin@company.com" not in redacted_str


def test_hash_salt_rotation(monkeypatch):
    detector = PIIDetector(RedactionConfig(hash_salt_rotation_hours=0))
    first = detector.hash_session_id("session_123")
    # force rotation by modifying time
    detector.salt_rotation_time = detector.salt_rotation_time.replace(
        hour=detector.salt_rotation_time.hour - 1
    )
    second = detector.hash_session_id("session_123")
    assert first != second
