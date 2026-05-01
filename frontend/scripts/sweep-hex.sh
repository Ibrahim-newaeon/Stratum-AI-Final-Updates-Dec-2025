#!/usr/bin/env bash
# Phase 4 — bracketed-class hex sweep.
#
# Replaces Tailwind arbitrary-value classes like `bg-[#080C14]`, `text-[#FF1F6D]/30`,
# `from-[#1E2740]`, `border-[#1E2740]/50` with the semantic equivalents that
# resolve via CSS vars in `index.css`.
#
# Run from the frontend/ directory. Idempotent — safe to re-run.

set -euo pipefail

cd "$(dirname "$0")/.."

# Old hex → semantic token mapping.
#   Format:  HEX:semantic
declare -a MAP=(
  '#080C14:background'
  '#0F1320:card'
  '#181F33:muted'
  '#1E2740:border'
  '#5A6278:muted-foreground'
  '#8B92A8:muted-foreground'
  '#F0EDE5:foreground'
  '#FF1F6D:primary'
  '#FF4D8F:primary'
  '#FF3D00:primary'
  '#FF8C00:secondary'
  '#FFB347:secondary'
)

# Tailwind utility prefixes that accept arbitrary color values via [#hex].
PREFIXES='bg|text|border|from|to|via|ring|placeholder|caret|accent|fill|stroke|outline|decoration|divide|shadow'

mapfile -t FILES < <(find src -type f \( -name '*.ts' -o -name '*.tsx' \) ! -path '*/node_modules/*')

for entry in "${MAP[@]}"; do
  hex="${entry%%:*}"
  name="${entry#*:}"
  # Pattern: <prefix>-[#HEX]<optional /NN>  →  <prefix>-<name><optional /NN>
  perl -i -pe \
    "s/(?<![-\\w])(${PREFIXES})-\\[\\Q${hex}\\E\\](\\/[0-9]+)?/\$1-${name}\$2/g" \
    "${FILES[@]}"
done

echo "Hex-class sweep done."
