from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from universal_framework.observability import UniversalFrameworkLogger

from ..contracts.exceptions import (
    TemplateNotFoundError,
    TemplateStoreError,
    TemplateValidationError,
)
from ..contracts.redis.key_manager import RedisKeyManager
from ..contracts.templates import StoredTemplate
from ..observability.simple_metrics import SimpleMetricsCollector
from ..redis.connection import RedisConnectionAdapter


class TemplateStore:
    """Redis-backed storage for enterprise templates."""

    def __init__(self, redis_adapter: RedisConnectionAdapter) -> None:
        self.redis = redis_adapter
        self.key_manager = RedisKeyManager()
        self.metrics = SimpleMetricsCollector()
        self.logger = UniversalFrameworkLogger("template_store")

    async def find_template_by_type(self, template_type: str) -> StoredTemplate | None:
        """Retrieve stored template by type, or None if not found."""
        start_time = datetime.now()
        try:
            pattern = self.key_manager.template_pattern_by_type(template_type)
            keys = await self.redis.execute_command("KEYS", pattern)
            if not keys:
                self.logger.log_template_operation(
                    "retrieve",
                    template_type,
                    {
                        "success": False,
                        "reason": "no_templates_found",
                    },
                )
                return None

            key = keys[0]
            raw = await self.redis.execute_command("GET", key)
            if not raw:
                raise TemplateNotFoundError(f"Template data missing for key: {key}")

            data = json.loads(raw)
            template = self._deserialize_template(data)
            updated = template.copy_with_usage_update()
            await self.store_template(updated)

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.observe_histogram("template_lookup_ms", elapsed)
            self.metrics.increment_counter("template_retrieved")

            self.logger.log_template_operation(
                "retrieve",
                template.template_id,
                {
                    "success": True,
                    "usage_count": updated.usage_count,
                    "lookup_time_ms": elapsed,
                },
            )
            return updated
        except TemplateNotFoundError as err:
            self.metrics.increment_counter("template_lookup_failures")
            self.logger.log_template_operation(
                "retrieve",
                template_type,
                {"success": False, "error": str(err)},
            )
            return None
        except json.JSONDecodeError as err:
            self.metrics.increment_counter("template_lookup_failures")
            self.logger.log_template_operation(
                "retrieve",
                template_type,
                {"success": False, "error": "invalid_json"},
            )
            raise TemplateStoreError(f"Invalid template data format: {err}") from err
        except Exception as err:
            self.metrics.increment_counter("template_lookup_failures")
            self.logger.log_template_operation(
                "retrieve",
                template_type,
                {"success": False, "error": str(err)},
            )
            raise TemplateStoreError("Template retrieval failed") from err

    async def store_template(self, template: StoredTemplate) -> bool:
        """Store or update a template with validation."""
        try:
            self._validate_template_content(template)

            key = self.key_manager.template_key(
                template.template_id, template.template_type
            )
            data = {
                "template_id": template.template_id,
                "template_type": template.template_type,
                "subject_template": template.subject_template,
                "body_template": template.body_template,
                "variables": template.variables,
                "metadata": template.metadata,
                "created_date": template.created_date.isoformat(),
                "last_used": template.last_used.isoformat(),
                "usage_count": template.usage_count,
            }
            await self.redis.execute_command("SET", key, json.dumps(data))
            self.logger.log_template_operation(
                "store",
                template.template_id,
                {
                    "success": True,
                    "template_type": template.template_type,
                    "variables_count": len(template.variables),
                },
            )
            return True
        except TemplateValidationError as err:
            self.logger.log_template_operation(
                "store",
                template.template_id,
                {"success": False, "error": str(err)},
            )
            raise
        except Exception as err:
            self.logger.log_template_operation(
                "store",
                template.template_id,
                {"success": False, "error": str(err)},
            )
            raise TemplateStoreError("Template storage failed") from err

    def _deserialize_template(self, data: dict[str, Any]) -> StoredTemplate:
        return StoredTemplate(
            template_id=data["template_id"],
            template_type=data["template_type"],
            subject_template=data["subject_template"],
            body_template=data["body_template"],
            variables=list(data.get("variables", [])),
            metadata=data.get("metadata", {}),
            created_date=datetime.fromisoformat(data["created_date"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            usage_count=data.get("usage_count", 0),
        )

    def _validate_template_content(self, template: StoredTemplate) -> None:
        """Validate template content for security compliance."""
        dangerous_patterns = ["<script", "javascript:", "onload=", "onclick="]
        for pattern in dangerous_patterns:
            if pattern.lower() in template.body_template.lower():
                raise TemplateValidationError(f"Dangerous content detected: {pattern}")
        if not template.template_id or not template.template_type:
            raise TemplateValidationError("Template ID and type are required")
        if not template.subject_template or not template.body_template:
            raise TemplateValidationError("Subject and body templates are required")
