#!/usr/bin/env python3
"""Remove console.log / console.warn / console.error standalone statements from frontend source files.
Skips legitimate logging infrastructure files."""

import re
from pathlib import Path

FRONTEND_SRC = Path("frontend/src")

# Files/paths to skip (legitimate logging infrastructure)
SKIP_PATTERNS = [
    "lib/sentry.ts",
    "lib/logger",
    "utils/logger",
    "utils/pdfExport.ts",  # may use console intentionally for PDF debug
]

CONSOLE_RE = re.compile(
    r"^[ \t]*console\.(log|warn|error)\([^;]*\);?[ \t]*(?:\n|$)",
    re.MULTILINE,
)


def should_skip(path: Path) -> bool:
    rel = path.as_posix()
    return any(p in rel for p in SKIP_PATTERNS)


def process_file(path: Path) -> int:
    if should_skip(path):
        return 0
    original = path.read_text(encoding="utf-8")
    modified, count = CONSOLE_RE.subn("", original)
    if modified != original:
        path.write_text(modified, encoding="utf-8")
    return count


def main():
    total = 0
    files = []
    for ext in ("*.tsx", "*.ts"):
        files.extend(FRONTEND_SRC.rglob(ext))

    for f in sorted(files):
        c = process_file(f)
        if c:
            total += c
            print(f"  {f.relative_to(FRONTEND_SRC)}: {c} removed")

    print(f"\nTotal console statements removed: {total}")


if __name__ == "__main__":
    main()
