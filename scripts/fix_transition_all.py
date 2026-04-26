#!/usr/bin/env python3
"""
Smart replacement of `transition-all` with specific Tailwind transition utilities.
Analyzes className context to pick the right replacement.
"""

import re
from pathlib import Path

FRONTEND_SRC = Path("frontend/src")

# Patterns that suggest which transition utility to use
TRANSFORM_HINTS = [
    r"\bscale-\d+", r"\bscale-\[", r"hover:scale-",
    r"\btranslate-", r"\brotate-", r"\bskew-",
    r"\btransform\b",
]

SHADOW_HINTS = [
    r"hover:shadow-", r"group-hover:shadow-",
]

OPACITY_HINTS = [
    r"hover:opacity-", r"group-hover:opacity-", r"opacity-0", r"opacity-100",
]

WIDTH_HINTS = [
    r"\bh-full\b", r"\bw-full\b",
    # progress-bar-like patterns
]

COLOR_HINTS = [
    r"hover:bg-", r"hover:text-", r"hover:border-",
    r"group-hover:bg-", r"group-hover:text-", r"group-hover:border-",
    r"focus:bg-", r"focus:text-", r"focus:border-",
    r"hover:shadow-",  # shadow changes often accompany color changes
]


def pick_replacement(classname: str) -> str:
    """Given a className string, decide what to replace `transition-all` with."""
    has_transform = any(re.search(p, classname) for p in TRANSFORM_HINTS)
    has_shadow = any(re.search(p, classname) for p in SHADOW_HINTS)
    has_opacity = any(re.search(p, classname) for p in OPACITY_HINTS)
    has_width = any(re.search(p, classname) for p in WIDTH_HINTS)
    has_color = any(re.search(p, classname) for p in COLOR_HINTS)

    replacements = []

    # Progress bars / width animations (very specific case)
    if has_width and not has_color and not has_transform:
        # Likely a progress bar where only width changes
        return "transition-[width]"

    if has_transform:
        replacements.append("transition-transform")

    if has_color:
        replacements.append("transition-colors")

    if has_shadow and "transition-colors" not in replacements:
        replacements.append("transition-shadow")

    if has_opacity and not has_color and not has_transform:
        replacements.append("transition-opacity")

    if not replacements:
        # Default fallback: most UI elements only change colors
        return "transition-colors"

    return " ".join(replacements)


def process_file(path: Path) -> int:
    """Replace transition-all in a single file. Returns count of replacements."""
    original = path.read_text(encoding="utf-8")
    modified = original
    count = 0

    # Match className strings: className="..." or className={cn("...")} or className={`...`}
    # We'll do a simpler approach: find transition-all and look at the surrounding quoted string

    def replacer(match):
        nonlocal count
        before = match.string[max(0, match.start() - 200):match.start()]
        after = match.string[match.end():min(len(match.string), match.end() + 200)]

        # Try to extract the full className string
        # Look backwards for the nearest quote/backtick start
        quote = None
        start_idx = None
        for i in range(len(before) - 1, -1, -1):
            c = before[i]
            if c in ('"', "'", '`'):
                # Check it's not escaped
                if i > 0 and before[i - 1] == '\\':
                    continue
                quote = c
                start_idx = i + 1
                break

        # Look forwards for the matching end quote
        end_idx = None
        for i, c in enumerate(after):
            if c == quote:
                if i > 0 and after[i - 1] == '\\':
                    continue
                end_idx = match.end() + i
                break

        if start_idx is not None and end_idx is not None:
            classname = before[start_idx:] + "transition-all" + after[:end_idx - match.end()]
            replacement = pick_replacement(classname)
        else:
            replacement = "transition-colors"

        count += 1
        return replacement

    # Use regex to find standalone transition-all (not part of another word)
    modified = re.sub(r"(?<![\w-])transition-all(?![\w-])", replacer, modified)

    if modified != original:
        path.write_text(modified, encoding="utf-8")

    return count


def main():
    total = 0
    files = []
    for ext in ("*.tsx", "*.ts", "*.css"):
        files.extend(FRONTEND_SRC.rglob(ext))

    for f in sorted(files):
        c = process_file(f)
        if c:
            total += c
            print(f"  {f.relative_to(FRONTEND_SRC)}: {c} replacements")

    print(f"\nTotal replacements: {total}")


if __name__ == "__main__":
    main()
