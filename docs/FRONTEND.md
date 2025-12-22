# Stratum AI - Frontend Documentation

## Overview

The Stratum AI frontend is a single-page application built with React 18, TypeScript, and Tailwind CSS. It provides a comprehensive dashboard for managing advertising campaigns across multiple platforms.

---

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Tailwind CSS | 3.x | Styling |
| React Router | 6.x | Routing |
| React Query | 5.x | Data fetching |
| Zustand | 4.x | State management |
| Recharts | 2.x | Charts |
| i18next | 23.x | Internationalization |

---

## Project Structure

```
frontend/
├── public/                      # Static assets
│   ├── favicon.ico
│   └── locales/                # Translation files
│
├── src/
│   ├── main.tsx                # Application entry
│   ├── App.tsx                 # Root component + routing
│   ├── index.css               # Global styles
│   │
│   ├── components/             # Reusable components
│   │   ├── auth/               # Authentication
│   │   ├── campaigns/          # Campaign management
│   │   ├── charts/             # Data visualization
│   │   ├── common/             # Shared utilities
│   │   ├── dashboard/          # Dashboard-specific
│   │   ├── guide/              # Tutorial/onboarding
│   │   ├── ui/                 # Base UI components
│   │   └── widgets/            # Dashboard widgets
│   │
│   ├── views/                  # Page components
│   │   ├── Login.tsx
│   │   ├── Overview.tsx
│   │   ├── Campaigns.tsx
│   │   └── ...
│   │
│   ├── contexts/               # React contexts
│   │   ├── AuthContext.tsx
│   │   └── ThemeContext.tsx
│   │
│   ├── services/               # API clients
│   │   ├── api.ts              # Axios instance
│   │   ├── authApi.ts
│   │   ├── campaignsApi.ts
│   │   └── ...
│   │
│   ├── types/                  # TypeScript definitions
│   │   ├── dashboard.ts
│   │   ├── campaign.ts
│   │   └── ...
│   │
│   ├── lib/                    # Utility functions
│   │   └── utils.ts
│   │
│   └── i18n/                   # Internationalization
│       ├── index.ts
│       └── locales/
│           ├── en.json
│           ├── ar.json
│           └── uk.json
│
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── nginx.conf                  # Production server config
```

---

## Component Architecture

### Component Hierarchy

```
App.tsx
├── ThemeProvider
│   └── AuthProvider
│       └── Router
│           ├── /login → Login.tsx
│           │
│           └── ProtectedRoute
│               └── DashboardLayout.tsx
│                   ├── Sidebar
│                   ├── Header
│                   └── Outlet
│                       ├── /overview → Overview.tsx
│                       ├── /campaigns → Campaigns.tsx
│                       ├── /rules → Rules.tsx
│                       ├── /assets → Assets.tsx
│                       ├── /benchmarks → Benchmarks.tsx
│                       ├── /whatsapp → WhatsApp.tsx
│                       ├── /settings → Settings.tsx
│                       ├── /ml-training → MLTraining.tsx
│                       ├── /capi-setup → CAPISetup.tsx
│                       └── /data-quality → DataQuality.tsx
```

### Component Types

| Type | Location | Purpose |
|------|----------|---------|
| **Views** | `views/` | Full-page components |
| **Widgets** | `components/widgets/` | Dashboard modules |
| **UI** | `components/ui/` | Base components |
| **Charts** | `components/charts/` | Data visualization |
| **Common** | `components/common/` | Shared utilities |

---

## Views (Pages)

### Login.tsx

Authentication page with email/password login and forgot password flow.

**Features:**
- Email/password form
- Form validation
- Forgot password modal
- Error handling
- Redirect to dashboard on success

**State:**
```typescript
interface LoginState {
  email: string;
  password: string;
  isLoading: boolean;
  error: string | null;
  showForgotPassword: boolean;
}
```

**Key Functions:**
```typescript
// Handle login submission
const handleLogin = async (e: FormEvent) => {
  e.preventDefault();
  setIsLoading(true);
  try {
    const response = await authApi.login(email, password);
    localStorage.setItem('access_token', response.access_token);
    navigate('/overview');
  } catch (error) {
    setError('Invalid credentials');
  } finally {
    setIsLoading(false);
  }
};
```

---

### Overview.tsx

Main dashboard with KPIs, charts, and campaign overview.

**Features:**
- KPI tiles (spend, revenue, ROAS, conversions)
- Platform breakdown chart
- Daily trend chart
- Top campaigns table
- Date range filter
- Export functionality

**Components Used:**
```tsx
<Overview>
  <FilterBar />
  <KPITiles />
  <div className="grid grid-cols-2 gap-4">
    <PlatformBreakdownWidget />
    <DailyTrendChart />
  </div>
  <CampaignsWidget />
</Overview>
```

