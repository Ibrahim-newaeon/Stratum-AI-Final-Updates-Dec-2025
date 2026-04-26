#!/usr/bin/env python3
"""Add .limit(1000) to unbounded .order_by() queries in backend endpoints."""

import re
from pathlib import Path

BACKEND = Path("backend/app/api/v1/endpoints")
LIMIT = 1000


def find_unbounded_queries(content: str):
    """Yield (start_idx, end_idx) of .order_by(...) calls that have no .limit() within 5 lines."""
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if ".order_by(" not in line:
            i += 1
            continue

        # Check if .limit() already exists in the next 5 lines
        ahead = "\n".join(lines[i : min(i + 6, len(lines))])
        if ".limit(" in ahead:
            i += 1
            continue

        # Find the end of the order_by expression
        # If the line ends with ), the order_by is complete on this line
        stripped = line.rstrip()
        if stripped.endswith(")"):
            yield i, stripped
            i += 1
            continue

        # Multi-line order_by: find the line that closes it
        paren_depth = line.count("(") - line.count(")")
        j = i + 1
        while j < len(lines) and paren_depth > 0:
            paren_depth += lines[j].count("(") - lines[j].count(")")
            j += 1
        if j <= len(lines):
            closing_line = lines[j - 1].rstrip()
            yield j - 1, closing_line
        i = j


def add_limit_to_file(path: Path) -> int:
    original = content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    replacements = []

    for line_idx, line_text in find_unbounded_queries(content):
        old = line_text
        new = line_text + f".limit({LIMIT})"
        replacements.append((old, new))

    count = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        path.write_text(content, encoding="utf-8")
    return count


def main():
    total = 0
    for f in sorted(BACKEND.glob("*.py")):
        c = add_limit_to_file(f)
        if c:
            total += c
            print(f"  {f.name}: {c} limits added")
    print(f"\nTotal limits added: {total}")


if __name__ == "__main__":
    main()
