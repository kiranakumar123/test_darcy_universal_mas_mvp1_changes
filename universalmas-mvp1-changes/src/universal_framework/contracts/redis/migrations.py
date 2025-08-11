"""
Redis Contract Migration Framework
==================================

Support for schema versioning and safe contract evolution.
"""

from datetime import datetime
from typing import Any

from .exceptions import RedisVersionError
from .validation import SchemaValidator


class ContractMigration:
    """Base class for contract migrations."""

    def __init__(self, from_version: int, to_version: int):
        self.from_version = from_version
        self.to_version = to_version

    def can_migrate(self, data: dict[str, Any]) -> bool:
        """Check if data can be migrated."""
        schema = int(data.get("schema_version", 1))
        return schema == self.from_version

    def migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Perform migration. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement migrate()")

    def rollback(self, data: dict[str, Any]) -> dict[str, Any]:
        """Rollback migration. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement rollback()")


class SessionDataMigrationV1ToV2(ContractMigration):
    """Example migration from v1 to v2 (placeholder for future use)."""

    def __init__(self):
        super().__init__(from_version=1, to_version=2)

    def migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate session data from v1 to v2."""
        migrated = data.copy()

        # Example: Add new field with default value
        migrated["schema_version"] = 2
        migrated["migration_timestamp"] = datetime.now().isoformat()

        return migrated

    def rollback(self, data: dict[str, Any]) -> dict[str, Any]:
        """Rollback session data from v2 to v1."""
        rolled_back = data.copy()

        # Example: Remove v2-specific fields
        rolled_back["schema_version"] = 1
        rolled_back.pop("migration_timestamp", None)

        return rolled_back


class MigrationManager:
    """Manages contract migrations and version compatibility."""

    def __init__(self):
        self.migrations: list[ContractMigration] = []
        self.validator = SchemaValidator()
        self.current_version = 1

    def register_migration(self, migration: ContractMigration) -> None:
        """Register a migration."""
        self.migrations.append(migration)
        # Sort by from_version for proper ordering
        self.migrations.sort(key=lambda m: m.from_version)

    def get_migration_path(
        self, from_version: int, to_version: int
    ) -> list[ContractMigration]:
        """Get ordered list of migrations needed."""
        if from_version == to_version:
            return []

        path = []
        current = from_version

        while current < to_version:
            # Find migration from current version
            next_migration = None
            for migration in self.migrations:
                if (
                    migration.from_version == current
                    and migration.to_version <= to_version
                ):
                    next_migration = migration
                    break

            if not next_migration:
                raise RedisVersionError(
                    f"No migration path from v{from_version} to v{to_version}"
                )

            path.append(next_migration)
            current = next_migration.to_version

        return path

    def migrate_data(
        self, data: dict[str, Any], target_version: int | None = None
    ) -> dict[str, Any]:
        """Migrate data to target version (default: current version)."""
        if target_version is None:
            target_version = self.current_version

        current_version = data.get("schema_version", 1)

        if current_version == target_version:
            return data

        if current_version > target_version:
            raise RedisVersionError(
                f"Downgrade from v{current_version} to v{target_version} not supported"
            )

        # Get migration path
        migration_path = self.get_migration_path(current_version, target_version)

        # Apply migrations in sequence
        migrated_data = data.copy()
        for migration in migration_path:
            try:
                migrated_data = migration.migrate(migrated_data)
            except Exception as err:
                raise RedisVersionError(
                    f"Migration failed v{migration.from_version} -> v{migration.to_version}: {err}"
                ) from err

        return migrated_data

    def is_version_supported(self, version: int) -> bool:
        """Check if version is supported."""
        return 1 <= version <= self.current_version

    def get_supported_versions(self) -> list[int]:
        """Get list of supported schema versions."""
        return list(range(1, self.current_version + 1))


# Global migration manager
_migration_manager = MigrationManager()


def get_migration_manager() -> MigrationManager:
    """Get global migration manager."""
    return _migration_manager


def migrate_session_data(
    data: dict[str, Any], target_version: int | None = None
) -> dict[str, Any]:
    """Convenience function for migrating session data."""
    return _migration_manager.migrate_data(data, target_version)


def register_migration(migration: ContractMigration) -> None:
    """Register a migration with the global manager."""
    _migration_manager.register_migration(migration)


# Register default migrations
# (Currently just placeholder - actual migrations added as needed)
# register_migration(SessionDataMigrationV1ToV2())
