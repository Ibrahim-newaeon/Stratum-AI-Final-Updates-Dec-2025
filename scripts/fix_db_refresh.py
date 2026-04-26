#!/usr/bin/env python3
"""Remove unnecessary standalone `await db.refresh(...)` lines from backend Python files."""

import re
from pathlib import Path

BACKEND = Path("backend")

# Match standalone await db.refresh(...) lines (possibly with trailing comment)
REFRESH_RE = re.compile(
    r"^[ \t]*await db\.refresh\([^)]+\)[ \t]*(?:#.*)?(?:\n|$)",
    re.MULTILINE,
)


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    modified, count = REFRESH_RE.subn("", original)
    if modified != original:
        path.write_text(modified, encoding="utf-8")
    return count


def main():
    total = 0
    files = list(BACKEND.rglob("*.py"))

    for f in sorted(files):
        c = process_file(f)
        if c:
            total += c
            print(f"  {f.relative_to(BACKEND)}: {c} removed")

    print(f"\nTotal db.refresh() calls removed: {total}")


if __name__ == "__main__":
    main()
