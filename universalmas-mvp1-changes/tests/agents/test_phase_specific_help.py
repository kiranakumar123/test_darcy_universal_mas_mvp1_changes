"""Tests for phase-specific help functionality in IntentClassifier."""

from universal_framework.agents.intent_classifier import IntentClassifier
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase


class TestPhaseSpecificHelp:
    """Test suite for phase-specific help functionality."""

    def test_help_adapts_to_workflow_phase(self):
        """Test that help content changes based on workflow phase."""
        classifier = IntentClassifier()

        # Test initialization phase
        init_state = UniversalWorkflowState(
            workflow_phase=WorkflowPhase.INITIALIZATION,
            session_id="test_123",
            user_id="test_user",
            auth_token="test_token",
        )

        init_help = classifier.get_phase_specific_help(init_state)
        assert init_help["current_phase"]["name"] == "Getting Started"
        assert "Start new email workflow" in init_help["available_actions"]

        # Test discovery phase
        discovery_state = UniversalWorkflowState(
            workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
            session_id="test_123",
            user_id="test_user",
            auth_token="test_token",
        )

        discovery_help = classifier.get_phase_specific_help(discovery_state)
        assert discovery_help["current_phase"]["name"] == "Requirements Gathering"
        assert "Provide email requirements" in discovery_help["available_actions"]
        assert "Start new email workflow" not in discovery_help["available_actions"]

    def test_help_handles_dict_state(self):
        """Test defensive programming for LangGraph dict conversion."""
        classifier = IntentClassifier()

        # Test with dict state
        dict_state = {
            "workflow_phase": "strategy_analysis",
            "session_id": "test_dict",
            "user_id": "test_user",
            "auth_token": "test_token",
        }

        help_data = classifier.get_phase_specific_help(dict_state)
        assert help_data["current_phase"]["name"] == "Strategy Development"
        assert "Review analysis results" in help_data["available_actions"]

    def test_help_fallback_on_invalid_state(self):
        """Test that invalid state falls back gracefully."""
        classifier = IntentClassifier()

        # Test with completely invalid state
        invalid_state = {"invalid_field": "invalid_value"}
        help_data = classifier.get_phase_specific_help(invalid_state)

        # Should return fallback help without crashing
        assert "global_commands" in help_data
        assert help_data["current_phase"]["phase"] == "unknown"

    def test_help_intent_returns_phase_help(self):
        """Test that help requests return phase-specific information."""
        classifier = IntentClassifier()

        state = UniversalWorkflowState(
            workflow_phase=WorkflowPhase.GENERATION,
            session_id="test_integration",
            user_id="test_user",
            auth_token="test_token",
        )

        result = classifier.classify_intent_with_state("help", state)

        assert result["intent"] == "help_request"
        assert result["response_type"] == "phase_specific_help"
        assert result["phase_aware"] is True
        assert "Content Creation" in result["help_data"]["current_phase"]["name"]

    def test_is_help_request(self):
        """Test help request detection."""
        classifier = IntentClassifier()

        # Test various help requests
        help_requests = [
            "help",
            "what can i do",
            "options",
            "what's available",
            "how does this work",
            "what now",
            "what next",
            "stuck",
            "what are my options",
            "show me",
            "guide",
            "assist",
        ]

        for request in help_requests:
            assert classifier._is_help_request(request) is True

        # Test non-help requests
        non_help_requests = [
            "create email",
            "write document",
            "analyze data",
            "hello",
            "good morning",
        ]

        for request in non_help_requests:
            assert classifier._is_help_request(request) is False
