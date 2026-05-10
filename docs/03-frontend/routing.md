# Routing Configuration

## Overview

Stratum AI uses React Router v6 for client-side routing with lazy-loaded components.

---

## Route Structure

### Public Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | Landing | Main landing page |
| `/ar` | LandingAr | Arabic landing page |
| `/ai` | AILanding | AI-focused marketing page |
| `/login` | Login | User login |
| `/signup` | Signup | User registration |
| `/forgot-password` | ForgotPassword | Password reset request |
| `/reset-password` | ResetPassword | Password reset form |
| `/verify-email` | VerifyEmail | Email verification |
| `/cdp-calculator` | CDPCalculator | ROI calculator |
| `/plans/:tier` | TierLandingPage | Tier-specific pages |

### Product Pages

| Path | Component | Description |
|------|-----------|-------------|
| `/features` | FeaturesPage | Product features |
| `/pricing` | PricingPage | Pricing plans |
| `/integrations` | IntegrationsPage | Integration catalog |
| `/api-docs` | ApiDocsPage | API documentation |

### Solutions Pages

| Path | Component | Description |
|------|-----------|-------------|
| `/solutions/cdp` | CDPSolutionPage | CDP solution |
| `/solutions/audience-sync` | AudienceSyncPage | Audience sync |
| `/solutions/predictions` | PredictionsSolutionPage | Predictions |
| `/solutions/trust-engine` | TrustEnginePage | Trust engine |

### Company Pages

| Path | Component | Description |
|------|-----------|-------------|
| `/about` | AboutPage | About us |
| `/careers` | CareersPage | Job listings |
| `/blog` | BlogPage | Blog index |
| `/blog/:slug` | BlogPostPage | Blog post |
| `/contact` | ContactPage | Contact form |
| `/faq` | FAQPage | FAQ |

### Legal Pages

| Path | Component | Description |
|------|-----------|-------------|
| `/privacy` | PrivacyPage | Privacy policy |
| `/terms` | TermsPage | Terms of service |
| `/security` | SecurityPage | Security info |
| `/dpa` | DPAPage | Data processing agreement |

### Resources Pages

| Path | Component | Description |
|------|-----------|-------------|
| `/docs` | DocsPage | Documentation |
| `/changelog` | ChangelogPage | Release notes |
| `/case-studies` | CaseStudiesPage | Case studies |
| `/resources` | ResourcesPage | Resource center |
| `/status` | StatusPage | System status |
| `/compare` | ComparisonPage | Product comparison |
| `/glossary` | GlossaryPage | Terminology glossary |

---

## Protected Routes

### Dashboard Routes (`/dashboard/*`)

