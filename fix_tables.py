import os, re

# Files with tables to fix
table_files = [
    'components/AttributionVariancePanel.tsx',
    'views/Campaigns.tsx',
    'views/Assets.tsx',
    'views/Competitors.tsx',
    'views/WhatsApp.tsx',
    'views/Settings.tsx',
    'views/SuperadminDashboard.tsx',
    'components/ui/data-table.tsx',
    'components/cdp/ConsentManager.tsx',
    'components/cdp/FunnelBuilder.tsx',
    'components/SignalHealthPanel.tsx',
    'views/tenant/AuditLog.tsx',
    'views/superadmin/Billing.tsx',
    'views/superadmin/System.tsx',
    'views/superadmin/TenantsList.tsx',
    'views/newsletter/NewsletterSubscribers.tsx',
    'views/newsletter/NewsletterCampaigns.tsx',
    'views/newsletter/NewsletterAnalytics.tsx',
    'views/newsletter/NewsletterDashboard.tsx',
    'views/Tenants.tsx',
    'components/CommandCenter.tsx',
    'views/knowledge-graph/KGRevenueAttribution.tsx',
]

fixed = 0
for rel_path in table_files:
    path = os.path.join('frontend/src', rel_path)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    # Add scope='col' to <th> that doesn't already have scope
    content = re.sub(r'<th(?!\s[^>]*\sscope=)(\s[^>]*)?>', r'<th scope="col"\1>', content)
    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed += 1
        print(f'Fixed: {rel_path}')

print(f'Total files fixed: {fixed}')
