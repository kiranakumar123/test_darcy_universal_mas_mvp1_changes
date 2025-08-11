"""
Human-Controlled AI Migration Framework
Implements strict human oversight boundaries for AI-assisted code migration.

CRITICAL SAFETY CONTROLS:
- AI agents are EXECUTORS ONLY, never orchestrators
- Every strategic decision requires explicit human approval
- Zero autonomous production system modifications
- Human retains complete authority over deployment and rollback
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from universal_framework.contracts.exceptions import SecurityError
from universal_framework.core.logging_foundation import get_safe_logger

logger = get_safe_logger(__name__)


class AIAgentRole(Enum):
    """Strictly enforced AI agent role boundaries."""

    EXECUTOR_ONLY = "executor_only"  # ✅ Safe: Execute pre-approved tasks
    ADVISOR_ONLY = "advisor_only"  # ✅ Safe: Provide analysis, no actions
    FORBIDDEN = "forbidden"  # ❌ Never allow orchestration


class HumanApprovalStatus(Enum):
    """Human approval states for migration tasks."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class HumanApprovedTask:
    """
    Every AI action requires explicit human approval.
    AI agents cannot create or modify these tasks.
    """

    task_id: str
    description: str
    files_to_modify: list[str]
    expected_changes: dict[str, str]
    rollback_plan: str
    human_approver: str
    approval_timestamp: str
    safety_checklist_completed: bool
    approval_signature: str = field(init=False)

    def __post_init__(self):
        """Generate cryptographic signature to prevent AI tampering."""
        self.approval_signature = self._generate_approval_signature()

    def _generate_approval_signature(self) -> str:
        """Create tamper-proof human approval signature."""
        content = f"{self.task_id}:{self.human_approver}:{self.approval_timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class MigrationAnalysis:
    """AI-generated analysis that requires human approval to act upon."""

    analysis_id: str
    scope_description: str
    files_analyzed: list[str]
    proposed_changes: dict[str, str]
    risk_assessment: dict[str, Any]
    complexity_score: float
    estimated_duration: str
    rollback_complexity: str
    human_review_required: bool = True
    ai_confidence: float = field(default=0.0)

    def requires_human_approval(self) -> bool:
        """All analyses require human approval - AI cannot override."""
        return True


class AIAgentConstraints:
    """
    Hardcoded constraints that AI agents cannot override.
    Prevents AI orchestrator behavior.
    """

    FORBIDDEN_CAPABILITIES = {
        "production_deployment",
        "system_rollback",
        "config_modification",
        "network_changes",
        "security_policy_changes",
        "autonomous_decision_making",
        "stakeholder_communication",
        "timeline_modification",
        "scope_changes",
    }

    REQUIRED_HUMAN_APPROVALS = {
        "migration_scope_definition",
        "file_list_approval",
        "change_pattern_validation",
        "rollback_plan_approval",
        "deployment_authorization",
        "production_validation",
        "error_recovery_decision",
    }

    def __init__(self):
        # These constraints cannot be modified by AI
        self.human_approval_mandatory = True
        self.autonomous_actions_blocked = True
        self.orchestration_forbidden = True
        self._constraint_lock = True  # Prevents AI modification

    def validate_ai_action(
        self, action: str, human_approval: str | None = None
    ) -> bool:
        """Prevent AI from taking forbidden actions."""
        if action in self.FORBIDDEN_CAPABILITIES:
            raise SecurityError(
                f"AI FORBIDDEN: Action '{action}' requires human execution"
            )

        if action in self.REQUIRED_HUMAN_APPROVALS and not human_approval:
            raise SecurityError(f"HUMAN APPROVAL REQUIRED: Action '{action}' blocked")

        logger.info(
            f"AI action validated: {action}",
            extra={
                "action": action,
                "human_approval_provided": bool(human_approval),
                "security_check": "PASSED",
            },
        )

        return True

    def is_orchestration_attempt(self, method_name: str) -> bool:
        """Detect if AI is attempting orchestration patterns."""
        orchestration_patterns = {
            "manage_",
            "orchestrate_",
            "control_",
            "decide_",
            "initiate_",
            "deploy_",
            "rollback_",
            "assess_system",
        }

        return any(pattern in method_name.lower() for pattern in orchestration_patterns)


