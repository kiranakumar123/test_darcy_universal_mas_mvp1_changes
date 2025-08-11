from datetime import datetime
from typing import Any

from universal_framework.observability import UniversalFrameworkLogger


class SessionFlowLogger:
    """Structured logging helper for session events."""

    def __init__(self) -> None:
        self.logger = UniversalFrameworkLogger("session_flow")

    def _redact(self, session_id: str) -> str:
        return session_id[:8] + "..." if session_id else "invalid_session"

    def log_session_creation(
        self, session_id: str, user_id: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.logger.info(
            "session_created",
            session_id_prefix=self._redact(session_id),
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )

    def log_session_propagation(
        self, session_id: str, user_id: str, direction: str, endpoint: str
    ) -> None:
        self.logger.info(
            "session_propagated",
            session_id_prefix=self._redact(session_id),
            user_id=user_id,
            direction=direction,
            endpoint=endpoint,
            timestamp=datetime.utcnow().isoformat(),
        )

    def log_session_retrieval(self, session_id: str, user_id: str) -> None:
        """Log retrieval of an existing session."""
        self.logger.info(
            "session_retrieved",
            session_id_prefix=self._redact(session_id),
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
        )

    def log_workflow_phase_transition(
        self, session_id: str, user_id: str, from_phase: str, to_phase: str
    ) -> None:
        self.logger.info(
            "workflow_phase_transition",
            session_id_prefix=self._redact(session_id),
            user_id=user_id,
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.utcnow().isoformat(),
        )
