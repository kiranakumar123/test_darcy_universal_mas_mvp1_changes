#!/usr/bin/env python3
"""
Script to find and update all old logger usage in the codebase.
Run this to ensure all code uses the new modular logger.
"""
import re
import sys
from pathlib import Path


def find_old_logger_imports():
    """Find all files that need logger import updates."""

    old_patterns = [
        (
            r"from.*\.observability\.unified_logger.*import.*UniversalFrameworkLogger",
            "Old unified_logger import",
        ),
        (r"from.*compliance.*import.*PrivacySafeLogger", "Direct compliance import"),
        (
            r"UniversalFrameworkLogger\([^,]+,\s*privacy_config=",
            "Old privacy_config parameter",
        ),
        (
            r"from.*\.observability.*import.*PrivacySafeLogger",
            "Direct PrivacySafeLogger import",
        ),
        (
            r"\.privacy_logger\s*=.*PrivacySafeLogger\(",
            "Direct privacy logger instantiation",
        ),
    ]

    src_dir = Path("src")
    if not src_dir.exists():
        print("❌ 'src' directory not found. Run from project root.")
        return []

    python_files = list(src_dir.glob("**/*.py"))
    issues = []

    for file_path in python_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern, description in old_patterns:
                if re.search(pattern, line):
                    issues.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip(),
                            "issue": description,
                        }
                    )

    return issues


def find_circular_import_risks():
    """Find potential circular import issues."""

    risky_patterns = [
        (r"from.*\.compliance.*import", "Compliance import (potential circular)"),
        (r"from.*\.observability.*unified_logger.*import", "Old unified_logger import"),
        (r"import.*structlog.*", "Direct structlog import (should use safe_logger)"),
    ]

    src_dir = Path("src")
    python_files = list(src_dir.glob("**/*.py"))
    risks = []

    for file_path in python_files:
        # Skip the files we know are safe
        if any(
            safe_name in str(file_path)
            for safe_name in [
                "protocols.py",
                "langsmith_tracer.py",
                "structured_logger.py",
                "modern_logger.py",
                "core/logging_foundation.py",
            ]
        ):
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern, description in risky_patterns:
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    risks.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip(),
                            "risk": description,
                        }
                    )

    return risks


def suggest_fixes():
    """Suggest fixes for common migration patterns."""

    suggestions = {
        "Old unified_logger import": """
# OLD:
from .observability.unified_logger import UniversalFrameworkLogger

# NEW:
from .observability import UniversalFrameworkLogger
        """,
        "Direct compliance import": """
# OLD:
from ..compliance import PrivacySafeLogger
logger.privacy_logger = PrivacySafeLogger(config)

# NEW:
# Use dependency injection instead:
from .observability.protocols import PrivacyFilterProtocol

def __init__(self, privacy_filter: Optional[PrivacyFilterProtocol] = None):
    self._privacy_filter = privacy_filter
        """,
        "Old privacy_config parameter": """
# OLD:
UniversalFrameworkLogger("component", privacy_config={...})

# NEW:
UniversalFrameworkLogger("component")
# Privacy filtering now handled via protocol injection
        """,
        "Direct structlog import": """
# OLD:
import structlog
logger = structlog.get_logger()

# NEW:
from ..core.logging_foundation import get_safe_logger
logger = get_safe_logger("component_name")
        """,
    }

    return suggestions


