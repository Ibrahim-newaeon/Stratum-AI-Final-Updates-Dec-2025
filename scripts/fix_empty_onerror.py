#!/usr/bin/env python3
"""Remove empty onError handlers left behind by console removal."""

import re
from pathlib import Path

FILES = [
    Path("frontend/src/api/assets.ts"),
    Path("frontend/src/api/campaigns.ts"),
    Path("frontend/src/api/rules.ts"),
]

EMPTY_ONERROR_RE = re.compile(
    r"[ \t]*onError: \(error: Error\) => \{\s*\},?\s*\n",
    re.MULTILINE,
)


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    modified, count = EMPTY_ONERROR_RE.subn("", original)
    if modified != original:
        path.write_text(modified, encoding="utf-8")
    return count


for f in FILES:
    c = process_file(f)
    print(f"  {f}: {c} empty onError blocks removed")