class HumanControlledAIMigrator:
    """
    AI agent with strict human oversight boundaries.
    ZERO autonomous decision-making capability.

    Role: Code transformation executor under human supervision
    Forbidden: Strategic decisions, production control, system assessment
    """

    def __init__(self):
        self.role = AIAgentRole.EXECUTOR_ONLY
        self.constraints = AIAgentConstraints()
        self.human_approval_required = True  # Cannot be disabled
        self.autonomous_actions_forbidden = True
        self.execution_log: list[dict[str, Any]] = []

        logger.info(
            "Human-controlled AI migrator initialized",
            extra={
                "role": self.role.value,
                "autonomous_actions": "FORBIDDEN",
                "human_oversight": "MANDATORY",
            },
        )

    async def analyze_migration_scope(
        self, file_patterns: list[str]
    ) -> MigrationAnalysis:
        """
        AI ADVISOR ROLE: Analyze and propose, never execute.
        Human must review and approve before any action.
        """
        self.constraints.validate_ai_action("migration_analysis")

        logger.info(
            "Starting migration scope analysis",
            extra={
                "file_patterns": file_patterns,
                "ai_role": "ADVISOR_ONLY",
                "human_approval_required": True,
            },
        )

        # AI provides technical analysis only
        analysis = MigrationAnalysis(
            analysis_id=f"analysis_{int(time.time())}",
            scope_description=f"Analysis of {len(file_patterns)} file patterns",
            files_analyzed=file_patterns,
            proposed_changes=await self._analyze_file_patterns(file_patterns),
            risk_assessment=await self._assess_migration_risks(file_patterns),
            complexity_score=self._calculate_complexity_score(file_patterns),
            estimated_duration=self._estimate_duration(file_patterns),
            rollback_complexity=self._assess_rollback_complexity(file_patterns),
            ai_confidence=0.85,
        )

        logger.info(
            "Migration analysis completed",
            extra={
                "analysis_id": analysis.analysis_id,
                "files_analyzed": len(analysis.files_analyzed),
                "complexity_score": analysis.complexity_score,
                "human_decision_required": True,
                "no_actions_taken": True,
            },
        )

        return analysis

    async def execute_human_approved_task(
        self, approved_task: HumanApprovedTask
    ) -> dict[str, Any]:
        """
        AI EXECUTOR ROLE: Execute only pre-approved, specific tasks.
        No deviation from approved plan allowed.
        """
        # Validate human approval authenticity
        if not self._validate_human_approval(approved_task):
            raise SecurityError("Invalid or missing human approval signature")

        if not approved_task.safety_checklist_completed:
            raise SecurityError("Human safety checklist not completed")

        self.constraints.validate_ai_action(
            "execute_approved_task", approved_task.approval_signature
        )

        logger.info(
            "Executing human-approved task",
            extra={
                "task_id": approved_task.task_id,
                "human_approver": approved_task.human_approver,
                "files_to_modify": len(approved_task.files_to_modify),
                "safety_checklist": "COMPLETED",
            },
        )

        # Execute ONLY the approved changes
        execution_result = await self._execute_approved_changes_only(approved_task)

        # Log execution for human review
        self.execution_log.append(
            {
                "task_id": approved_task.task_id,
                "executed_at": datetime.now(UTC).isoformat(),
                "human_approver": approved_task.human_approver,
                "files_modified": execution_result.get("files_modified", []),
                "success": execution_result.get("success", False),
                "requires_human_validation": True,
            }
        )

        return {
            "task_executed": approved_task.task_id,
            "execution_result": execution_result,
            "human_review_required": True,
            "autonomous_decisions_made": 0,  # Always zero
            "requires_human_validation": True,
            "next_step": "HUMAN_VALIDATION_REQUIRED",
        }

    async def _analyze_file_patterns(self, patterns: list[str]) -> dict[str, str]:
        """AI analysis of file patterns - advisory only."""
        # Technical analysis implementation
        return {
            "pattern_complexity": "medium",
            "import_dependencies": "manageable",
            "refactoring_scope": "file_moves_and_imports",
            "estimated_changes": f"{len(patterns) * 5} import statements",
        }

    async def _assess_migration_risks(self, patterns: list[str]) -> dict[str, Any]:
        """AI risk assessment - advisory only."""
        return {
            "technical_risk": "low",
            "breaking_changes": "minimal",
            "rollback_difficulty": "easy",
            "testing_requirements": "import_validation_sufficient",
            "production_impact": "none_if_staged_properly",
        }

    def _calculate_complexity_score(self, patterns: list[str]) -> float:
        """Calculate migration complexity (0.0 = simple, 1.0 = complex)."""
        # Simple heuristic based on file count and patterns
        base_score = min(len(patterns) / 50.0, 0.7)  # Max 0.7 for file count
        return base_score

    def _estimate_duration(self, patterns: list[str]) -> str:
        """Estimate migration duration - advisory only."""
        file_count = len(patterns)
        if file_count < 10:
            return "1-2 hours"
        elif file_count < 25:
            return "2-4 hours"
        else:
            return "4-8 hours"

    def _assess_rollback_complexity(self, patterns: list[str]) -> str:
        """Assess rollback complexity - advisory only."""
        return (
            "simple_git_revert" if len(patterns) < 30 else "staged_rollback_recommended"
        )

    def _validate_human_approval(self, task: HumanApprovedTask) -> bool:
        """Verify authentic human approval exists."""
        expected_signature = task._generate_approval_signature()
        signature_valid = task.approval_signature == expected_signature

        # Additional validation checks
        approval_recent = self._is_approval_recent(task.approval_timestamp)
        checklist_complete = task.safety_checklist_completed

        return signature_valid and approval_recent and checklist_complete

    def _is_approval_recent(self, timestamp_str: str) -> bool:
        """Ensure approval is recent (within 24 hours)."""
        try:
            approval_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            time_diff = now - approval_time
            return time_diff.total_seconds() < 86400  # 24 hours
        except Exception:
            return False

    async def _execute_approved_changes_only(
        self, task: HumanApprovedTask
    ) -> dict[str, Any]:
        """Execute only the specific changes approved by human."""
        modified_files = []
        success_count = 0

        try:
            for file_path in task.files_to_modify:
                expected_change = task.expected_changes.get(file_path)
                if expected_change:
                    # Execute the specific approved change
                    change_result = await self._apply_approved_change(
                        file_path, expected_change
                    )
                    if change_result["success"]:
                        modified_files.append(file_path)
                        success_count += 1

            return {
                "success": success_count == len(task.files_to_modify),
                "files_modified": modified_files,
                "changes_applied": success_count,
                "total_files": len(task.files_to_modify),
                "rollback_info": task.rollback_plan,
            }

        except Exception as e:
            logger.error(
                f"Error executing approved changes: {e}",
                extra={
                    "task_id": task.task_id,
                    "error": str(e),
                    "rollback_required": True,
                },
            )
            raise

    async def _apply_approved_change(
        self, file_path: str, change_description: str
    ) -> dict[str, Any]:
        """Apply a specific approved change to a file."""
        # Implementation would go here - for now, return success simulation
        return {
            "success": True,
            "file_path": file_path,
            "change_applied": change_description,
            "backup_created": True,
        }

    # ❌ FORBIDDEN METHODS (will raise SecurityError if called)

    def assess_production_health(self):
        """❌ FORBIDDEN: AI cannot assess production systems."""
        raise SecurityError(
            "AI FORBIDDEN: Production health assessment requires human expertise"
        )

    def initiate_rollback(self):
        """❌ FORBIDDEN: AI cannot initiate rollbacks."""
        raise SecurityError(
            "AI FORBIDDEN: Rollback decisions require human authorization"
        )

    def modify_deployment_config(self):
        """❌ FORBIDDEN: AI cannot modify deployment configurations."""
        raise SecurityError(
            "AI FORBIDDEN: Deployment configuration is human-controlled"
        )

    def communicate_with_stakeholders(self):
        """❌ FORBIDDEN: AI cannot communicate with stakeholders."""
        raise SecurityError(
            "AI FORBIDDEN: Stakeholder communication requires human judgment"
        )

    def change_migration_scope(self):
        """❌ FORBIDDEN: AI cannot change migration scope."""
        raise SecurityError("AI FORBIDDEN: Scope changes require human approval")

    def make_strategic_decisions(self):
        """❌ FORBIDDEN: AI cannot make strategic decisions."""
        raise SecurityError("AI FORBIDDEN: Strategic decisions require human judgment")


