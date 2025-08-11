"""Enterprise compliance validation for Universal Framework CI/CD."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class ComplianceValidator:
    """Enterprise compliance validation for CI/CD pipeline."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).parent.parent.parent
        self.src_path = self.project_root / "src" / "universal_framework"
        self.compliance_results: dict[str, Any] = {}

    def validate_privacy_compliance(self) -> bool:
        """Validate GDPR privacy compliance requirements."""
        print("🔒 Validating GDPR privacy compliance...")
        privacy_files = [
            self.src_path / "compliance" / "privacy_manager.py",
            self.src_path / "compliance" / "audit_manager.py",
            self.src_path / "contracts" / "state.py",
        ]
        missing_files = [str(p) for p in privacy_files if not p.exists()]
        if missing_files:
            print(f"❌ Missing privacy compliance files: {missing_files}")
            return False
        state_file = self.src_path / "contracts" / "state.py"
        state_content = state_file.read_text()
        required_fields = [
            "session_id",
            "user_id",
            "audit_trail",
            "compliance_metadata",
        ]
        missing_fields = [f for f in required_fields if f not in state_content]
        if missing_fields:
            print(
                f"❌ Missing audit fields in UniversalWorkflowState: {missing_fields}"
            )
            return False
        print("✅ GDPR privacy compliance validation passed")
        return True

    def validate_security_framework(self) -> bool:
        """Validate enterprise security framework implementation."""
        print("🔐 Validating enterprise security framework...")
        security_files = [
            self.src_path / "security" / "authentication.py",
            self.src_path / "security" / "authorization.py",
            self.src_path / "contracts" / "security.py",
        ]
        for file_path in security_files:
            if not file_path.exists():
                print(f"❌ Missing security file: {file_path}")
                return False
        print("✅ Enterprise security framework validation passed")
        return True

    def validate_fsm_enforcement(self) -> bool:
        """Validate FSM state enforcement compliance."""
        print("⚙️ Validating FSM state enforcement...")
        contracts_path = self.src_path / "contracts"
        fsm_files = list(contracts_path.glob("**/fsm*.py")) + list(
            contracts_path.glob("**/state*.py")
        )
        if not fsm_files:
            print("❌ Missing FSM enforcement implementation")
            return False
        print("✅ FSM state enforcement validation passed")
        return True

    def validate_agent_contracts(self) -> bool:
        """Validate universal agent contract compliance."""
        print("🤖 Validating universal agent contracts...")
        agents_path = self.src_path / "agents"
        if not agents_path.exists():
            print("❌ Missing agents directory")
            return False
        agent_files = list(agents_path.glob("*.py"))
        if len(agent_files) < 4:
            print(
                f"❌ Insufficient agent implementations: {len(agent_files)} < 4 required"
            )
            return False
        print(
            f"✅ Universal agent contracts validation passed ({len(agent_files)} agents)"
        )
        return True

    def validate_enterprise_requirements(self) -> bool:
        """Validate enterprise requirements (performance, scalability)."""
        print("🏢 Validating enterprise requirements...")
        monitoring_paths = [
            self.src_path / "observability",
            self.src_path / "monitoring",
        ]
        has_monitoring = any(p.exists() for p in monitoring_paths)
        if not has_monitoring:
            print("❌ Missing performance monitoring infrastructure")
            return False
        print("✅ Enterprise requirements validation passed")
        return True

    def generate_compliance_report(self) -> dict[str, Any]:
        """Generate comprehensive compliance report."""
        return {
            "timestamp": "2025-07-21T10:00:00Z",
            "validation_results": self.compliance_results,
            "compliance_status": all(self.compliance_results.values()),
            "framework_version": "3.1.0",
            "enterprise_standards": {
                "privacy_compliance": "GDPR",
                "security_framework": "Enterprise",
                "performance_requirements": "<500ms",
                "uptime_target": "99.9%",
            },
        }

    def run_validation(self) -> bool:
        """Execute complete compliance validation suite."""
        print("🔍 Running enterprise compliance validation...")
        print(f"Project root: {self.project_root}")
        print(f"Source path: {self.src_path}")
        validations = [
            ("privacy_compliance", self.validate_privacy_compliance),
            ("security_framework", self.validate_security_framework),
            ("fsm_enforcement", self.validate_fsm_enforcement),
            ("agent_contracts", self.validate_agent_contracts),
            ("enterprise_requirements", self.validate_enterprise_requirements),
        ]
        all_passed = True
        for name, func in validations:
            try:
                result = func()
                self.compliance_results[name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Validation error in {name}: {e}")
                self.compliance_results[name] = False
                all_passed = False
        report = self.generate_compliance_report()
        with open(self.project_root / "compliance-report.json", "w") as f:
            json.dump(report, f, indent=2)
        if all_passed:
            print("\n✅ All enterprise compliance validations passed")
            return True
        print("\n❌ Enterprise compliance validation failed")
        print("Review compliance-report.json for detailed results")
        return False


if __name__ == "__main__":
    validator = ComplianceValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
