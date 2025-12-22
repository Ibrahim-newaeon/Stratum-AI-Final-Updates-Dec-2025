"""Add Landing Page CMS tables

Revision ID: 006
Revises: 005
Create Date: 2024-12-22 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Create landing_content table (main CMS content)
    # =========================================================================
    op.create_table(
        'landing_content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # Section and language
        sa.Column('section', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),

        # Content as JSONB
        sa.Column('content', JSONB(), nullable=False, server_default='{}'),

        # Publishing
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),

        # Audit
        sa.Column('updated_by', sa.Integer(), nullable=True),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index('ix_landing_section', 'landing_content', ['section'])
    op.create_index('ix_landing_section_lang', 'landing_content', ['section', 'language'], unique=True)
    op.create_index('ix_landing_published', 'landing_content', ['is_published', 'section'])

    # =========================================================================
    # Create landing_content_history table (version history)
    # =========================================================================
    op.create_table(
        'landing_content_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # Reference
        sa.Column('content_id', sa.Integer(), nullable=False),

        # Snapshot
        sa.Column('section', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('content', JSONB(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),

        # Audit
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index('ix_landing_history_content', 'landing_content_history', ['content_id'])
    op.create_index('ix_landing_history_content_version', 'landing_content_history', ['content_id', 'version'])

    # =========================================================================
    # Seed default content for English
    # =========================================================================
    op.execute("""
    INSERT INTO landing_content (section, language, content, is_published, version) VALUES
    ('hero', 'en', '{
        "badge": "AI-Powered Marketing Intelligence",
        "title_line1": "Unify Your Ad Platforms.",
        "title_line2": "Amplify Your Results.",
        "subtitle": "Stratum AI consolidates Meta, Google, TikTok, Snapchat, and LinkedIn into one intelligent platform. Get AI-powered predictions, automated optimization, and real-time insights.",
        "cta_primary": "Start Free Trial",
        "cta_secondary": "See How It Works"
    }', true, 1),

    ('stats', 'en', '{
        "items": [
            {"value": "50%", "label": "Time Saved on Reporting"},
            {"value": "32%", "label": "Average ROAS Improvement"},
            {"value": "5+", "label": "Platforms Unified"},
            {"value": "24/7", "label": "Automated Monitoring"}
        ]
    }', true, 1),

    ('features', 'en', '{
        "title": "Everything You Need to Dominate Digital Advertising",
        "subtitle": "From AI predictions to automated optimization, Stratum AI gives you the tools to maximize ROAS.",
        "items": [
            {"icon": "Brain", "title": "AI-Powered Intelligence", "description": "Machine learning models predict ROAS, optimize budgets, and identify growth opportunities automatically."},
            {"icon": "Globe", "title": "Unified Multi-Platform", "description": "Connect Meta, Google, TikTok, Snapchat, and LinkedIn in one dashboard. No more platform switching."},
            {"icon": "Zap", "title": "Smart Automation", "description": "IFTTT-style rules that pause underperformers, reallocate budgets, and send alerts automatically."},
            {"icon": "Target", "title": "Competitor Intelligence", "description": "Track competitors, benchmark performance, and identify market opportunities in real-time."},
            {"icon": "LineChart", "title": "Real-Time Analytics", "description": "Live dashboards with KPIs, trends, and custom reports. Make decisions with confidence."},
            {"icon": "Shield", "title": "GDPR Compliant", "description": "Enterprise-grade security with PII encryption, audit trails, and data export capabilities."}
        ]
    }', true, 1),

    ('pricing', 'en', '{
        "title": "Simple, Transparent Pricing",
        "subtitle": "Start free, upgrade when you are ready. No hidden fees.",
        "plans": [
            {
                "name": "Starter",
                "price": "$49",
                "period": "per month",
                "description": "For small teams getting started",
                "features": ["5 team members", "25 campaigns", "2 ad platforms", "10 automation rules", "Basic AI predictions", "90-day data retention", "Email support"],
                "cta": "Start 14-Day Free Trial",
                "popular": false
            },
            {
                "name": "Professional",
                "price": "$199",
                "period": "per month",
                "description": "For growing marketing teams",
                "features": ["15 team members", "100 campaigns", "5 ad platforms", "50 automation rules", "Advanced AI predictions", "20 competitor tracking", "1-year data retention", "API access", "Priority support"],
                "cta": "Start 14-Day Free Trial",
                "popular": true
            },
            {
                "name": "Enterprise",
                "price": "Custom",
                "period": "contact us",
                "description": "For large organizations",
                "features": ["Unlimited team members", "Unlimited campaigns", "All ad platforms", "Unlimited automation", "Full AI capabilities", "Unlimited competitors", "Unlimited data retention", "White-label option", "Dedicated success manager", "SLA guarantee"],
                "cta": "Contact Sales",
                "popular": false
            }
        ]
    }', true, 1),

    ('testimonials', 'en', '{
        "title": "Trusted by Marketing Teams Worldwide",
        "subtitle": "See what our customers have to say about Stratum AI.",
        "items": [
            {"quote": "Stratum AI transformed how we manage ads. We cut reporting time by 60% and improved ROAS by 40%.", "author": "Sarah Chen", "role": "Head of Performance Marketing", "company": "TechScale Inc."},
            {"quote": "The AI predictions are incredibly accurate. It is like having a data scientist on the team 24/7.", "author": "Michael Torres", "role": "Digital Marketing Director", "company": "GrowthBox"},
            {"quote": "Finally, one platform for all our ad channels. The automation rules alone saved us 20 hours per week.", "author": "Emma Williams", "role": "CMO", "company": "Velocity Commerce"}
        ]
    }', true, 1),

    ('cta', 'en', '{
        "title": "Ready to Transform Your Marketing?",
        "subtitle": "Join thousands of marketing teams using Stratum AI to maximize their advertising ROI.",
        "button": "Start Your Free Trial",
        "note": "No credit card required. 14-day free trial."
    }', true, 1),

    ('seo', 'en', '{
        "title": "Stratum AI - Unified Marketing Intelligence Platform",
        "description": "Consolidate Meta, Google, TikTok, Snapchat, and LinkedIn into one AI-powered platform. Get predictions, automation, and real-time insights.",
        "keywords": ["marketing automation", "ad management", "ROAS optimization", "AI marketing", "multi-platform ads"],
        "og_image": "/og-image.png"
    }', true, 1),

    ('announcement', 'en', '{
        "enabled": false,
        "text": "",
        "link": "",
        "link_text": ""
    }', true, 1);
    """)

    # =========================================================================
    # Seed default content for Arabic
    # =========================================================================
    op.execute("""
    INSERT INTO landing_content (section, language, content, is_published, version) VALUES
    ('hero', 'ar', '{
        "badge": "ذكاء تسويقي مدعوم بالذكاء الاصطناعي",
        "title_line1": "وحّد منصات إعلاناتك.",
        "title_line2": "ضاعف نتائجك.",
        "subtitle": "تجمع Stratum AI منصات Meta وGoogle وTikTok وSnapchat وLinkedIn في منصة ذكية واحدة. احصل على تنبؤات مدعومة بالذكاء الاصطناعي وتحسين آلي ورؤى في الوقت الفعلي.",
        "cta_primary": "ابدأ النسخة التجريبية المجانية",
        "cta_secondary": "شاهد كيف يعمل"
    }', true, 1),

    ('stats', 'ar', '{
        "items": [
            {"value": "50%", "label": "توفير في وقت إعداد التقارير"},
            {"value": "32%", "label": "متوسط تحسين العائد على الإنفاق الإعلاني"},
            {"value": "5+", "label": "منصات موحدة"},
            {"value": "24/7", "label": "مراقبة آلية"}
        ]
    }', true, 1),

    ('features', 'ar', '{
        "title": "كل ما تحتاجه للسيطرة على الإعلانات الرقمية",
        "subtitle": "من تنبؤات الذكاء الاصطناعي إلى التحسين الآلي، تمنحك Stratum AI الأدوات لتعظيم العائد على الإنفاق الإعلاني.",
        "items": [
            {"icon": "Brain", "title": "ذكاء اصطناعي متقدم", "description": "نماذج تعلم آلي تتنبأ بالعائد على الإنفاق الإعلاني وتحسن الميزانيات وتحدد فرص النمو تلقائياً."},
            {"icon": "Globe", "title": "منصة موحدة متعددة القنوات", "description": "اربط Meta وGoogle وTikTok وSnapchat وLinkedIn في لوحة تحكم واحدة. لا مزيد من التنقل بين المنصات."},
            {"icon": "Zap", "title": "أتمتة ذكية", "description": "قواعد IFTTT توقف الحملات الضعيفة وتعيد توزيع الميزانيات وترسل التنبيهات تلقائياً."},
            {"icon": "Target", "title": "استخبارات المنافسين", "description": "تتبع المنافسين وقارن الأداء وحدد فرص السوق في الوقت الفعلي."},
            {"icon": "LineChart", "title": "تحليلات في الوقت الفعلي", "description": "لوحات تحكم مباشرة مع مؤشرات الأداء والاتجاهات والتقارير المخصصة. اتخذ قرارات بثقة."},
            {"icon": "Shield", "title": "متوافق مع GDPR", "description": "أمان على مستوى المؤسسات مع تشفير البيانات الشخصية وسجلات التدقيق وإمكانيات تصدير البيانات."}
        ]
    }', true, 1),

    ('pricing', 'ar', '{
        "title": "أسعار بسيطة وشفافة",
        "subtitle": "ابدأ مجاناً، وقم بالترقية عندما تكون جاهزاً. لا رسوم خفية.",
        "plans": [
            {
                "name": "المبتدئ",
                "price": "$49",
                "period": "شهرياً",
                "description": "للفرق الصغيرة في البداية",
                "features": ["5 أعضاء فريق", "25 حملة", "منصتان إعلانيتان", "10 قواعد أتمتة", "تنبؤات ذكاء اصطناعي أساسية", "احتفاظ بالبيانات 90 يوم", "دعم بالبريد الإلكتروني"],
                "cta": "ابدأ النسخة التجريبية 14 يوم",
                "popular": false
            },
            {
                "name": "الاحترافي",
                "price": "$199",
                "period": "شهرياً",
                "description": "لفرق التسويق النامية",
                "features": ["15 عضو فريق", "100 حملة", "5 منصات إعلانية", "50 قاعدة أتمتة", "تنبؤات ذكاء اصطناعي متقدمة", "تتبع 20 منافس", "احتفاظ بالبيانات سنة", "وصول API", "دعم ذو أولوية"],
                "cta": "ابدأ النسخة التجريبية 14 يوم",
                "popular": true
            },
            {
                "name": "المؤسسات",
                "price": "مخصص",
                "period": "تواصل معنا",
                "description": "للمؤسسات الكبيرة",
                "features": ["أعضاء فريق غير محدودين", "حملات غير محدودة", "جميع منصات الإعلان", "أتمتة غير محدودة", "إمكانيات ذكاء اصطناعي كاملة", "منافسين غير محدودين", "احتفاظ غير محدود بالبيانات", "خيار العلامة البيضاء", "مدير نجاح مخصص", "ضمان SLA"],
                "cta": "تواصل مع المبيعات",
                "popular": false
            }
        ]
    }', true, 1),

    ('testimonials', 'ar', '{
        "title": "موثوق من فرق التسويق حول العالم",
        "subtitle": "شاهد ماذا يقول عملاؤنا عن Stratum AI.",
        "items": [
            {"quote": "غيّرت Stratum AI طريقة إدارتنا للإعلانات. قللنا وقت إعداد التقارير بنسبة 60% وحسّنا العائد على الإنفاق الإعلاني بنسبة 40%.", "author": "سارة تشن", "role": "رئيسة تسويق الأداء", "company": "TechScale Inc."},
            {"quote": "تنبؤات الذكاء الاصطناعي دقيقة بشكل لا يصدق. إنها مثل وجود عالم بيانات في الفريق على مدار الساعة.", "author": "مايكل توريس", "role": "مدير التسويق الرقمي", "company": "GrowthBox"},
            {"quote": "أخيراً، منصة واحدة لجميع قنواتنا الإعلانية. قواعد الأتمتة وحدها وفرت لنا 20 ساعة أسبوعياً.", "author": "إيما ويليامز", "role": "كبيرة مسؤولي التسويق", "company": "Velocity Commerce"}
        ]
    }', true, 1),

    ('cta', 'ar', '{
        "title": "هل أنت مستعد لتحويل تسويقك؟",
        "subtitle": "انضم إلى آلاف فرق التسويق التي تستخدم Stratum AI لتعظيم عائد الاستثمار الإعلاني.",
        "button": "ابدأ النسخة التجريبية المجانية",
        "note": "لا حاجة لبطاقة ائتمان. نسخة تجريبية مجانية لمدة 14 يوم."
    }', true, 1),

    ('seo', 'ar', '{
        "title": "Stratum AI - منصة ذكاء تسويقي موحدة",
        "description": "ادمج Meta وGoogle وTikTok وSnapchat وLinkedIn في منصة واحدة مدعومة بالذكاء الاصطناعي. احصل على تنبؤات وأتمتة ورؤى في الوقت الفعلي.",
        "keywords": ["أتمتة التسويق", "إدارة الإعلانات", "تحسين العائد على الإنفاق الإعلاني", "تسويق بالذكاء الاصطناعي", "إعلانات متعددة المنصات"],
        "og_image": "/og-image.png"
    }', true, 1),

    ('announcement', 'ar', '{
        "enabled": false,
        "text": "",
        "link": "",
        "link_text": ""
    }', true, 1);
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_table('landing_content_history')
    op.drop_table('landing_content')
