import pytest

from universal_framework.observability.unified_logger import UniversalFrameworkLogger


@pytest.fixture
def universal_logger():
    return UniversalFrameworkLogger("test_component")


def test_agent_execution_logging(universal_logger, caplog):
    caplog.set_level("INFO")
    universal_logger.log_agent_execution(
        agent_name="test_agent",
        session_id="test_session_123",
        execution_context={"execution_time_ms": 150.5, "workflow_phase": "discovery"},
        success=True,
    )
    messages = [record.message for record in caplog.records]
    assert any("agent_execution" in m for m in messages)


def test_compliance_event_logging(universal_logger, caplog):
    caplog.set_level("INFO")
    universal_logger.log_compliance_event(
        event_type="data_access",
        event_data={"user_id": "user123", "resource": "sensitive_data"},
        session_id="test_session_123",
        privacy_level="enterprise_audit",
    )
    messages = [record.message for record in caplog.records]
    assert any("compliance_event" in m for m in messages)
