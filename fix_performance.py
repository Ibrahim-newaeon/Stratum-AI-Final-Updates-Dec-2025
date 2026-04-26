import os, re

# Fix background-tab polling in widgets
polling_widgets = [
    'frontend/src/components/widgets/ROASAlertsWidget.tsx',
    'frontend/src/components/widgets/LivePredictionsWidget.tsx',
    'frontend/src/components/widgets/BudgetOptimizerWidget.tsx',
]

for path in polling_widgets:
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find setInterval patterns and wrap with visibility check
    # This is a targeted fix - we look for setInterval and add visibility handling
    if 'setInterval' in content and 'visibilityState' not in content:
        # Add visibility check import if missing
        if 'useEffect' in content and 'document.visibilityState' not in content:
            # Find the useEffect that sets up the interval and modify it
            # This is complex; let's add a utility pattern
            content = content.replace(
                'import { useState, useEffect } from \'react\'',
                'import { useState, useEffect, useRef } from \'react\''
            )
            # We can't safely auto-modify arbitrary interval setups without reading each file
            print(f'Note: {path} needs manual visibilityState fix')

# Add React.memo to heavy components
memo_targets = [
    'frontend/src/components/dashboard/CampaignTable.tsx',
    'frontend/src/components/ui/data-table.tsx',
    'frontend/src/components/AttributionVariancePanel.tsx',
    'frontend/src/components/widgets/ROASAlertsWidget.tsx',
    'frontend/src/components/widgets/LivePredictionsWidget.tsx',
    'frontend/src/components/widgets/BudgetOptimizerWidget.tsx',
]

memo_fixed = 0
for path in memo_targets:
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'memo(' in content or 'React.memo' in content:
        continue
    # Add memo import if not present
    if 'memo' not in content.split('from')[0]:
        content = content.replace(
            "from 'react'",
            "from 'react'",
        )
        # Find the import line and add memo
        content = re.sub(
            r"(import\s+\{[^}]*)(\}\s+from\s+['\"]react['\"])",
            lambda m: f"{m.group(1) + (',' if not m.group(1).endswith(',') else '')} memo{m.group(2)}" if 'memo' not in m.group(1) else m.group(0),
            content
        )
    # Wrap default export with memo
    content = re.sub(
        r"export\s+default\s+function\s+(\w+)",
        r"function \1",
        content
    )
    # Add memo export at end if not already there
    if 'export default memo(' not in content:
        # Find the last non-empty line before closing brace or end
        lines = content.split('\n')
        # Simple approach: add at end of file
        content = content.rstrip() + '\n\nexport default memo(' + re.search(r'function\s+(\w+)', content).group(1) + ')\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    memo_fixed += 1
    print(f'Added memo: {path}')

# Fix artificial loading delay in Overview.tsx
overview_path = 'frontend/src/views/Overview.tsx'
if os.path.exists(overview_path):
    with open(overview_path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    content = re.sub(
        r"setTimeout\(\(\)\s*=>\s*setInitialLoading\(false\),\s*\d+\)",
        "setInitialLoading(false)",
        content
    )
    if content != orig:
        with open(overview_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Removed artificial delay: {overview_path}')

print(f'Memo fixes applied: {memo_fixed}')