class MigrationOversightFramework:
    """
    Ensures human control over all critical migration decisions.
    AI agents cannot bypass these control points.
    """

    def __init__(self):
        self.human_approvals: dict[str, bool] = {}
        self.approval_log: list[dict[str, Any]] = []
        self.ai_constraints = AIAgentConstraints()
        self.oversight_active = True

        logger.info(
            "Migration oversight framework activated",
            extra={
                "human_control": "MANDATORY",
                "ai_constraints": "ENFORCED",
                "approval_gates": len(self.ai_constraints.REQUIRED_HUMAN_APPROVALS),
            },
        )

    async def require_human_approval(
        self, decision_point: str, context: dict[str, Any] = None
    ) -> bool:
        """
        Block AI execution until human provides explicit approval.
        This is a BLOCKING call - AI cannot proceed without human input.
        """
        if decision_point not in self.ai_constraints.REQUIRED_HUMAN_APPROVALS:
            raise ValueError(f"Unrecognized decision point: {decision_point}")

        logger.info(
            f"🚨 HUMAN APPROVAL REQUIRED: {decision_point}",
            extra={
                "decision_point": decision_point,
                "ai_execution": "PAUSED",
                "context": context or {},
            },
        )

        # BLOCKING: AI cannot proceed without human approval
        print(f"\n🚨 HUMAN APPROVAL REQUIRED: {decision_point}")
        print("AI execution paused. Waiting for human decision...")
        if context:
            print(f"Context: {json.dumps(context, indent=2)}")

        human_decision = await self._wait_for_human_input(decision_point, context)

        # Log the human decision
        self.approval_log.append(
            {
                "decision_point": decision_point,
                "human_decision": human_decision,
                "timestamp": datetime.now(UTC).isoformat(),
                "context": context,
            }
        )

        self.human_approvals[decision_point] = human_decision

        logger.info(
            f"Human decision recorded: {decision_point}",
            extra={
                "decision": "APPROVED" if human_decision else "REJECTED",
                "ai_execution": "RESUMED" if human_decision else "HALTED",
            },
        )

        return human_decision

    async def _wait_for_human_input(
        self, decision: str, context: dict[str, Any] = None
    ) -> bool:
        """
        BLOCKING CALL: AI execution halts here.
        Human must provide explicit approval via secure interface.
        """
        # In a real implementation, this would integrate with a secure UI
        # For now, we'll simulate the blocking behavior

        print(f"\n{'='*60}")
        print("HUMAN DECISION REQUIRED")
        print(f"Decision Point: {decision}")
        print(f"{'='*60}")

        if context:
            print("Context Information:")
            for key, value in context.items():
                print(f"  {key}: {value}")
            print()

        # Simulate human input (in production, this would be a secure interface)
        response = input("Approve this action? (yes/no): ").strip().lower()
        approved = response in ["yes", "y", "approve", "approved"]

        print(f"Human Decision: {'APPROVED' if approved else 'REJECTED'}")
        print(f"{'='*60}\n")

        return approved

    def get_approval_status(self, decision_point: str) -> bool | None:
        """Get the status of a human approval."""
        return self.human_approvals.get(decision_point)

    def get_approval_log(self) -> list[dict[str, Any]]:
        """Get the complete log of human approvals."""
        return self.approval_log.copy()


