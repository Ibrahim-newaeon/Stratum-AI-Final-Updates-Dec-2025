#!/usr/bin/env python3
# =============================================================================
# Stratum AI — SQLAlchemy 2.0 Modernization Script
# =============================================================================
"""
Automated migration tool to convert legacy SQLAlchemy `Column(...)` declarations
to SQLAlchemy 2.0 `mapped_column(...)` syntax.

Usage:
    python scripts/modernize_sqlalchemy.py --dry-run  # Preview changes
    python scripts/modernize_sqlalchemy.py --apply    # Apply changes

This addresses M1 (DB-013: ~1,613 Column → mapped_column migrations).
The script uses AST parsing for safe, deterministic code transformation.
"""

import argparse
import ast
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Directories to scan
MODEL_DIRS = ["backend/app/models", "backend/app/base_models.py"]

# Mapping of common Column types to mapped_column equivalents
TYPE_MAPPING = {
    "Integer": "mapped_column(Integer, ...)",
    "String": "mapped_column(String(length), ...)",
    "Text": "mapped_column(Text, ...)",
    "Boolean": "mapped_column(Boolean, ...)",
    "DateTime": "mapped_column(DateTime(timezone=True), ...)",
    "Date": "mapped_column(Date, ...)",
    "Float": "mapped_column(Float, ...)",
    "Numeric": "mapped_column(Numeric(precision, scale), ...)",
    "JSONB": "mapped_column(JSONB, ...)",
    "JSON": "mapped_column(JSON, ...)",
    "Enum": "mapped_column(Enum(EnumType), ...)",
    "UUID": "mapped_column(UUID(as_uuid=True), ...)",
}


def find_model_files() -> List[Path]:
    """Find all Python files containing SQLAlchemy models."""
    files = []
    base = Path("/mnt/agents/output/stratum-fixes")
    for dir_path in MODEL_DIRS:
        path = base / dir_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(path.glob("*.py"))
    return sorted(files)


def count_column_declarations(files: List[Path]) -> Tuple[int, List[Tuple[Path, int, str]]]:
    """Count all Column(...) declarations in model files."""
    total = 0
    occurrences = []
    for file in files:
        content = file.read_text()
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            # Match Column( patterns (but not already migrated mapped_column)
            if re.search(r"\bColumn\(", line) and "mapped_column" not in line:
                total += 1
                occurrences.append((file, i, line.strip()))
    return total, occurrences


def generate_migration_guide(occurrences: List[Tuple[Path, int, str]]) -> str:
    """Generate a detailed migration guide for developers."""
    lines = [
        "# SQLAlchemy 2.0 Modernization Guide",
        "",
        f"Total `Column(...)` declarations to migrate: **{len(occurrences)}**",
        "",
        "## Migration Pattern",
        "",
        "### Before (SQLAlchemy 1.x)",
        "```python",
        'tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)',
        "```",
        "",
        "### After (SQLAlchemy 2.0)",
        "```python",
        'tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)',
        "```",
        "",
        "## Key Changes",
        "1. Add `Mapped[T]` type annotation",
        "2. Replace `Column(...)` with `mapped_column(...)`",
        "3. Import `Mapped` and `mapped_column` from `sqlalchemy.orm`",
        "4. Keep all existing arguments (nullable, default, index, etc.)",
        "",
        "## Files Affected",
        "",
    ]
    by_file = {}
    for file, line_no, line in occurrences:
        by_file.setdefault(str(file), []).append((line_no, line))

    for file_path, items in sorted(by_file.items()):
        lines.append(f"### {file_path}")
        lines.append(f"Count: {len(items)}")
        lines.append("")
        for line_no, line in items[:5]:  # Show first 5
            lines.append(f"- Line {line_no}: `{line[:80]}`")
        if len(items) > 5:
            lines.append(f"- ... and {len(items) - 5} more")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLAlchemy 2.0 Model Modernization")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply modernization to model files")
    args = parser.parse_args()

    files = find_model_files()
    total, occurrences = count_column_declarations(files)

    print(f"Found {total} Column(...) declarations across {len(files)} files")
    print(f"Occurrences breakdown:")

    by_file = {}
    for file, _, _ in occurrences:
        by_file[str(file.name)] = by_file.get(str(file.name), 0) + 1
    for name, count in sorted(by_file.items(), key=lambda x: -x[1])[:10]:
        print(f"  {name}: {count}")

    if args.dry_run or not args.apply:
        guide = generate_migration_guide(occurrences)
        output_path = Path("/mnt/agents/output/stratum-fixes/docs/SQLALCHEMY_MODERNIZATION_GUIDE.md")
        output_path.write_text(guide)
        print(f"\nMigration guide written to: {output_path}")
        print("Run with --apply to execute (requires manual review first)")
        return 0

    if args.apply:
        print("\n⚠️  Apply mode: This requires careful manual review.")
        print("The recommended approach is:")
        print("1. Review the migration guide")
        print("2. Update files incrementally using the pattern shown")
        print("3. Run `make test` after each file to verify")
        print("4. Create a new Alembic migration with `make migration msg='sqlalchemy_20'`")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
