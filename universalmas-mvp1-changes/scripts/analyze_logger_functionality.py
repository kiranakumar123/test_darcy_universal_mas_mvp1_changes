#!/usr/bin/env python3
"""
CRITICAL: Analyze functionality gaps before deleting unified_logger.py
This script identifies if ModernUniversalFrameworkLogger has ALL features from the legacy implementation.
"""

import ast
import inspect
import sys
from pathlib import Path


def analyze_unified_logger_methods() -> dict[str, dict]:
    """Extract all public methods from unified_logger.py (if it exists)."""
    # First try the original location
    unified_logger_path = Path(
        "src/universal_framework/observability/unified_logger.py"
    )

    # If not found, try the recovered backup
    if not unified_logger_path.exists():
        unified_logger_path = Path(".temp/recovered_unified_logger.py")
        print("📁 Using recovered unified_logger.py from git history for analysis")

    if not unified_logger_path.exists():
        print("❌ unified_logger.py not found - may have been deleted already")
        print("⚠️  Cannot perform gap analysis without original file")
        return {}

    methods = {}

    try:
        with open(unified_logger_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
            tree = ast.parse(content)

        # Find the UniversalFrameworkLogger class
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "UniversalFrameworkLogger"
            ):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith(
                        "_"
                    ):
                        # Extract method signature info
                        args = []
                        for arg in item.args.args:
                            args.append(arg.arg)

                        methods[item.name] = {
                            "args": args,
                            "line": item.lineno,
                            "docstring": ast.get_docstring(item),
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                        }

    except Exception as e:
        print(f"❌ Error parsing unified_logger.py: {e}")
        return {}

    return methods


def analyze_modern_logger_methods() -> dict[str, dict]:
    """Extract all public methods from ModernUniversalFrameworkLogger."""
    try:
        # Import the modern logger
        sys.path.insert(0, str(Path("src").absolute()))
        from universal_framework.observability.modern_logger import (
            ModernUniversalFrameworkLogger,
        )

        methods = {}

        for name in dir(ModernUniversalFrameworkLogger):
            if not name.startswith("_") and name != "model_config":
                attr = getattr(ModernUniversalFrameworkLogger, name)
                if callable(attr):
                    try:
                        sig = inspect.signature(attr)
                        methods[name] = {
                            "signature": str(sig),
                            "is_async": inspect.iscoroutinefunction(attr),
                            "docstring": inspect.getdoc(attr),
                        }
                    except Exception as e:
                        # Some methods might not be introspectable
                        methods[name] = {
                            "signature": "Unknown",
                            "is_async": False,
                            "docstring": None,
                            "error": str(e),
                        }

        return methods

    except Exception as e:
        print(f"❌ Error analyzing ModernUniversalFrameworkLogger: {e}")
        return {}


