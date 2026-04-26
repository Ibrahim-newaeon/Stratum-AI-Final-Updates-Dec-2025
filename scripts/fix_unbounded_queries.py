#!/usr/bin/env python3
"""Add .limit(1000) to unbounded .order_by() queries in backend endpoints."""

import re
from pathlib import Path

BACKEND = Path("backend/app/api/v1/endpoints")
LIMIT = 1000


def add_limit_to_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    lines = original.split("\n")
    modified = []
    count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Pattern 1: select(...).order_by(...) on same line, no .limit() in next 5 lines
        if ".order_by(" in stripped and ".limit(" not in stripped:
            # Look ahead up to 5 lines to see if there's already a .limit()
            ahead = "\n".join(lines[i : min(i + 6, len(lines))])
            if ".limit(" not in ahead:
                # Check if this is part of a multi-line statement
                # Find the closing ) of the order_by call
                # Simple heuristic: if line ends with ) and doesn't continue, add .limit(1000)
                if stripped.endswith(")"):
                    line = line + f".limit({LIMIT})"
                    count += 1
                elif stripped.endswith(")") and stripped.startswith("select("):
                    line = line + f".limit({LIMIT})"
                    count += 1
                else:
                    # Builder pattern: query = query.order_by(...)
                    # Add .limit(1000) at the end of the expression
                    # Check if next non-empty line continues the chain or closes it
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    next_line = lines[j].strip() if j < len(lines) else ""
                    if next_line.startswith(")") or next_line.startswith(".scalar") or next_line.startswith("result"):
                        # The order_by is the last chain before execution
                        line = line + f".limit({LIMIT})"
                        count += 1
            else:
                # There is a .limit() somewhere in the next few lines, check if it's on the same statement
                pass

        modified.append(line)
        i += 1

    result = "\n".join(modified)
    if result != original:
        path.write_text(result, encoding="utf-8")
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
