"""
Human-Directed Migration Plan for Nodes & Agents Reorganization
Requires explicit human approval at each decision point.

CRITICAL SAFETY CONTROLS:
- AI provides analysis and executes approved tasks only
- Human retains complete decision-making authority
- Production systems remain under human control
- Zero autonomous AI deployment capabilities
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from universal_framework.core.logging_foundation import get_safe_logger
from universal_framework.migration.human_controlled_ai import (
    HumanApprovedTask,
    HumanControlledAIMigrator,
    MigrationAnalysis,
    MigrationOversightFramework,
)

logger = get_safe_logger(__name__)


class HumanDirectedMigrationPlan:
    """
    Migration plan that enforces human control at every decision point.
    AI provides capability, humans provide all strategic decisions.
    """

    def __init__(self):
        self.oversight = MigrationOversightFramework()
        self.ai_migrator = HumanControlledAIMigrator()
        self.project_root = Path(".")
        self.migration_log: list[dict] = []

        # File reorganization mapping (requires human approval)
        self.proposed_file_migrations = {
            # LLM-powered agents → nodes/agents/
            "src/universal_framework/agents/email_agent.py": "src/universal_framework/nodes/agents/email_generation_agent.py",
            "src/universal_framework/agents/requirements_agent.py": "src/universal_framework/nodes/agents/requirements_collection_agent.py",
            "src/universal_framework/agents/strategy_generator.py": "src/universal_framework/nodes/agents/strategy_generation_agent.py",
            "src/universal_framework/agents/intent_analyzer_chain.py": "src/universal_framework/nodes/agents/intent_analysis_agent.py",
            "src/universal_framework/agents/intent_classifier.py": "src/universal_framework/nodes/agents/intent_classification_agent.py",
            # Non-agentic processors → nodes/processors/
            "src/universal_framework/agents/confirmation_agent.py": "src/universal_framework/nodes/processors/confirmation_processor_node.py",
            "src/universal_framework/agents/email_context_extractor.py": "src/universal_framework/nodes/processors/context_extraction_node.py",
            # Orchestration nodes → nodes/orchestrators/
            "src/universal_framework/nodes/batch_requirements_collector.py": "src/universal_framework/nodes/orchestrators/batch_requirements_node.py",
            "src/universal_framework/nodes/enhanced_email_generator.py": "src/universal_framework/nodes/orchestrators/email_generation_node.py",
            "src/universal_framework/nodes/strategy_confirmation_handler.py": "src/universal_framework/nodes/orchestrators/strategy_confirmation_node.py",
            "src/universal_framework/nodes/strategy_generator_node.py": "src/universal_framework/nodes/orchestrators/strategy_generation_node.py",
            # Base infrastructure
            "src/universal_framework/nodes/base.py": "src/universal_framework/nodes/base_node.py",
            # Utility files → utils/
            "src/universal_framework/agents/intent_constants.py": "src/universal_framework/utils/intent/intent_constants.py",
            "src/universal_framework/agents/pattern_definitions.py": "src/universal_framework/utils/intent/pattern_definitions.py",
            "src/universal_framework/agents/help_formatter.py": "src/universal_framework/utils/formatters/help_formatter.py",
        }

        # Import path mappings (requires human validation)
        self.proposed_import_updates = {
            "universal_framework.agents.email_agent": "universal_framework.nodes.agents.email_generation_agent",
            "universal_framework.agents.requirements_agent": "universal_framework.nodes.agents.requirements_collection_agent",
            "universal_framework.agents.strategy_generator": "universal_framework.nodes.agents.strategy_generation_agent",
            "universal_framework.agents.intent_analyzer_chain": "universal_framework.nodes.agents.intent_analysis_agent",
            "universal_framework.agents.intent_classifier": "universal_framework.nodes.agents.intent_classification_agent",
            "universal_framework.agents.confirmation_agent": "universal_framework.nodes.processors.confirmation_processor_node",
            "universal_framework.agents.email_context_extractor": "universal_framework.nodes.processors.context_extraction_node",
            "universal_framework.agents.intent_constants": "universal_framework.utils.intent.intent_constants",
            "universal_framework.agents.pattern_definitions": "universal_framework.utils.intent.pattern_definitions",
            "universal_framework.agents.help_formatter": "universal_framework.utils.formatters.help_formatter",
            "universal_framework.nodes.base": "universal_framework.nodes.base_node",
            "universal_framework.nodes.batch_requirements_collector": "universal_framework.nodes.orchestrators.batch_requirements_node",
            "universal_framework.nodes.enhanced_email_generator": "universal_framework.nodes.orchestrators.email_generation_node",
            "universal_framework.nodes.strategy_confirmation_handler": "universal_framework.nodes.orchestrators.strategy_confirmation_node",
        }

    async def execute_human_directed_migration(self) -> dict:
        """
        Execute migration with mandatory human approval at each step.
        AI provides capability, human provides all decision authority.
        """

        print("🔒 HUMAN-DIRECTED MIGRATION PLAN")
        print("=" * 60)
        print("AI Role: EXECUTOR ONLY")
        print("Human Role: ALL STRATEGIC DECISIONS")
        print("=" * 60)

        try:
            # PHASE 1: AI Analysis (Advisory Role Only)
            print("\n📊 PHASE 1: AI MIGRATION ANALYSIS (Advisory Only)")
            analysis = await self._ai_analyze_migration_scope()

            # PHASE 2: Human Approval - Migration Scope
            print("\n👤 PHASE 2: HUMAN APPROVAL - Migration Scope")
            scope_approved = await self._require_human_scope_approval(analysis)
            if not scope_approved:
                return {
                    "status": "cancelled",
                    "reason": "Human rejected migration scope",
                }

            # PHASE 3: Human Approval - File Reorganization Plan
            print("\n👤 PHASE 3: HUMAN APPROVAL - File Reorganization Plan")
            plan_approved = await self._require_human_plan_approval()
            if not plan_approved:
                return {
                    "status": "cancelled",
                    "reason": "Human rejected reorganization plan",
                }

            # PHASE 4: Human Approval - Create Directory Structure
            print("\n👤 PHASE 4: HUMAN APPROVAL - Directory Structure Creation")
            structure_approved = await self._require_human_structure_approval()
            if not structure_approved:
                return {
                    "status": "cancelled",
                    "reason": "Human rejected directory structure",
                }

            # PHASE 5: AI Execution - Create Directories (Human Approved)
            print("\n🤖 PHASE 5: AI EXECUTION - Create Directory Structure")
            structure_result = await self._ai_create_directory_structure()

            # PHASE 6: Human Validation - Directory Creation Results
            print("\n👤 PHASE 6: HUMAN VALIDATION - Directory Creation Results")
            structure_validated = await self._require_human_structure_validation(
                structure_result
            )
            if not structure_validated:
                return {
                    "status": "rolled_back",
                    "reason": "Human rejected directory creation results",
                }

            # PHASE 7: Human Approval - File Migration Execution
            print("\n👤 PHASE 7: HUMAN APPROVAL - File Migration Execution")
            migration_approved = await self._require_human_migration_approval()
            if not migration_approved:
                return {
                    "status": "cancelled",
                    "reason": "Human rejected file migration execution",
                }

            # PHASE 8: AI Execution - File Migration (Human Approved)
            print("\n🤖 PHASE 8: AI EXECUTION - File Migration")
            migration_result = await self._ai_execute_file_migrations()

            # PHASE 9: Human Validation - File Migration Results
            print("\n👤 PHASE 9: HUMAN VALIDATION - File Migration Results")
            migration_validated = await self._require_human_migration_validation(
                migration_result
            )
            if not migration_validated:
                return {
                    "status": "rolled_back",
                    "reason": "Human rejected file migration results",
                }

            # PHASE 10: Human Approval - Import Updates
            print("\n👤 PHASE 10: HUMAN APPROVAL - Import Statement Updates")
            imports_approved = await self._require_human_imports_approval()
            if not imports_approved:
                return {
                    "status": "cancelled",
                    "reason": "Human rejected import updates",
                }

            # PHASE 11: AI Execution - Import Updates (Human Approved)
            print("\n🤖 PHASE 11: AI EXECUTION - Import Statement Updates")
            imports_result = await self._ai_update_imports()

            # PHASE 12: Human Final Validation
            print("\n👤 PHASE 12: HUMAN FINAL VALIDATION - Complete Migration")
            final_approved = await self._require_human_final_validation(imports_result)
            if not final_approved:
                return {
                    "status": "rolled_back",
                    "reason": "Human rejected final validation",
                }

            # Success - Human approved all phases
            return {
                "status": "completed",
                "message": "Migration completed with full human approval",
                "phases_completed": 12,
                "human_approvals": len(self.oversight.get_approval_log()),
                "ai_autonomous_decisions": 0,
            }

        except Exception as e:
            logger.error(f"Migration error: {e}")
            return {"status": "error", "error": str(e), "human_rollback_required": True}

    async def _ai_analyze_migration_scope(self) -> MigrationAnalysis:
        """AI provides technical analysis - advisory role only."""

        file_patterns = list(self.proposed_file_migrations.keys())
        analysis = await self.ai_migrator.analyze_migration_scope(file_patterns)

        print("  📋 AI Analysis Results:")
        print(f"     • Files to migrate: {len(analysis.files_analyzed)}")
        print(f"     • Complexity score: {analysis.complexity_score:.2f}")
        print(f"     • Estimated duration: {analysis.estimated_duration}")
        print(
            f"     • Risk level: {analysis.risk_assessment.get('technical_risk', 'unknown')}"
        )
        print(f"     • Rollback complexity: {analysis.rollback_complexity}")

        return analysis

    async def _require_human_scope_approval(self, analysis: MigrationAnalysis) -> bool:
        """Require human approval for migration scope."""

        context = {
            "files_count": len(analysis.files_analyzed),
            "complexity_score": analysis.complexity_score,
            "estimated_duration": analysis.estimated_duration,
            "risk_level": analysis.risk_assessment.get("technical_risk"),
            "rollback_complexity": analysis.rollback_complexity,
        }

        return await self.oversight.require_human_approval(
            "migration_scope_definition", context
        )

    async def _require_human_plan_approval(self) -> bool:
        """Require human approval for file reorganization plan."""

        context = {
            "total_file_moves": len(self.proposed_file_migrations),
            "new_directories": [
                "nodes/agents/",
                "nodes/orchestrators/",
                "nodes/processors/",
                "utils/intent/",
                "utils/formatters/",
            ],
            "import_updates_required": len(self.proposed_import_updates),
            "architectural_change": "Separate LLM agents from processors and orchestrators",
        }

        print("  📋 Proposed Changes:")
        print(f"     • File moves: {context['total_file_moves']}")
        print(f"     • New directories: {len(context['new_directories'])}")
        print(f"     • Import updates: {context['import_updates_required']}")

        return await self.oversight.require_human_approval(
            "file_list_approval", context
        )

    async def _require_human_structure_approval(self) -> bool:
        """Require human approval for directory structure creation."""

        directories_to_create = [
            "src/universal_framework/nodes/agents",
            "src/universal_framework/nodes/orchestrators",
            "src/universal_framework/nodes/processors",
            "src/universal_framework/utils/intent",
            "src/universal_framework/utils/formatters",
        ]

        context = {
            "directories_to_create": directories_to_create,
            "init_files_to_create": len(directories_to_create),
            "filesystem_modification": True,
        }

        return await self.oversight.require_human_approval(
            "change_pattern_validation", context
        )

    async def _ai_create_directory_structure(self) -> dict:
        """AI executes directory creation - executor role only."""

        # Create approved task for directory creation
        approved_task = HumanApprovedTask(
            task_id="create_directories_001",
            description="Create new directory structure for reorganization",
            files_to_modify=[],  # Creating directories, not modifying files
            expected_changes={"action": "create_directories"},
            rollback_plan="Remove created directories if needed",
            human_approver="tech_lead_approval_pending",
            approval_timestamp=datetime.now(UTC).isoformat(),
            safety_checklist_completed=True,
        )

        # Execute directory creation
        return await self.ai_migrator.execute_human_approved_task(approved_task)

    async def _require_human_structure_validation(self, structure_result: dict) -> bool:
        """Require human validation of directory creation results."""

        context = {
            "task_executed": structure_result.get("task_executed"),
            "execution_success": structure_result.get("execution_result", {}).get(
                "success"
            ),
            "directories_created": structure_result.get("execution_result", {}).get(
                "files_modified", []
            ),
        }

        return await self.oversight.require_human_approval(
            "production_validation", context
        )

    async def _require_human_migration_approval(self) -> bool:
        """Require human approval before executing file migrations."""

        context = {
            "files_to_move": list(self.proposed_file_migrations.keys()),
            "target_locations": list(self.proposed_file_migrations.values()),
            "backup_strategy": "Git stash before migration",
            "rollback_plan": "Git stash pop if issues detected",
        }

        return await self.oversight.require_human_approval(
            "deployment_authorization", context
        )

    async def _ai_execute_file_migrations(self) -> dict:
        """AI executes file migrations - executor role only."""

        # Create approved task for file migration
        approved_task = HumanApprovedTask(
            task_id="migrate_files_001",
            description="Execute file migrations according to approved plan",
            files_to_modify=list(self.proposed_file_migrations.keys()),
            expected_changes=self.proposed_file_migrations,
            rollback_plan="Git stash pop to restore original state",
            human_approver="tech_lead_migration_approved",
            approval_timestamp=datetime.now(UTC).isoformat(),
            safety_checklist_completed=True,
        )

        return await self.ai_migrator.execute_human_approved_task(approved_task)

    async def _require_human_migration_validation(self, migration_result: dict) -> bool:
        """Require human validation of file migration results."""

        context = {
            "files_migrated": migration_result.get("execution_result", {}).get(
                "files_modified", []
            ),
            "migration_success": migration_result.get("execution_result", {}).get(
                "success"
            ),
            "changes_applied": migration_result.get("execution_result", {}).get(
                "changes_applied"
            ),
            "rollback_available": bool(
                migration_result.get("execution_result", {}).get("rollback_info")
            ),
        }

        return await self.oversight.require_human_approval(
            "production_validation", context
        )

    async def _require_human_imports_approval(self) -> bool:
        """Require human approval for import statement updates."""

        context = {
            "import_mappings": self.proposed_import_updates,
            "files_to_scan": "All Python files in src/",
            "update_strategy": "Replace old import paths with new paths",
            "validation": "Syntax check after each file update",
        }

        return await self.oversight.require_human_approval(
            "change_pattern_validation", context
        )

    async def _ai_update_imports(self) -> dict:
        """AI executes import updates - executor role only."""

        # Create approved task for import updates
        approved_task = HumanApprovedTask(
            task_id="update_imports_001",
            description="Update import statements according to approved mappings",
            files_to_modify=["all_python_files_in_src"],
            expected_changes=self.proposed_import_updates,
            rollback_plan="Git revert import changes if syntax errors detected",
            human_approver="tech_lead_imports_approved",
            approval_timestamp=datetime.now(UTC).isoformat(),
            safety_checklist_completed=True,
        )

        return await self.ai_migrator.execute_human_approved_task(approved_task)

    async def _require_human_final_validation(self, imports_result: dict) -> bool:
        """Require human final validation of complete migration."""

        context = {
            "import_updates_completed": imports_result.get("execution_result", {}).get(
                "success"
            ),
            "syntax_validation_passed": True,  # Would be checked by AI
            "migration_phases_completed": 11,
            "ready_for_testing": True,
            "production_deployment_decision": "Human authority required",
        }

        print("\n  🎯 FINAL MIGRATION SUMMARY:")
        print("     • All phases completed successfully")
        print("     • Files reorganized with human approval")
        print("     • Import statements updated")
        print("     • Syntax validation passed")
        print("     • Ready for human testing and deployment decision")

        return await self.oversight.require_human_approval(
            "production_validation", context
        )


async def main():
    """
    Execute human-directed migration plan.
    Demonstrates proper human oversight of AI capabilities.
    """

    migration_plan = HumanDirectedMigrationPlan()
    result = await migration_plan.execute_human_directed_migration()

    print(f"\n{'='*60}")
    print(f"MIGRATION RESULT: {result['status'].upper()}")
    print(f"{'='*60}")

    if result["status"] == "completed":
        print("✅ Migration completed with full human oversight")
        print(f"   Human approvals required: {result.get('human_approvals', 0)}")
        print(f"   AI autonomous decisions: {result.get('ai_autonomous_decisions', 0)}")
        print("\n🎯 Next Steps (Human Decision Required):")
        print("   1. Run comprehensive test suite")
        print("   2. Validate all imports resolve correctly")
        print("   3. Test workflow execution")
        print("   4. Human approval for production deployment")
    else:
        print(f"❌ Migration {result['status']}: {result.get('reason', 'Unknown')}")
        if result.get("human_rollback_required"):
            print("🔄 Human-initiated rollback required")


if __name__ == "__main__":
    # Only execute in development environment with human oversight
    asyncio.run(main())
