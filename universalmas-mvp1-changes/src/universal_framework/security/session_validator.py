import hashlib
import hmac
import os
import re

from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.redis.session_storage import SessionStorage


class SessionSecurityError(Exception):
    """Raised when session security validation fails."""


class SessionValidator:
    """Validate and manage session identifiers."""

    SESSION_ID_PATTERN = re.compile(
        r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
    )

    def __init__(self) -> None:
        self.logger = UniversalFrameworkLogger("session_security")
        self.session_storage: SessionStorage | None = None

    def set_session_storage(self, session_storage: SessionStorage) -> None:
        """Inject session storage implementation for ownership checks."""
        self.session_storage = session_storage

    def validate_session_format(self, session_id: str) -> bool:
        """Return True if the session ID matches the expected pattern."""
        if not session_id or len(session_id) < 36:
            return False
        return bool(self.SESSION_ID_PATTERN.match(session_id))

    async def validate_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Return True if the session ID belongs to the given user."""
        if not self.session_storage:
            self.logger.error("session_storage_not_configured")
            return True  # Fallback for non-configured environments

        if not self.validate_session_format(session_id):
            self.logger.warning(
                "invalid_session_format",
                session_id_prefix=self._redact(session_id),
                user_id=user_id,
            )
            return False

        return await self.session_storage.validate_session_ownership(
            session_id, user_id
        )

    def create_user_namespaced_session_id(
        self, user_id: str, base_session_id: str
    ) -> str:
        """Return an HMAC based session identifier."""
        session_data = f"{user_id}:{base_session_id}"
        digest = hmac.new(
            key=self._get_secret().encode(),
            msg=session_data.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return (
            digest[:8]
            + "-"
            + digest[8:12]
            + "-4"
            + digest[12:15]
            + "-a"
            + digest[15:18]
            + "-"
            + digest[18:30]
        )

    def _redact(self, session_id: str) -> str:
        return session_id[:8] + "..." if session_id else "invalid_session"

    def _get_secret(self) -> str:
        return os.environ.get("SESSION_SECRET_KEY", "dev_secret")