Requires authentication and completed onboarding.

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard` | → `/dashboard/overview` | Redirect to overview |
| `/dashboard/overview` | UnifiedDashboard | Main dashboard |
| `/dashboard/campaigns` | Campaigns | Campaign list |
| `/dashboard/stratum` | Stratum | Stratum intelligence |
| `/dashboard/benchmarks` | Benchmarks | Performance benchmarks |
| `/dashboard/assets` | Assets | Digital assets |
| `/dashboard/rules` | Rules | Automation rules |
| `/dashboard/competitors` | Competitors | Competitor intel |
| `/dashboard/predictions` | Predictions | ML predictions |
| `/dashboard/whatsapp` | WhatsApp | WhatsApp integration |
| `/dashboard/settings` | Settings | User settings |
| `/dashboard/tenants` | Tenants | Tenant management |
| `/dashboard/ml-training` | MLTraining | ML model training |
| `/dashboard/capi-setup` | CAPISetup | CAPI configuration |
| `/dashboard/data-quality` | DataQuality | Data quality tools |
| `/dashboard/emq-dashboard` | DataQualityDashboard | EMQ dashboard |

### CDP Routes (`/dashboard/cdp/*`)

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard/cdp` | CDPDashboard | CDP overview |
| `/dashboard/cdp/profiles` | CDPProfiles | Profile viewer |
| `/dashboard/cdp/segments` | CDPSegments | Segment builder |
| `/dashboard/cdp/events` | CDPEvents | Event timeline |
| `/dashboard/cdp/identity` | CDPIdentityGraph | Identity graph |
| `/dashboard/cdp/audience-sync` | CDPAudienceSync | Audience sync |
| `/dashboard/cdp/rfm` | CDPRfm | RFM analysis |
| `/dashboard/cdp/funnels` | CDPFunnels | Conversion funnels |
| `/dashboard/cdp/computed-traits` | CDPComputedTraits | Computed traits |
| `/dashboard/cdp/consent` | CDPConsent | Consent management |
| `/dashboard/cdp/predictive-churn` | CDPPredictiveChurn | Churn prediction |

### Enterprise Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard/custom-autopilot-rules` | CustomAutopilotRules | Custom rules |
| `/dashboard/custom-reports` | CustomReportBuilder | Report builder |

### Superadmin Routes (`/dashboard/superadmin/*`)

Requires `superadmin` role.

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard/superadmin` | SuperadminDashboard | Admin overview |
| `/dashboard/superadmin/control-tower` | ControlTower | Platform control |
| `/dashboard/superadmin/tenants` | TenantsList | All tenants |
| `/dashboard/superadmin/tenants/:tenantId` | TenantProfile | Tenant details |
| `/dashboard/superadmin/benchmarks` | Benchmarks | Global benchmarks |
| `/dashboard/superadmin/audit` | Audit | Audit logs |
| `/dashboard/superadmin/billing` | Billing | Billing management |
| `/dashboard/superadmin/system` | System | System settings |
| `/dashboard/superadmin/cms` | CMS | Content management |
| `/dashboard/superadmin/users` | Users | User management |

### Account Manager Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard/am/portfolio` | AMPortfolio | Client portfolio |
| `/dashboard/am/tenant/:tenantId` | AMTenantNarrative | Client narrative |

---

## Tenant-Scoped Routes (`/app/:tenantId/*`)

All routes include tenant context.

| Path | Component | Description |
|------|-----------|-------------|
| `/app/:tenantId` | TenantOverview | Tenant dashboard |
| `/app/:tenantId/overview` | TenantOverview | Same as above |
| `/app/:tenantId/trust` | TenantAdminOverview | Trust overview |
| `/app/:tenantId/console` | MediaBuyerConsole | Media buyer view |
| `/app/:tenantId/signal-hub` | SignalHub | Signal hub |
| `/app/:tenantId/campaigns` | TenantCampaigns | Campaigns |
| `/app/:tenantId/campaigns/connect` | ConnectPlatforms | Connect platforms |
| `/app/:tenantId/campaigns/accounts` | AdAccounts | Ad accounts |
| `/app/:tenantId/campaigns/new` | CampaignBuilder | New campaign |
| `/app/:tenantId/campaigns/drafts` | CampaignDrafts | Draft campaigns |
| `/app/:tenantId/campaigns/drafts/:draftId` | CampaignBuilder | Edit draft |
| `/app/:tenantId/campaigns/logs` | PublishLogs | Publish history |
| `/app/:tenantId/settings` | TenantSettings | Settings |
| `/app/:tenantId/team` | TeamManagement | Team management |
| `/app/:tenantId/competitors` | Competitors | Competitor intel |
| `/app/:tenantId/benchmarks` | Benchmarks | Benchmarks |
| `/app/:tenantId/assets` | Assets | Digital assets |
| `/app/:tenantId/rules` | Rules | Automation rules |
| `/app/:tenantId/predictions` | Predictions | ML predictions |
| `/app/:tenantId/integrations` | Integrations | CRM integrations |
| `/app/:tenantId/pacing` | Pacing | Pacing & forecasting |
| `/app/:tenantId/profit` | ProfitROAS | Profit ROAS |
| `/app/:tenantId/attribution` | Attribution | Attribution |
| `/app/:tenantId/reporting` | Reporting | Reporting |
| `/app/:tenantId/ab-testing` | ABTesting | A/B testing |
| `/app/:tenantId/dead-letter-queue` | DeadLetterQueue | DLQ management |
| `/app/:tenantId/explainability` | ModelExplainability | Model explainability |
| `/app/:tenantId/embed-widgets` | EmbedWidgets | Embed widgets |

---

## CMS Portal Routes (`/cms/*`)

Requires `admin` or `superadmin` role.

| Path | Component | Description |
|------|-----------|-------------|
| `/cms-login` | CMSLogin | CMS login |
| `/cms` | CMSDashboard | CMS dashboard |
| `/cms/posts` | SuperAdminCMS | Posts management |
| `/cms/categories` | SuperAdminCMS | Categories |
| `/cms/authors` | SuperAdminCMS | Authors |
| `/cms/contacts` | SuperAdminCMS | Contact submissions |
| `/cms/pages` | SuperAdminCMS | Page management |
| `/cms/landing/features` | SuperAdminCMS | Landing features |
| `/cms/landing/faq` | SuperAdminCMS | Landing FAQ |
| `/cms/landing/pricing` | SuperAdminCMS | Landing pricing |
| `/cms/settings` | SuperAdminCMS | CMS settings |

---

## Route Guards

### ProtectedRoute

Requires authentication:

```tsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <DashboardLayout />
    </ProtectedRoute>
  }
/>
```

### Role-Based Protection

Requires specific role:

```tsx
<Route
  path="/superadmin"
  element={
    <ProtectedRoute requiredRole="superadmin">
      <SuperadminDashboard />
    </ProtectedRoute>
  }
/>
```

### OnboardingGuard

Requires completed onboarding:

```tsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <OnboardingGuard>
        <DashboardLayout />
      </OnboardingGuard>
    </ProtectedRoute>
  }
/>
```

---

## Lazy Loading

All views are lazy-loaded for code splitting:

```tsx
const CDPDashboard = lazy(() => import('./views/cdp/CDPDashboard'))

<Route
  path="cdp"
  element={
    <Suspense fallback={<LoadingSpinner />}>
      <CDPDashboard />
    </Suspense>
  }
/>
```

---

## Navigation Hooks

### useNavigate

```tsx
import { useNavigate } from 'react-router-dom'

function Component() {
  const navigate = useNavigate()

  const handleClick = () => {
    navigate('/dashboard/campaigns')
  }
}
```

### useParams

```tsx
import { useParams } from 'react-router-dom'

function TenantView() {
  const { tenantId } = useParams<{ tenantId: string }>()
  // tenantId is available
}
```

### useSearchParams

```tsx
import { useSearchParams } from 'react-router-dom'

function SearchView() {
  const [searchParams, setSearchParams] = useSearchParams()

  const query = searchParams.get('q')
  const page = searchParams.get('page') || '1'
}
```
