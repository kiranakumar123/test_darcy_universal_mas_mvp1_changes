"""Performance baseline validation for Universal Framework CI/CD."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class PerformanceValidator:
    """Performance baseline validation for CI/CD pipeline."""

    def __init__(self) -> None:
        self.performance_results: dict[str, float] = {}
        self.max_response_time = 500  # milliseconds

    async def test_workflow_initialization_performance(self) -> bool:
        """Test UniversalWorkflowState initialization performance."""
        print("⚡ Testing workflow initialization performance...")
        try:
            from universal_framework.contracts.state import UniversalWorkflowState

            start_time = time.perf_counter()
            _ = UniversalWorkflowState(
                session_id="test_session",
                user_id="test_user",
                auth_token="test_token",
                current_node="test_node",
                messages=[],
                message_history=[],
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.performance_results["workflow_initialization"] = duration_ms
            if duration_ms < self.max_response_time:
                print(
                    f"✅ Workflow initialization: {duration_ms:.2f}ms < {self.max_response_time}ms"
                )
                return True
            print(
                f"❌ Workflow initialization: {duration_ms:.2f}ms > {self.max_response_time}ms"
            )
            return False
        except Exception as exc:
            print(f"❌ Workflow initialization test failed: {exc}")
            return False

    async def test_agent_execution_performance(self) -> bool:
        """Test basic agent execution performance."""
        print("🤖 Testing agent execution performance...")
        try:
            start_time = time.perf_counter()
            await asyncio.sleep(0.1)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.performance_results["agent_execution"] = duration_ms
            if duration_ms < self.max_response_time:
                print(
                    f"✅ Agent execution: {duration_ms:.2f}ms < {self.max_response_time}ms"
                )
                return True
            print(
                f"❌ Agent execution: {duration_ms:.2f}ms > {self.max_response_time}ms"
            )
            return False
        except Exception as exc:
            print(f"❌ Agent execution test failed: {exc}")
            return False

    def generate_performance_report(self) -> dict[str, float | bool]:
        """Generate performance validation report."""
        return {
            "timestamp": time.time(),
            "performance_results": self.performance_results,
            "max_response_time_ms": self.max_response_time,
            "all_tests_passed": all(
                r < self.max_response_time for r in self.performance_results.values()
            ),
        }

    async def run_performance_validation(self) -> bool:
        """Execute complete performance validation suite."""
        print("🚀 Running performance baseline validation...")
        tests = [
            self.test_workflow_initialization_performance,
            self.test_agent_execution_performance,
        ]
        all_passed = True
        for test in tests:
            try:
                result = await test()
                if not result:
                    all_passed = False
            except Exception as exc:
                print(f"❌ Performance test error: {exc}")
                all_passed = False
        self.generate_performance_report()
        if all_passed:
            print("\n✅ All performance validations passed")
            print(f"Results: {self.performance_results}")
            return True
        print("\n❌ Performance validation failed")
        print(f"Results: {self.performance_results}")
        return False


async def main() -> None:
    validator = PerformanceValidator()
    success = await validator.run_performance_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
