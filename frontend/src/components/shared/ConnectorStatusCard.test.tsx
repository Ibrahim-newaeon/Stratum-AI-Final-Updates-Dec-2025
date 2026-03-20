import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConnectorStatusCard } from './ConnectorStatusCard';

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  ArrowPathIcon: (props: any) => <svg data-testid="arrow-path-icon" {...props} />,
  LinkIcon: (props: any) => <svg data-testid="link-icon" {...props} />,
  SignalIcon: (props: any) => <svg data-testid="signal-icon" {...props} />,
}));

// Mock cn utility
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

describe('ConnectorStatusCard', () => {
  it('renders connected platform with health indicator', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
      />
    );
    expect(screen.getByText('Meta Ads')).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('renders disconnected platform', () => {
    render(
      <ConnectorStatusCard
        platform="Google Ads"
        status="disconnected"
        health="disconnected"
      />
    );
    expect(screen.getByText('Google Ads')).toBeInTheDocument();
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('renders degraded health status', () => {
    render(
      <ConnectorStatusCard
        platform="TikTok Ads"
        status="connected"
        health="degraded"
      />
    );
    expect(screen.getByText('Degraded')).toBeInTheDocument();
  });

  it('renders unhealthy health status', () => {
    render(
      <ConnectorStatusCard
        platform="Snapchat"
        status="connected"
        health="unhealthy"
      />
    );
    expect(screen.getByText('Unhealthy')).toBeInTheDocument();
  });

  it('shows EMQ score when connected and provided', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
        emqScore={92}
      />
    );
    expect(screen.getByText('EMQ 92%')).toBeInTheDocument();
  });

  it('does not show EMQ score when disconnected', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="disconnected"
        health="disconnected"
        emqScore={92}
      />
    );
    expect(screen.queryByText('EMQ 92%')).not.toBeInTheDocument();
  });

  it('shows last sync and data volume when connected', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
        lastSync="5 min ago"
        dataVolume="12.4K events"
      />
    );
    expect(screen.getByText('Last Sync')).toBeInTheDocument();
    expect(screen.getByText('5 min ago')).toBeInTheDocument();
    expect(screen.getByText('Data Volume')).toBeInTheDocument();
    expect(screen.getByText('12.4K events')).toBeInTheDocument();
  });

  it('shows "Never" for last sync when not provided', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
      />
    );
    expect(screen.getByText('Never')).toBeInTheDocument();
    expect(screen.getByText('0 events')).toBeInTheDocument();
  });

  it('does not show stats section when disconnected', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="disconnected"
        health="disconnected"
        lastSync="5 min ago"
      />
    );
    expect(screen.queryByText('Last Sync')).not.toBeInTheDocument();
  });

  it('renders Sync Now button when connected and onRefresh is provided', () => {
    const onRefresh = vi.fn();
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
        onRefresh={onRefresh}
      />
    );
    const syncButton = screen.getByText('Sync Now');
    fireEvent.click(syncButton);
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it('renders Disconnect button when connected and onDisconnect is provided', () => {
    const onDisconnect = vi.fn();
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
        onDisconnect={onDisconnect}
      />
    );
    const disconnectButton = screen.getByText('Disconnect');
    fireEvent.click(disconnectButton);
    expect(onDisconnect).toHaveBeenCalledOnce();
  });

  it('renders Connect button when disconnected and onConnect is provided', () => {
    const onConnect = vi.fn();
    render(
      <ConnectorStatusCard
        platform="Google Ads"
        status="disconnected"
        health="disconnected"
        onConnect={onConnect}
      />
    );
    const connectButton = screen.getByText('Connect Google Ads');
    fireEvent.click(connectButton);
    expect(onConnect).toHaveBeenCalledOnce();
  });

  it('renders platform initial when no custom icon provided', () => {
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
      />
    );
    expect(screen.getByText('M')).toBeInTheDocument();
  });

  it('renders custom platform icon when provided', () => {
    const customIcon = <span data-testid="custom-icon">ICON</span>;
    render(
      <ConnectorStatusCard
        platform="Meta Ads"
        status="connected"
        health="healthy"
        platformIcon={customIcon}
      />
    );
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });
});