def auto_fix_imports(file_path: Path, content: str) -> tuple[str, list[str]]:
    """Automatically fix common import patterns."""

    changes = []
    modified_content = content

    # Fix 1: Update unified_logger imports
    old_import_pattern = (
        r"from\s+.*\.observability\.unified_logger\s+import\s+UniversalFrameworkLogger"
    )
    new_import = (
        "from universal_framework.observability import UniversalFrameworkLogger"
    )

    if re.search(old_import_pattern, modified_content):
        modified_content = re.sub(old_import_pattern, new_import, modified_content)
        changes.append("Updated unified_logger import to use new modular API")

    # Fix 2: Remove privacy_config parameters
    privacy_config_pattern = (
        r"UniversalFrameworkLogger\(([^,)]+),\s*privacy_config\s*=[^,)]+\)"
    )
    privacy_config_replacement = r"UniversalFrameworkLogger(\1)"

    if re.search(privacy_config_pattern, modified_content):
        modified_content = re.sub(
            privacy_config_pattern, privacy_config_replacement, modified_content
        )
        changes.append("Removed deprecated privacy_config parameter")

    # Fix 3: Remove direct compliance imports
    compliance_import_patterns = [
        (
            r"from\s+.*\.compliance\s+import\s+PrivacySafeLogger[^\n]*\n",
            "# Privacy logging now handled via dependency injection\n",
        ),
        (
            r"from\s+.*\.compliance\.privacy_logger\s+import\s+PrivacySafeLogger[^\n]*\n",
            "# Privacy logging now handled via dependency injection\n",
        ),
    ]

    for pattern, replacement in compliance_import_patterns:
        if re.search(pattern, modified_content):
            modified_content = re.sub(pattern, replacement, modified_content)
            changes.append(
                "Removed direct compliance import (replaced with dependency injection)"
            )

    # Fix 4: Replace direct PrivacySafeLogger instantiation
    privacy_logger_pattern = r"self\.privacy_logger\s*=\s*PrivacySafeLogger\([^)]*\)"
    privacy_logger_replacement = (
        "# Privacy logging now handled by UniversalFrameworkLogger"
    )

    if re.search(privacy_logger_pattern, modified_content):
        modified_content = re.sub(
            privacy_logger_pattern, privacy_logger_replacement, modified_content
        )
        changes.append("Removed direct PrivacySafeLogger instantiation")

    # Fix 5: Replace direct structlog imports in non-core files
    if "core/logging_foundation.py" not in str(file_path) and "protocols.py" not in str(
        file_path
    ):
        structlog_pattern = r"import\s+structlog\n"
        structlog_replacement = (
            "from universal_framework.core.logging_foundation import get_safe_logger\n"
        )

        if re.search(structlog_pattern, modified_content):
            modified_content = re.sub(
                structlog_pattern, structlog_replacement, modified_content
            )
            changes.append("Replaced direct structlog import with safe_logger")

    return modified_content, changes


def apply_auto_fixes():
    """Apply automatic fixes to common migration patterns."""

    src_dir = Path("src")
    if not src_dir.exists():
        print("❌ 'src' directory not found. Run from project root.")
        return 0

    python_files = list(src_dir.glob("**/*.py"))
    total_files_changed = 0
    total_changes = 0

    for file_path in python_files:
        # Skip certain files that should not be auto-modified
        skip_files = [
            "protocols.py",
            "core/logging_foundation.py",
            "modern_logger.py",
            "structured_logger.py",
            "langsmith_tracer.py",
            "__init__.py",
        ]

        if any(skip_file in str(file_path) for skip_file in skip_files):
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()
        except UnicodeDecodeError:
            continue

        modified_content, changes = auto_fix_imports(file_path, original_content)

        if changes:
            # Write the modified content back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)

            total_files_changed += 1
            total_changes += len(changes)

            print(f"📝 Fixed {file_path}:")
            for change in changes:
                print(f"   • {change}")
            print()

    return total_files_changed, total_changes

    # Find old logger imports
    issues = find_old_logger_imports()

    if issues:
        print(f"❌ Found {len(issues)} old logger usage patterns:")
        print()

        # Group by issue type
        by_issue = {}
        for issue in issues:
            issue_type = issue["issue"]
            if issue_type not in by_issue:
                by_issue[issue_type] = []
            by_issue[issue_type].append(issue)

        for issue_type, issue_list in by_issue.items():
            print(f"📋 {issue_type}: {len(issue_list)} instances")
            for issue in issue_list[:3]:  # Show first 3 examples
                print(f"   {issue['file']}:{issue['line']} - {issue['content']}")
            if len(issue_list) > 3:
                print(f"   ... and {len(issue_list) - 3} more")
            print()
    else:
        print("✅ No old logger usage patterns found!")

    # Find circular import risks
    print("🔍 Checking for circular import risks...")
    risks = find_circular_import_risks()

    if risks:
        print(f"⚠️  Found {len(risks)} potential circular import risks:")
        print()

        by_risk = {}
        for risk in risks:
            risk_type = risk["risk"]
            if risk_type not in by_risk:
                by_risk[risk_type] = []
            by_risk[risk_type].append(risk)

        for risk_type, risk_list in by_risk.items():
            print(f"📋 {risk_type}: {len(risk_list)} instances")
            for risk in risk_list[:3]:
                print(f"   {risk['file']}:{risk['line']} - {risk['content']}")
            if len(risk_list) > 3:
                print(f"   ... and {len(risk_list) - 3} more")
            print()
    else:
        print("✅ No circular import risks detected!")

    # Show suggestions if issues found
    if issues or risks:
        print("=" * 60)
        print("💡 SUGGESTED FIXES:")
        print()

        suggestions = suggest_fixes()
        all_issue_types = set(issue["issue"] for issue in issues) | set(
            risk["risk"] for risk in risks
        )

        for issue_type in all_issue_types:
            if issue_type in suggestions:
                print(f"🔧 {issue_type}:")
                print(suggestions[issue_type])
                print()

    # Summary
    total_issues = len(issues) + len(risks)
    print("=" * 60)
    print("📊 MIGRATION SUMMARY:")
    print(f"   Old logger patterns: {len(issues)}")
    print(f"   Circular import risks: {len(risks)}")
    print(f"   Total issues to fix: {total_issues}")
    print()

    if total_issues == 0:
        print("🎉 MIGRATION COMPLETE - No issues found!")
        print("✅ Codebase is ready for the new modular logging architecture!")
    else:
        print("📝 ACTION REQUIRED:")
        print("   1. Review the issues listed above")
        print("   2. Apply the suggested fixes")
        print("   3. Run integration tests to validate changes")
        print("   4. Re-run this script to verify all issues resolved")


