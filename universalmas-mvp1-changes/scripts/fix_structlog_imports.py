#!/usr/bin/env python3
"""
Quick fix script for remaining structlog usage issues after migration.
"""

import re
from pathlib import Path


def fix_structlog_usage():
    """Fix remaining structlog.get_logger() usage without imports."""

    src_dir = Path("src")
    if not src_dir.exists():
        print("❌ 'src' directory not found")
        return

    python_files = list(src_dir.glob("**/*.py"))

    # Skip files that should keep direct structlog usage
    skip_files = [
        "core/logging_foundation.py",
        "protocols.py",
        "structured_logger.py",
        "modern_logger.py",
    ]

    fixed_files = 0

    for file_path in python_files:
        if any(skip_file in str(file_path) for skip_file in skip_files):
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        original_content = content

        # Check if file uses structlog.get_logger but doesn't import structlog
        if "structlog.get_logger" in content and "import structlog" not in content:
            # Add the import and modify usage
            has_safe_logger_import = (
                "from universal_framework.core.logging_foundation import get_safe_logger"
                in content
            )

            if not has_safe_logger_import:
                # Add the import after other imports
                import_lines = []
                other_lines = []
                in_imports = True

                for line in content.split("\n"):
                    if in_imports and (
                        line.startswith("import ")
                        or line.startswith("from ")
                        or line.strip() == ""
                        or line.startswith("#")
                        or line.startswith('"""')
                        or line.startswith("'''")
                    ):
                        import_lines.append(line)
                    else:
                        if in_imports:
                            # Add our import before the first non-import line
                            import_lines.append(
                                "from universal_framework.core.logging_foundation import get_safe_logger"
                            )
                            in_imports = False
                        other_lines.append(line)

                content = "\n".join(import_lines) + "\n" + "\n".join(other_lines)

            # Replace structlog.get_logger() calls with get_safe_logger()
            content = re.sub(
                r"structlog\.get_logger\((.*?)\)", r"get_safe_logger(\1)", content
            )
            content = re.sub(
                r"get_safe_logger\(\)", "get_safe_logger(__name__)", content
            )

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Fixed {file_path}")
                fixed_files += 1

    print(f"\n🎉 Fixed {fixed_files} files with structlog usage issues")


if __name__ == "__main__":
    fix_structlog_usage()
