#!/usr/bin/env python3
"""
Consolidate intent_classifier.py logging patterns to use UniversalFrameworkLogger
"""

import re


def consolidate_logging():
    file_path = "src/universal_framework/agents/intent_classifier.py"

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Replace inline logger declarations
    content = re.sub(
        r'logger = structlog\.get_logger\("intent_classifier"\)',
        "logger = self.logger",
        content,
    )

    # Remove standalone import structlog lines
    content = re.sub(r"\s*import structlog\s*\n", "", content, flags=re.MULTILINE)

    # Remove any remaining structlog references
    content = re.sub(
        r'structlog\.get_logger\("intent_classifier"\)', "self.logger", content
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ Consolidated intent_classifier logging patterns")


if __name__ == "__main__":
    consolidate_logging()