def find_functionality_gaps() -> bool:
    """Find methods in legacy that aren't in modern implementation."""
    print("🔍 Analyzing logger functionality gaps...")
    print("=" * 60)

    legacy_methods = analyze_unified_logger_methods()
    modern_methods = analyze_modern_logger_methods()

    if not legacy_methods:
        print("⚠️  Cannot analyze gaps - unified_logger.py not accessible")
        return False

    if not modern_methods:
        print("❌ Cannot analyze ModernUniversalFrameworkLogger")
        return False

    print(f"📊 Legacy methods found: {len(legacy_methods)}")
    print(f"📊 Modern methods found: {len(modern_methods)}")

    legacy_method_names = set(legacy_methods.keys())
    modern_method_names = set(modern_methods.keys())

    missing_methods = legacy_method_names - modern_method_names
    new_methods = modern_method_names - legacy_method_names

    # Report findings
    if missing_methods:
        print(
            f"\n🚨 BLOCKING ISSUES: {len(missing_methods)} methods missing from modern implementation:"
        )
        for method in sorted(missing_methods):
            legacy_info = legacy_methods[method]
            print(
                f"  - {method}({', '.join(legacy_info['args'][1:])})  # Line {legacy_info['line']}"
            )
            if legacy_info["docstring"]:
                print(f"    → {legacy_info['docstring'][:80]}...")

        print("\n❌ CANNOT DELETE unified_logger.py - functionality gaps exist")
        return False

    if new_methods:
        print(f"\n✨ {len(new_methods)} new methods in modern implementation:")
        for method in sorted(new_methods):
            print(f"  + {method}{modern_methods[method]['signature']}")

    # Check method signature compatibility for common methods
    common_methods = legacy_method_names.intersection(modern_method_names)
    signature_mismatches = []

    for method in common_methods:
        legacy_args = legacy_methods[method]["args"][1:]  # Skip 'self'
        modern_sig = modern_methods[method]["signature"]

        # Simple signature comparison (could be enhanced)
        if len(legacy_args) > 0:
            # Check if basic argument count seems compatible
            modern_arg_count = modern_sig.count(",") + (
                1 if "(" in modern_sig and ")" in modern_sig else 0
            )
            if modern_sig.strip() == "()":
                modern_arg_count = 0

            if len(legacy_args) > modern_arg_count + 2:  # Allow some flexibility
                signature_mismatches.append(
                    {
                        "method": method,
                        "legacy_args": legacy_args,
                        "modern_sig": modern_sig,
                    }
                )

    if signature_mismatches:
        print(f"\n⚠️  {len(signature_mismatches)} potential signature mismatches:")
        for mismatch in signature_mismatches:
            print(
                f"  - {mismatch['method']}: legacy({', '.join(mismatch['legacy_args'])}) vs modern{mismatch['modern_sig']}"
            )

    print(
        f"\n✅ All {len(legacy_method_names)} legacy methods available in modern implementation"
    )
    if signature_mismatches:
        print("⚠️  Review signature mismatches before proceeding")
        return False

    return True


def analyze_import_dependencies():
    """Analyze what other files depend on unified_logger.py."""
    print("\n🔍 Analyzing import dependencies...")

    # Check if any files still import from unified_logger
    import subprocess

    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "from.*unified_logger.*import", "src/"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.stdout:
            print("❌ Files still importing from unified_logger:")
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
            return False
        else:
            print("✅ No direct imports from unified_logger found")
            return True

    except FileNotFoundError:
        # grep not available on Windows, use Python approach
        print("🔍 Using Python-based import analysis (grep unavailable)...")

        from pathlib import Path

        python_files = list(Path("src").rglob("*.py"))
        problematic_files = []

        for file_path in python_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    if (
                        "from.*unified_logger.*import" in content
                        or "unified_logger.py" in content
                    ):
                        problematic_files.append(str(file_path))
            except Exception:
                continue

        if problematic_files:
            print("❌ Files still importing from unified_logger:")
            for file_path in problematic_files:
                print(f"  {file_path}")
            return False
        else:
            print("✅ No direct imports from unified_logger found")
            return True


def main():
    """Main analysis function."""
    print("🚨 CRITICAL: Pre-deletion validation for unified_logger.py")
    print("This analysis determines if it's safe to delete the legacy file")
    print("=" * 70)

    # Step 1: Check functionality gaps
    functionality_ok = find_functionality_gaps()

    # Step 2: Check import dependencies
    imports_ok = analyze_import_dependencies()

    # Final assessment
    print("\n" + "=" * 70)
    print("📋 FINAL ASSESSMENT:")

    if functionality_ok and imports_ok:
        print("✅ SAFE to delete unified_logger.py")
        print("   • All legacy methods available in modern implementation")
        print("   • No files importing directly from unified_logger")
        print("   • Proceed with deletion and integration testing")
    else:
        print("❌ UNSAFE to delete unified_logger.py")
        if not functionality_ok:
            print("   • Missing functionality in modern implementation")
        if not imports_ok:
            print("   • Files still importing from legacy unified_logger")
        print("   • Fix issues above before attempting deletion")

    return functionality_ok and imports_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
