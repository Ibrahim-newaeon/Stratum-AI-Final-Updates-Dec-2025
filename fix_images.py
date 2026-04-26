import os, re

img_pattern = re.compile(r'<img\s([^>]*?)>')
lazy_pattern = re.compile(r'loading=["\']lazy["\']')

files_to_check = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.tsx', '.jsx', '.ts', '.js')):
            files_to_check.append(os.path.join(root, f))

fixed = 0
for path in files_to_check:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    def add_lazy(match):
        attrs = match.group(1)
        if lazy_pattern.search(attrs):
            return match.group(0)
        # Skip above-the-fold images
        if 'hero' in attrs.lower() or 'logo' in attrs.lower():
            return match.group(0)
        return f'<img {attrs} loading="lazy">'
    content = img_pattern.sub(add_lazy, content)
    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed += 1

print(f'Total files fixed: {fixed}')
