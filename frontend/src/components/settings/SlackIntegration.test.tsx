/**
 * SlackIntegration Component Tests
 *
 * Tests for rendering, webhook URL input, toggle notifications,
 * test connection, and save functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('lucide-react', () => ({
  Activity: (props: any) => <svg {...props} />,
  AlertTriangle: (props: any) => <svg {...props} />,
  BarChart3: (props: any) => <svg {...props} />,
  CheckCircle2: (props: any) => <svg {...props} />,
  Clock: (props: any) => <svg {...props} />,
  ExternalLink: (props: any) => <svg {...props} />,
  Loader2: (props: any) => <svg data-testid="loader" {...props} />,
  Shield: (props: any) => <svg {...props} />,
  XCircle: (props: any) => <svg {...props} />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

import { SlackIntegration } from './SlackIntegration';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SlackIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset fetch mock
    global.fetch = vi.fn();
  });

  it('renders the component header', () => {
    render(<SlackIntegration />);

    expect(screen.getByText('Slack Integration')).toBeInTheDocument();
    expect(
      screen.getByText('Receive Trust Gate alerts and reports in your Slack channels')
    ).toBeInTheDocument();
  });

  it('renders the webhook URL input', () => {
    render(<SlackIntegration />);

    const input = screen.getByPlaceholderText('https://hooks.slack.com/services/...');
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue('');
  });

  it('renders the webhook URL with initial config', () => {
    render(
      <SlackIntegration
        initialConfig={{ webhookUrl: 'https://hooks.slack.com/services/abc' }}
      />
    );

    expect(
      screen.getByPlaceholderText('https://hooks.slack.com/services/...')
    ).toHaveValue('https://hooks.slack.com/services/abc');
  });

  it('renders the enable notifications toggle', () => {
    render(<SlackIntegration />);

    expect(screen.getByText('Enable Notifications')).toBeInTheDocument();
    expect(screen.getByText('Send alerts to Slack')).toBeInTheDocument();
  });

  it('renders all notification type options', () => {
    render(<SlackIntegration />);

    expect(screen.getByText('Trust Gate Blocked')).toBeInTheDocument();
    expect(screen.getByText('Trust Gate Hold')).toBeInTheDocument();
    expect(screen.getByText('Trust Gate Pass')).toBeInTheDocument();
    expect(screen.getByText('Signal Health Alerts')).toBeInTheDocument();
    expect(screen.getByText('Anomaly Detection')).toBeInTheDocument();
    expect(screen.getByText('Daily Summary')).toBeInTheDocument();
    expect(screen.getByText('Weekly Summary')).toBeInTheDocument();
  });

  it('shows "Recommended" badges on appropriate options', () => {
    render(<SlackIntegration />);

    const recommendedBadges = screen.getAllByText('Recommended');
    expect(recommendedBadges.length).toBe(4);
  });

  it('shows the count of enabled notifications', () => {
    render(<SlackIntegration />);

    // Default config has 5 enabled (trustGateHold, trustGateBlock, signalHealthAlerts, anomalyDetection, dailySummary)
    expect(screen.getByText('5 enabled')).toBeInTheDocument();
  });

  it('disables the Test button when webhook URL is empty', () => {
    render(<SlackIntegration />);

    const testButton = screen.getByText('Test');
    expect(testButton).toBeDisabled();
  });

  it('enables the Test button when webhook URL is provided', () => {
    render(<SlackIntegration />);

    const input = screen.getByPlaceholderText('https://hooks.slack.com/services/...');
    fireEvent.change(input, {
      target: { value: 'https://hooks.slack.com/services/abc' },
    });

    expect(screen.getByText('Test')).not.toBeDisabled();
  });

  it('shows "All changes saved" initially and "unsaved changes" after modification', () => {
    render(<SlackIntegration />);

    expect(screen.getByText('All changes saved')).toBeInTheDocument();

    const input = screen.getByPlaceholderText('https://hooks.slack.com/services/...');
    fireEvent.change(input, {
      target: { value: 'https://hooks.slack.com/services/new' },
    });

    expect(screen.getByText('You have unsaved changes')).toBeInTheDocument();
  });

  it('disables Save Changes button when there are no changes', () => {
    render(<SlackIntegration />);

    const saveButton = screen.getByText('Save Changes');
    expect(saveButton).toBeDisabled();
  });

  it('enables Save Changes button after making changes', () => {
    render(<SlackIntegration />);

    fireEvent.change(
      screen.getByPlaceholderText('https://hooks.slack.com/services/...'),
      { target: { value: 'https://hooks.slack.com/test' } }
    );

    expect(screen.getByText('Save Changes')).not.toBeDisabled();
  });

  it('calls onSave with config when Save Changes is clicked', async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);

    render(<SlackIntegration onSave={handleSave} />);

    // Change webhook URL to enable Save
    fireEvent.change(
      screen.getByPlaceholderText('https://hooks.slack.com/services/...'),
      { target: { value: 'https://hooks.slack.com/services/test' } }
    );

    fireEvent.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(handleSave).toHaveBeenCalledWith(
        expect.objectContaining({
          webhookUrl: 'https://hooks.slack.com/services/test',
        })
      );
    });
  });

  it('renders the help link for creating webhooks', () => {
    render(<SlackIntegration />);

    const helpLink = screen.getByText('How to create a Slack webhook');
    expect(helpLink.closest('a')).toHaveAttribute(
      'href',
      'https://api.slack.com/messaging/webhooks'
    );
  });

  it('toggles notification options when clicked', () => {
    render(<SlackIntegration />);

    // "Trust Gate Pass" is off by default, click to toggle it on
    fireEvent.click(screen.getByText('Trust Gate Pass'));

    // After toggle, the count should now be 6
    expect(screen.getByText('6 enabled')).toBeInTheDocument();
  });
});
