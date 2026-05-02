import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

const mockStore: Record<string, string> = {};
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn((k: string) => mockStore[k] ?? null),
    setItem: vi.fn((k: string, v: string) => {
      mockStore[k] = v;
    }),
    removeItem: vi.fn((k: string) => {
      delete mockStore[k];
    }),
    clear: vi.fn(() => {
      Object.keys(mockStore).forEach((k) => delete mockStore[k]);
    }),
    length: 0,
    key: () => null,
  },
});

import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';
import { Sidebar, type SidebarGroup } from './Sidebar';

const wrap = (ui: ReactElement, path = '/') =>
  render(<MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>);

const groups: SidebarGroup[] = [
  {
    id: 'operate',
    label: 'Operate',
    items: [
      { label: 'Overview', href: '/dashboard/overview' },
      { label: 'Campaigns', href: '/dashboard/campaigns' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { label: 'CDP', href: '/dashboard/cdp' },
      { label: 'Reporting', href: '/dashboard/reporting', badge: '3' },
    ],
  },
];

beforeEach(() => {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
});

describe('Sidebar', () => {
  it('renders all groups and items', () => {
    wrap(<Sidebar groups={groups} currentPath="/dashboard/overview" />, "/dashboard/overview");
    expect(screen.getByText('Operate')).toBeInTheDocument();
    expect(screen.getByText('Intelligence')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('CDP')).toBeInTheDocument();
  });

  it('marks the active item with aria-current="page"', () => {
    wrap(<Sidebar groups={groups} currentPath="/dashboard/overview" />, "/dashboard/overview");
    const link = screen.getByRole('link', { name: /Overview/ });
    expect(link.getAttribute('aria-current')).toBe('page');
  });

  it('treats nested paths as active for the parent route', () => {
    wrap(<Sidebar groups={groups} currentPath="/dashboard/campaigns/123" />, "/dashboard/campaigns/123");
    const link = screen.getByRole('link', { name: /Campaigns/ });
    expect(link.getAttribute('aria-current')).toBe('page');
  });

  it('renders item badges', () => {
    wrap(<Sidebar groups={groups} currentPath="/" />, "/");
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('group header toggles aria-expanded on click', () => {
    wrap(<Sidebar groups={groups} currentPath="/" />, "/");
    // 'Operate' header is initially expanded (no stored state).
    const header = screen.getByRole('button', { name: /Operate/ });
    expect(header.getAttribute('aria-expanded')).toBe('true');
    fireEvent.click(header);
    expect(header.getAttribute('aria-expanded')).toBe('false');
  });

  it('persists collapse state to localStorage', () => {
    wrap(<Sidebar groups={groups} currentPath="/" />, "/");
    fireEvent.click(screen.getByRole('button', { name: /Operate/ }));
    expect(mockStore['stratum-sidebar-groups']).toBeDefined();
    expect(JSON.parse(mockStore['stratum-sidebar-groups']).operate).toBe(true);
  });

  it('force-expands the group containing the active route', () => {
    // Pre-collapse the operate group.
    mockStore['stratum-sidebar-groups'] = JSON.stringify({ operate: true });
    wrap(<Sidebar groups={groups} currentPath="/dashboard/overview" />, "/dashboard/overview");
    const header = screen.getByRole('button', { name: /Operate/ });
    expect(header.getAttribute('aria-expanded')).toBe('true');
  });

  it('renders the brand and footer slots', () => {
    wrap(
      <Sidebar
        groups={groups}
        currentPath="/"
        brand={<span data-testid="brand">stratum.ai</span>}
        footer={<span data-testid="footer">jane@co.com</span>}
      />,
      '/'
    );
    expect(screen.getByTestId('brand')).toBeInTheDocument();
    expect(screen.getByTestId('footer')).toBeInTheDocument();
  });

  it('exposes role=navigation via the <aside> aria-label', () => {
    wrap(<Sidebar groups={groups} currentPath="/" />, "/");
    expect(
      screen.getByRole('complementary', { name: 'Primary navigation' })
    ).toBeInTheDocument();
  });
});
