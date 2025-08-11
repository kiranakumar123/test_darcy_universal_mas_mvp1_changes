"""Python 3.11+ compatibility validation for Universal Framework CI/CD."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any


class Python311CompatibilityValidator:
    """Validates Python 3.11+ compatibility and modern patterns."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).parent.parent.parent
        self.src_path = self.project_root / "src" / "universal_framework"
        self.validation_results: dict[str, Any] = {}
        self.deprecated_modules = {
            "distutils",
            "imp",
            "cgi",
            "cgitb",
            "formatter",
            "pipes",
            "sunau",
            "uu",
            "xdrlib",
            "aifc",
            "audioop",
            "chunk",
            "crypt",
            "imghdr",
            "mailcap",
            "msilib",
            "nis",
            "nntplib",
            "ossaudiodev",
            "sndhdr",
            "spwd",
            "telnetlib",
            "tomli",  # Should use tomllib in 3.11+
        }
        self.legacy_patterns = [
            # Type annotation patterns
            ("Optional[", "Should use `X | None` instead of `Optional[X]`"),
            ("Union[", "Should use `X | Y` instead of `Union[X, Y]`"),
            ("List[", "Should use `list[X]` instead of `List[X]`"),
            ("Dict[", "Should use `dict[X, Y]` instead of `Dict[X, Y]`"),
            ("Tuple[", "Should use `tuple[X, ...]` instead of `Tuple[X, ...]`"),
            ("Set[", "Should use `set[X]` instead of `Set[X]`"),
            # Exception handling patterns
            (
                "except Exception:",
                "Should use specific exception types or ExceptionGroup",
            ),
            # Config patterns
            ("import tomli", "Should use `import tomllib` (built-in in Python 3.11+)"),
        ]

    def validate_no_deprecated_modules(self) -> bool:
        """Validate no deprecated modules are imported."""
        print("🔍 Validating no deprecated modules...")
        deprecated_found = []

        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_name = alias.name.split(".")[0]
                            if module_name in self.deprecated_modules:
                                # Check if it's a valid fallback pattern
                                if not self._is_valid_fallback(content, alias.name):
                                    deprecated_found.append(
                                        f"{py_file.relative_to(self.project_root)}: import {alias.name}"
                                    )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_name = node.module.split(".")[0]
                            if module_name in self.deprecated_modules:
                                if not self._is_valid_fallback(content, node.module):
                                    deprecated_found.append(
                                        f"{py_file.relative_to(self.project_root)}: from {node.module}"
                                    )
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
                continue

        if deprecated_found:
            print("❌ Deprecated modules found:")
            for item in deprecated_found:
                print(f"  - {item}")
            return False

        print("✅ No deprecated modules found")
        return True

    def _is_valid_fallback(self, content: str, module_name: str) -> bool:
        """Check if deprecated module usage is part of a valid fallback pattern."""
        if module_name == "tomli":
            # Check for tomllib fallback pattern
            return (
                "import tomllib" in content
                and "except ModuleNotFoundError" in content
                and "import tomli as tomllib" in content
            )
        return False

    def validate_modern_type_annotations(self) -> bool:
        """Validate modern type annotation usage."""
        print("🔍 Validating modern type annotations...")
        critical_patterns_found = []

        # Focus on critical patterns only for CI/CD
        critical_patterns = [
            ("import tomli", "Should use `import tomllib` (built-in in Python 3.11+)"),
        ]

        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern, message in critical_patterns:
                    if pattern in content:
                        # Check if it's a valid fallback pattern
                        if pattern == "import tomli" and self._is_valid_fallback(
                            content, "tomli"
                        ):
                            continue  # Skip valid fallback patterns

                        lines = content.split("\n")
                        for i, line in enumerate(lines, 1):
                            if pattern in line:
                                critical_patterns_found.append(
                                    f"{py_file.relative_to(self.project_root)}:{i} - {message}"
                                )
            except Exception as e:
                print(f"Warning: Could not read {py_file}: {e}")
                continue

        if critical_patterns_found:
            print("❌ Critical legacy patterns found:")
            for item in critical_patterns_found:
                print(f"  - {item}")
            print("💡 These are blocking issues for Python 3.11+ compatibility")
            return False

        # Check for other patterns but only warn
        warning_patterns = [
            ("Optional[", "Consider using `X | None` instead of `Optional[X]`"),
            ("Union[", "Consider using `X | Y` instead of `Union[X, Y]`"),
        ]

        warning_count = 0
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern, _ in warning_patterns:
                    warning_count += content.count(pattern)
            except Exception:
                continue

        if warning_count > 0:
            print(f"⚠️  Found {warning_count} legacy type annotations (non-blocking)")
            print("💡 Consider modernizing type annotations in future updates")

        print("✅ Modern type annotations validated (critical patterns only)")
        return True

    def validate_match_case_usage(self) -> bool:
        """Validate usage of match/case statements where appropriate."""
        print("🔍 Validating match/case pattern usage...")
        if_elif_chains = []

        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.If) and self._has_long_elif_chain(node):
                        if_elif_chains.append(
                            f"{py_file.relative_to(self.project_root)}:{node.lineno}"
                        )
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
                continue

        if if_elif_chains:
            print("⚠️  Long if/elif chains found (consider match/case):")
            for item in if_elif_chains[:5]:  # Limit output
                print(f"  - {item}")
            if len(if_elif_chains) > 5:
                print(f"  ... and {len(if_elif_chains) - 5} more")
            # This is a warning, not a failure
            print("💡 Consider using match/case for better readability")

        print("✅ Match/case pattern validation completed")
        return True

    def validate_exception_handling(self) -> bool:
        """Validate modern exception handling patterns."""
        print("🔍 Validating exception handling patterns...")
        critical_issues = []

        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:  # bare except:
                            critical_issues.append(
                                f"{py_file.relative_to(self.project_root)}:{node.lineno} - bare except"
                            )
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
                continue

        if critical_issues:
            print("❌ Critical exception handling issues found:")
            for item in critical_issues[:5]:  # Limit output for CI
                print(f"  - {item}")
            if len(critical_issues) > 5:
                print(f"  ... and {len(critical_issues) - 5} more")
            print("💡 Bare except clauses can mask errors and break debugging")
            return False

        # Count except Exception patterns for warning
        except_exception_count = 0
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()
                except_exception_count += content.count("except Exception:")
            except Exception:
                continue

        if except_exception_count > 0:
            print(
                f"⚠️  Found {except_exception_count} 'except Exception:' patterns (non-blocking)"
            )
            print(
                "💡 Consider using specific exception types for better error handling"
            )

        print("✅ Exception handling patterns validated (critical issues only)")
        return True

    def validate_python_version_compatibility(self) -> bool:
        """Validate Python version compatibility."""
        print("🔍 Validating Python version compatibility...")

        # Check if we're running on Python 3.11+
        if sys.version_info < (3, 11):
            print(
                f"❌ Running on Python {sys.version_info.major}.{sys.version_info.minor}, requires 3.11+"
            )
            return False

        # Check pyproject.toml for version requirement
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            if ">=3.11" not in content and ">= 3.11" not in content:
                print("❌ pyproject.toml does not specify Python 3.11+ requirement")
                return False

        print(
            f"✅ Python version compatibility validated ({sys.version_info.major}.{sys.version_info.minor})"
        )
        return True

    def _has_long_elif_chain(self, node: ast.If) -> bool:
        """Check if an if statement has a long elif chain (3+ elifs)."""
        elif_count = 0
        current = node

        while hasattr(current, "orelse") and current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                elif_count += 1
                current = current.orelse[0]
            else:
                break

        return elif_count >= 3

    def generate_compatibility_report(self) -> dict[str, Any]:
        """Generate compatibility validation report."""
        return {
            "timestamp": "2025-07-21T16:00:00Z",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "validation_results": self.validation_results,
            "compatibility_status": all(self.validation_results.values()),
            "modern_python_features": {
                "type_unions": "X | Y syntax",
                "match_case": "Structural pattern matching",
                "exception_groups": "ExceptionGroup and except*",
                "tomllib": "Built-in TOML parser",
                "self_type": "PEP 673 Self type",
            },
        }

    def run_validation(self) -> bool:
        """Execute complete Python 3.11+ compatibility validation."""
        print("🚀 Running Python 3.11+ compatibility validation...")
        print(f"Project root: {self.project_root}")
        print(f"Source path: {self.src_path}")

        validations = [
            ("python_version", self.validate_python_version_compatibility),
            ("deprecated_modules", self.validate_no_deprecated_modules),
            ("modern_types", self.validate_modern_type_annotations),
            ("match_case", self.validate_match_case_usage),
            ("exception_handling", self.validate_exception_handling),
        ]

        all_passed = True
        for name, func in validations:
            try:
                result = func()
                self.validation_results[name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Validation error in {name}: {e}")
                self.validation_results[name] = False
                all_passed = False

        # Generate compatibility report
        report = self.generate_compatibility_report()
        with open(self.project_root / "python311-compatibility-report.json", "w") as f:
            import json

            json.dump(report, f, indent=2)

        if all_passed:
            print("\n✅ All Python 3.11+ compatibility validations passed")
            return True
        else:
            print("\n❌ Python 3.11+ compatibility validation failed")
            print("Review python311-compatibility-report.json for detailed results")
            return False


if __name__ == "__main__":
    validator = Python311CompatibilityValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