**Data Fetching:**
```typescript
// React Query for data fetching
const { data: kpis, isLoading } = useQuery({
  queryKey: ['kpis', dateRange],
  queryFn: () => analyticsApi.getKPIs(dateRange),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

**Export Logic:**
```typescript
const handleExport = () => {
  const dataToExport = {
    kpis,
    campaigns,
    dateRange,
    exportedAt: new Date().toISOString(),
  };

  const blob = new Blob([JSON.stringify(dataToExport, null, 2)], {
    type: 'application/json',
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `stratum-export-${Date.now()}.json`;
  a.click();
};
```

---

### Campaigns.tsx

Campaign management with CRUD operations.

**Features:**
- Campaign list with filters
- Platform/status filtering
- Search functionality
- Create campaign modal
- Edit/delete operations
- Bulk actions

**Table Columns:**
```typescript
const columns = [
  { key: 'name', label: 'Campaign Name', sortable: true },
  { key: 'platform', label: 'Platform' },
  { key: 'status', label: 'Status' },
  { key: 'spend', label: 'Spend', format: 'currency' },
  { key: 'revenue', label: 'Revenue', format: 'currency' },
  { key: 'roas', label: 'ROAS', format: 'decimal' },
  { key: 'actions', label: '' },
];
```

**Campaign Create Modal:**
```tsx
<CampaignCreateModal
  isOpen={showCreateModal}
  onClose={() => setShowCreateModal(false)}
  onSubmit={handleCreateCampaign}
  platforms={['meta', 'google', 'tiktok', 'snapchat', 'linkedin']}
/>
```

---

### Rules.tsx

Automation rules builder and management.

**Features:**
- Rule list view
- Visual rule builder
- Condition configuration
- Action configuration
- Enable/disable toggle
- Execution history

**Rule Builder Interface:**
```typescript
interface Rule {
  id: number;
  name: string;
  status: 'active' | 'paused' | 'draft';
  condition: {
    field: string;
    operator: RuleOperator;
    value: string;
    duration_hours: number;
  };
  action: {
    type: RuleAction;
    config: Record<string, any>;
  };
  applies_to: {
    campaigns: number[] | null;
    platforms: string[] | null;
  };
}
```

---

### WhatsApp.tsx

WhatsApp Business messaging interface.

**Features:**
- Conversation list
- Message composer
- Template selector
- Broadcast messaging
- Contact management
- Opt-in status tracking

**Message Sending:**
```typescript
const handleSendMessage = async () => {
  if (!selectedConversation || !replyText.trim()) return;

  await whatsappApi.sendMessage({
    contact_id: selectedConversation.contact.id,
    message_type: 'text',
    content: replyText.trim(),
  });

  setReplyText('');
  refetchConversations();
};
```

**Broadcast Logic:**
```typescript
const handleBroadcast = async () => {
  const sendPromises = selectedContactIds.map((contactId) =>
    whatsappApi.sendMessage({
      contact_id: contactId,
      message_type: 'template',
      template_name: broadcastTemplate,
      template_variables: {},
    })
  );

  await Promise.all(sendPromises);
  toast.success(`Sent to ${selectedContactIds.length} contacts`);
};
```

---

### CAPISetup.tsx

Conversion API configuration interface.

**Features:**
- Platform connection status
- API key configuration
- Pixel/tag setup instructions
- Test event sender
- Data quality metrics

**Connection Status Component:**
```tsx
<PlatformCard
  platform="meta"
  connected={connections.meta}
  lastSync={syncTimes.meta}
  onConnect={() => handleConnect('meta')}
  onTest={() => handleTestEvent('meta')}
/>
```

---

### DataQuality.tsx

Event Matching Quality dashboard.

**Features:**
- Overall EMQ score
- Platform-specific scores
- Missing field indicators
- Recommendations
- Historical trends

**Quality Score Display:**
```tsx
<QualityScoreGauge
  score={qualityData.overall_score}
  level={qualityData.level}
  breakdown={{
    email: qualityData.field_scores.email,
    phone: qualityData.field_scores.phone,
    click_id: qualityData.field_scores.click_id,
    ip_address: qualityData.field_scores.ip_address,
  }}
/>
```

---

## Widgets

### KPITiles.tsx

Displays key performance indicators in a grid.

**Props:**
```typescript
interface KPITilesProps {
  data: {
    spend: number;
    revenue: number;
    roas: number;
    conversions: number;
    impressions: number;
    clicks: number;
  };
  comparison?: {
    spend_change: number;
    revenue_change: number;
    roas_change: number;
  };
  isLoading?: boolean;
}
```

**Usage:**
```tsx
<KPITiles
  data={kpiData}
  comparison={comparisonData}
  isLoading={isLoading}
/>
```

---

### SimulatorWidget.tsx

What-If budget simulator.

**Features:**
- Budget slider
- Scenario comparison
- Real-time predictions
- Visual charts

**Simulation Logic:**
```typescript
const runSimulation = async (budgetChange: number) => {
  const result = await predictionsApi.simulate({
    campaign_id: selectedCampaign,
    scenarios: [{ budget_change_percent: budgetChange }],
    time_horizon_days: 30,
  });

  setSimulationResult(result);
};
```

---

### LivePredictionsWidget.tsx

Real-time ML predictions display.

**Features:**
- ROAS predictions
- Trend indicators
- Confidence intervals
- Refresh on interval

**Auto-refresh:**
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    refetchPredictions();
  }, 30000); // 30 seconds

  return () => clearInterval(interval);
}, []);
```

---

## Charts

### DailyTrendChart.tsx

Time-series line chart for metrics trends.

**Props:**
```typescript
interface DailyTrendChartProps {
  data: Array<{
    date: string;
    spend: number;
    revenue: number;
    roas: number;
  }>;
  metrics: ('spend' | 'revenue' | 'roas')[];
  height?: number;
}
```

**Implementation:**
```tsx
<ResponsiveContainer width="100%" height={height}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="date" />
    <YAxis yAxisId="left" />
    <YAxis yAxisId="right" orientation="right" />
    <Tooltip />
    <Legend />
    <Line
      yAxisId="left"
      type="monotone"
      dataKey="spend"
      stroke="#8884d8"
    />
    <Line
      yAxisId="right"
      type="monotone"
      dataKey="roas"
      stroke="#82ca9d"
    />
  </LineChart>
</ResponsiveContainer>
```

---

### PlatformPerformanceChart.tsx

Bar chart comparing platform metrics.

**Implementation:**
```tsx
<ResponsiveContainer width="100%" height={300}>
  <BarChart data={platformData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="platform" />
    <YAxis />
    <Tooltip />
    <Bar dataKey="spend" fill="#6366f1" name="Spend" />
    <Bar dataKey="revenue" fill="#22c55e" name="Revenue" />
  </BarChart>
</ResponsiveContainer>
```

---

## State Management

### AuthContext

Manages authentication state globally.

```typescript
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      validateToken(token).then(setUser).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    setUser(response.user);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
```

---

### ThemeContext

Manages dark/light theme.

```typescript
interface ThemeContextType {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as 'light' | 'dark') || 'light';
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

---

## API Services

### Base API Configuration

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        });
        localStorage.setItem('access_token', response.data.access_token);
        return api.request(error.config);
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Campaign API

```typescript
// services/campaignsApi.ts
import api from './api';

export const campaignsApi = {
  list: async (params: CampaignListParams) => {
    const response = await api.get('/api/v1/campaigns', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get(`/api/v1/campaigns/${id}`);
    return response.data;
  },

  create: async (data: CreateCampaignData) => {
    const response = await api.post('/api/v1/campaigns', data);
    return response.data;
  },

  update: async (id: number, data: UpdateCampaignData) => {
    const response = await api.put(`/api/v1/campaigns/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await api.delete(`/api/v1/campaigns/${id}`);
    return response.data;
  },

  getMetrics: async (id: number, params: MetricsParams) => {
    const response = await api.get(`/api/v1/campaigns/${id}/metrics`, { params });
    return response.data;
  },
};
```

---

## Internationalization (i18n)

### Configuration

```typescript
// i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import ar from './locales/ar.json';
import uk from './locales/uk.json';

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
    uk: { translation: uk },
  },
  lng: localStorage.getItem('language') || 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
```

### Translation Files

```json
// locales/en.json
{
  "common": {
    "loading": "Loading...",
    "error": "An error occurred",
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete"
  },
  "dashboard": {
    "title": "Dashboard",
    "total_spend": "Total Spend",
    "total_revenue": "Total Revenue",
    "roas": "ROAS",
    "conversions": "Conversions"
  },
  "campaigns": {
    "title": "Campaigns",
    "create": "Create Campaign",
    "name": "Campaign Name",
    "platform": "Platform",
    "status": "Status"
  }
}
```

### Usage

```tsx
import { useTranslation } from 'react-i18next';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('dashboard.title')}</h1>
      <KPICard label={t('dashboard.total_spend')} value={spend} />
      <KPICard label={t('dashboard.roas')} value={roas} />
    </div>
  );
};
```

---

## Styling

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eef2ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
      },
    },
  },
  plugins: [],
};
```

### Component Styling

```tsx
// Example styled component
const KPICard: React.FC<KPICardProps> = ({ label, value, change }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
    <p className="text-2xl font-bold text-gray-900 dark:text-white">
      {value}
    </p>
    {change !== undefined && (
      <p className={`text-sm ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
        {change >= 0 ? '+' : ''}{change}%
      </p>
    )}
  </div>
);
```

---

## Development

### Running Locally

```bash
cd frontend
npm install
npm run dev
```

### Building for Production

```bash
npm run build
npm run preview  # Preview production build
```

### Environment Variables

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEFAULT_LOCALE=en
```

---

## Testing

### Unit Tests

```bash
npm run test
```

### Coverage

```bash
npm run test:coverage
```

### Example Test

```typescript
// __tests__/KPICard.test.tsx
import { render, screen } from '@testing-library/react';
import { KPICard } from '../components/dashboard/KPICard';

describe('KPICard', () => {
  it('renders label and value', () => {
    render(<KPICard label="Total Spend" value="$1,234" />);

    expect(screen.getByText('Total Spend')).toBeInTheDocument();
    expect(screen.getByText('$1,234')).toBeInTheDocument();
  });

  it('shows positive change in green', () => {
    render(<KPICard label="ROAS" value="3.5" change={12.5} />);

    const change = screen.getByText('+12.5%');
    expect(change).toHaveClass('text-green-500');
  });
});
```
