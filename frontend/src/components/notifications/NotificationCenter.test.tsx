/**
 * NotificationCenter + NotificationBell Tests
 *
 * Tests for rendering, filtering, mark-as-read, delete,
 * clear-all, and keyboard behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock framer-motion to simplify rendering
vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Activity: (props: any) => <svg data-testid="icon-activity" {...props} />,
  AlertTriangle: (props: any) => <svg data-testid="icon-alert" {...props} />,
  Bell: (props: any) => <svg data-testid="icon-bell" {...props} />,
  Check: (props: any) => <svg data-testid="icon-check" {...props} />,
  CheckCheck: (props: any) => <svg data-testid="icon-check-check" {...props} />,
  Clock: (props: any) => <svg data-testid="icon-clock" {...props} />,
  Settings: (props: any) => <svg data-testid="icon-settings" {...props} />,
  Shield: (props: any) => <svg data-testid="icon-shield" {...props} />,
  Trash2: (props: any) => <svg data-testid="icon-trash" {...props} />,
  TrendingUp: (props: any) => <svg data-testid="icon-trending" {...props} />,
  Users: (props: any) => <svg data-testid="icon-users" {...props} />,
  X: (props: any) => <svg data-testid="icon-x" {...props} />,
  XCircle: (props: any) => <svg data-testid="icon-x-circle" {...props} />,
  Zap: (props: any) => <svg data-testid="icon-zap" {...props} />,
}));

import { NotificationCenter, NotificationBell } from './NotificationCenter';

// ---------------------------------------------------------------------------
// NotificationCenter Tests
// ---------------------------------------------------------------------------

describe('NotificationCenter', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <NotificationCenter isOpen={false} onClose={mockOnClose} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders the panel when isOpen is true', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  it('displays unread count in the header', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    // The demo data has 3 unread notifications
    expect(screen.getByText('3 unread')).toBeInTheDocument();
  });

  it('renders All and Unread filter buttons', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText(/Unread/)).toBeInTheDocument();
  });

  it('shows demo notifications by default', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText('Trust Gate Blocked')).toBeInTheDocument();
    expect(screen.getByText('Anomaly Detected')).toBeInTheDocument();
    expect(screen.getByText('Automation Executed')).toBeInTheDocument();
  });

  it('filters to show only unread notifications', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    // Click "Unread" filter
    fireEvent.click(screen.getByText(/Unread/));

    // Unread notifications should be visible
    expect(screen.getByText('Trust Gate Blocked')).toBeInTheDocument();
    expect(screen.getByText('Anomaly Detected')).toBeInTheDocument();

    // Read notifications should be hidden
    expect(screen.queryByText('Signal Health Improved')).not.toBeInTheDocument();
    expect(screen.queryByText('Segment Updated')).not.toBeInTheDocument();
  });

  it('shows empty state when all notifications are cleared', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    // Click "Clear all" button
    const clearButton = screen.getByTitle('Clear all');
    fireEvent.click(clearButton);

    expect(screen.getByText('No notifications')).toBeInTheDocument();
    expect(screen.getByText("You're all caught up!")).toBeInTheDocument();
  });

  it('calls onClose when backdrop is clicked', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    // Click the backdrop (first motion.div with fixed inset-0)
    const backdrop = screen.getByText('Notifications').closest('[class*="fixed"]')
      ?.previousElementSibling;
    if (backdrop) {
      fireEvent.click(backdrop);
    }

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape key is pressed', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('renders the Notification Settings link in the footer', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText('Notification Settings')).toBeInTheDocument();
  });

  it('marks all as read removes the unread indicator', () => {
    render(<NotificationCenter isOpen={true} onClose={mockOnClose} />);

    // Click "Mark all as read"
    const markAllButton = screen.getByTitle('Mark all as read');
    fireEvent.click(markAllButton);

    // Should now show "All caught up!"
    expect(screen.getByText('All caught up!')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NotificationBell Tests
// ---------------------------------------------------------------------------

describe('NotificationBell', () => {
  it('renders the bell icon', () => {
    render(<NotificationBell onClick={vi.fn()} />);

    expect(screen.getByTestId('icon-bell')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<NotificationBell onClick={handleClick} />);

    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows badge with unread count', () => {
    render(<NotificationBell onClick={vi.fn()} unreadCount={5} />);

    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows 9+ when unread count exceeds 9', () => {
    render(<NotificationBell onClick={vi.fn()} unreadCount={15} />);

    expect(screen.getByText('9+')).toBeInTheDocument();
  });

  it('does not show badge when unread count is 0', () => {
    render(<NotificationBell onClick={vi.fn()} unreadCount={0} />);

    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
