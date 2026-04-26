import os, re

# Key files and line ranges with icon-only buttons needing aria-label
fixes = [
    # (file, line_contains, aria_label)
    ('frontend/src/views/WhatsApp.tsx', 'Phone className', 'aria-label="Phone"'),
    ('frontend/src/views/WhatsApp.tsx', 'MoreHorizontal className', 'aria-label="More options"'),
    ('frontend/src/views/WhatsApp.tsx', 'Paperclip className', 'aria-label="Attach file"'),
    ('frontend/src/views/WhatsApp.tsx', 'Image className', 'aria-label="Attach image"'),
    ('frontend/src/views/WhatsApp.tsx', 'Smile className', 'aria-label="Add emoji"'),
    ('frontend/src/views/Assets.tsx', 'MoreHorizontal', 'aria-label="More options"'),
    ('frontend/src/views/whatsapp/WhatsAppTemplates.tsx', 'PencilIcon', 'aria-label="Edit template"'),
    ('frontend/src/views/whatsapp/WhatsAppTemplates.tsx', 'TrashIcon', 'aria-label="Delete template"'),
    ('frontend/src/views/whatsapp/WhatsAppContacts.tsx', 'PencilIcon', 'aria-label="Edit contact"'),
    ('frontend/src/views/whatsapp/WhatsAppContacts.tsx', 'TrashIcon', 'aria-label="Delete contact"'),
    ('frontend/src/views/portal/PortalLayout.tsx', 'BellIcon', 'aria-label="Notifications"'),
    ('frontend/src/components/dashboard/CopilotChat.tsx', 'Send className', 'aria-label="Send message"'),
    ('frontend/src/components/dashboard/NLFilterCard.tsx', 'X className', 'aria-label="Remove filter"'),
]

# Also do a broad sweep: find <button> tags that contain only an icon component (capitalized first letter)
# and no text, and add aria-label if missing
icon_button_pattern = re.compile(
    r'(<button\s[^>]*?)(?<!aria-label=["\'])(?<!aria-label=\{)([^>]*?)>'
    r'\s*<[A-Z][a-zA-Z]*(?:Icon)?\s[^>]*?/>\s*</button>',
    re.DOTALL
)

broad_fixed = 0
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if not f.endswith('.tsx'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        orig = content
        # Simple heuristic: button with only icon inside, no aria-label
        def add_aria_label(match):
            opening = match.group(1) + match.group(2)
            if 'aria-label' in opening:
                return match.group(0)
            # Try to infer label from icon name
            icon_match = re.search(r'<([A-Z][a-zA-Z]*(?:Icon)?)\s', match.group(0))
            label = 'Action'
            if icon_match:
                icon_name = icon_match.group(1)
                label = icon_name.replace('Icon', '').replace('Lucide', '')
                # Convert camelCase to words
                import re as re_mod
                label = re_mod.sub(r'([a-z])([A-Z])', r'\1 \2', label)
            return f'{match.group(1)} aria-label="{label}"{match.group(2)}>{match.group(0).split(">", 1)[1]}'
        # Only apply to files we know have issues to avoid false positives
        if any(x[0] == path for x in fixes):
            content = icon_button_pattern.sub(add_aria_label, content)
        if content != orig:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
            broad_fixed += 1

print(f'Broad aria-label fixes applied to {broad_fixed} files')