def analyze_legacy_usage():
    """Analyze all legacy usage patterns and return summary."""

    print("🔍 Scanning for legacy logger patterns...")

    # Get all issues
    import_issues = find_old_logger_imports()
    circular_risks = find_circular_import_risks()

    # Combine and analyze
    all_issues = import_issues + circular_risks
    pattern_summary = {}

    for issue in all_issues:
        issue_type = issue.get("issue") or issue.get("risk")
        pattern_summary[issue_type] = pattern_summary.get(issue_type, 0) + 1

    # Get file counts
    files_with_issues = set()
    for issue in all_issues:
        files_with_issues.add(issue["file"])

    print(
        f"✅ Analysis complete: {len(all_issues)} patterns found in {len(files_with_issues)} files"
    )

    return {
        "issues": all_issues,
        "pattern_summary": pattern_summary,
        "total_patterns": len(all_issues),
        "files_with_patterns": len(files_with_issues),
        "import_issues": import_issues,
        "circular_risks": circular_risks,
    }


def main():
    """Main migration function - analyze first, then apply fixes."""

    print("🔍 Analyzing codebase for old logger usage...")
    print("=" * 60)

    analysis_results = analyze_legacy_usage()

    if analysis_results["total_patterns"] == 0:
        print("✅ No legacy patterns found. Codebase is already using modern logging!")
        return

    print("\n📊 Migration Analysis Summary:")
    print(f"   • Files with legacy patterns: {analysis_results['files_with_patterns']}")
    print(f"   • Total patterns to migrate: {analysis_results['total_patterns']}")

    # Show top patterns
    if analysis_results["pattern_summary"]:
        print("\n🔍 Most Common Patterns:")
        for pattern, count in sorted(
            analysis_results["pattern_summary"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:
            print(f"   • {pattern}: {count} occurrences")

    # Ask for confirmation before applying fixes
    print("\n" + "=" * 60)

    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-fix":
        response = "y"
        print("🚀 Auto-fix mode enabled - applying fixes automatically...")
    else:
        response = input("🚀 Apply automatic fixes? (y/N): ").strip().lower()

    if response == "y":
        print("\n🔧 Applying automatic fixes...")
        files_changed, total_changes = apply_auto_fixes()

        if files_changed > 0:
            print("\n✅ Migration completed!")
            print(f"   • Files modified: {files_changed}")
            print(f"   • Total changes: {total_changes}")
            print("\n🔍 Re-running analysis to verify fixes...")

            # Re-analyze to show remaining issues
            remaining_results = analyze_legacy_usage()
            if remaining_results["total_patterns"] > 0:
                print(
                    f"\n⚠️ {remaining_results['total_patterns']} patterns still need manual attention."
                )
            else:
                print("\n🎉 All patterns successfully migrated!")
        else:
            print("\n ℹ️ No automatic fixes were applicable.")
    else:
        print("\n ℹ️ Migration cancelled. Run again when ready to apply fixes.")


if __name__ == "__main__":
    main()