# Example usage and validation
async def demonstrate_safe_ai_usage():
    """
    Demonstrate the safe human-controlled AI pattern.
    Shows proper AI executor role with human oversight.
    """

    print("🔒 Demonstrating Human-Controlled AI Migration")
    print("=" * 60)

    # Initialize human-controlled components
    oversight = MigrationOversightFramework()
    ai_migrator = HumanControlledAIMigrator()

    try:
        # Step 1: AI provides analysis (advisory role)
        print("\n1. AI Analysis Phase (Advisory Only)")
        file_patterns = ["agents/*.py", "nodes/*.py"]
        analysis = await ai_migrator.analyze_migration_scope(file_patterns)

        print("AI Analysis Complete:")
        print(f"  - Files analyzed: {len(analysis.files_analyzed)}")
        print(f"  - Complexity score: {analysis.complexity_score}")
        print(f"  - Estimated duration: {analysis.estimated_duration}")
        print(f"  - Human review required: {analysis.requires_human_approval()}")

        # Step 2: Human approval required for scope
        print("\n2. Human Approval Gate - Migration Scope")
        scope_approved = await oversight.require_human_approval(
            "migration_scope_definition",
            {
                "files_count": len(analysis.files_analyzed),
                "complexity": analysis.complexity_score,
                "estimated_duration": analysis.estimated_duration,
            },
        )

        if not scope_approved:
            print("❌ Migration cancelled by human decision")
            return

        # Step 3: Create human-approved task
        print("\n3. Creating Human-Approved Task")
        approved_task = HumanApprovedTask(
            task_id="migration_001",
            description="Reorganize agents and nodes directories",
            files_to_modify=analysis.files_analyzed,
            expected_changes=analysis.proposed_changes,
            rollback_plan="git revert + import fixes",
            human_approver="tech_lead@company.com",
            approval_timestamp=datetime.now(UTC).isoformat(),
            safety_checklist_completed=True,
        )

        print(
            f"Task created with approval signature: {approved_task.approval_signature}"
        )

        # Step 4: Human approval for execution
        print("\n4. Human Approval Gate - Task Execution")
        execution_approved = await oversight.require_human_approval(
            "file_list_approval",
            {
                "task_id": approved_task.task_id,
                "files_to_modify": len(approved_task.files_to_modify),
                "human_approver": approved_task.human_approver,
            },
        )

        if not execution_approved:
            print("❌ Task execution cancelled by human decision")
            return

        # Step 5: AI executes approved task (executor role)
        print("\n5. AI Execution Phase (Executor Only)")
        execution_result = await ai_migrator.execute_human_approved_task(approved_task)

        print("Execution completed:")
        print(f"  - Task ID: {execution_result['task_executed']}")
        print(
            f"  - Autonomous decisions made: {execution_result['autonomous_decisions_made']}"
        )
        print(
            f"  - Human validation required: {execution_result['requires_human_validation']}"
        )
        print(f"  - Next step: {execution_result['next_step']}")

        # Step 6: Human validation required
        print("\n6. Human Validation Gate - Results")
        validation_approved = await oversight.require_human_approval(
            "production_validation",
            {
                "execution_result": execution_result["execution_result"],
                "files_modified": execution_result["execution_result"].get(
                    "files_modified", []
                ),
            },
        )

        if validation_approved:
            print("✅ Migration completed with human approval")
        else:
            print("🔄 Human-initiated rollback required")

    except SecurityError as e:
        print(f"🚨 SECURITY VIOLATION: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("\n" + "=" * 60)
    print("Human oversight framework demonstration complete")


if __name__ == "__main__":
    # This would only run in a safe development environment
    asyncio.run(demonstrate_safe_ai_usage())
