import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AutopilotModeBanner } from './AutopilotModeBanner';
import type { AutopilotMode } from './AutopilotModeBanner';

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  PlayCircleIcon: (props: any) => <svg data-testid="play-icon" {...props} />,
  PauseCircleIcon: (props: any) => <svg data-testid="pause-icon" {...props} />,
  ExclamationTriangleIcon: (props: any) => <svg data-testid="exclamation-icon" {...props} />,
  XCircleIcon: (props: any) => <svg data-testid="x-circle-icon" {...props} />,
}));

// Mock cn utility
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

describe('AutopilotModeBanner', () => {
  it('renders normal mode with correct label and description', () => {
    render(<AutopilotModeBanner mode="normal" />);
    expect(screen.getByText('Autopilot: Normal')).toBeInTheDocument();
    expect(screen.getByText('Full automation enabled')).toBeInTheDocument();
  });

  it('renders limited mode with correct label and description', () => {
    render(<AutopilotModeBanner mode="limited" />);
    expect(screen.getByText('Autopilot: Limited')).toBeInTheDocument();
    expect(screen.getByText('Scaling capped at +10%')).toBeInTheDocument();
  });

  it('renders cuts_only mode with correct label and description', () => {
    render(<AutopilotModeBanner mode="cuts_only" />);
    expect(screen.getByText('Autopilot: Cuts Only')).toBeInTheDocument();
    expect(screen.getByText('Only pauses and reductions allowed')).toBeInTheDocument();
  });

  it('renders frozen mode with correct label and description', () => {
    render(<AutopilotModeBanner mode="frozen" />);
    expect(screen.getByText('Autopilot: Frozen')).toBeInTheDocument();
    expect(screen.getByText('All automation paused')).toBeInTheDocument();
  });

  it('renders allowed actions for normal mode', () => {
    render(<AutopilotModeBanner mode="normal" />);
    expect(screen.getByText('Scale budgets up/down')).toBeInTheDocument();
    expect(screen.getByText('Pause/activate campaigns')).toBeInTheDocument();
    expect(screen.getByText('Apply all recommendations')).toBeInTheDocument();
  });

  it('renders allowed actions for frozen mode', () => {
    render(<AutopilotModeBanner mode="frozen" />);
    expect(screen.getByText('No actions allowed')).toBeInTheDocument();
    expect(screen.getByText('Focus on fixing data issues')).toBeInTheDocument();
    expect(screen.getByText('Manual control only')).toBeInTheDocument();
  });

  it('hides description when showDescription is false', () => {
    render(<AutopilotModeBanner mode="normal" showDescription={false} />);
    expect(screen.getByText('Autopilot: Normal')).toBeInTheDocument();
    expect(screen.queryByText('Full automation enabled')).not.toBeInTheDocument();
    expect(screen.queryByText('Scale budgets up/down')).not.toBeInTheDocument();
  });

  it('renders compact variant with just label', () => {
    render(<AutopilotModeBanner mode="normal" compact />);
    expect(screen.getByText('Normal')).toBeInTheDocument();
    // Compact should not show the full "Autopilot: Normal" heading
    expect(screen.queryByText('Autopilot: Normal')).not.toBeInTheDocument();
    // Should not show description
    expect(screen.queryByText('Full automation enabled')).not.toBeInTheDocument();
  });

  it('renders compact variant for each mode', () => {
    const modes: AutopilotMode[] = ['normal', 'limited', 'cuts_only', 'frozen'];
    const labels = ['Normal', 'Limited', 'Cuts Only', 'Frozen'];

    modes.forEach((mode, index) => {
      const { unmount } = render(<AutopilotModeBanner mode={mode} compact />);
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('applies custom className', () => {
    const { container } = render(
      <AutopilotModeBanner mode="normal" className="my-custom" />
    );
    expect(container.firstChild).toHaveClass('my-custom');
  });

  it('applies custom className in compact mode', () => {
    const { container } = render(
      <AutopilotModeBanner mode="normal" compact className="compact-custom" />
    );
    expect(container.firstChild).toHaveClass('compact-custom');
  });

  it('renders the correct icon for each mode', () => {
    const { unmount: u1 } = render(<AutopilotModeBanner mode="normal" compact />);
    expect(screen.getByTestId('play-icon')).toBeInTheDocument();
    u1();

    const { unmount: u2 } = render(<AutopilotModeBanner mode="limited" compact />);
    expect(screen.getByTestId('pause-icon')).toBeInTheDocument();
    u2();

    const { unmount: u3 } = render(<AutopilotModeBanner mode="cuts_only" compact />);
    expect(screen.getByTestId('exclamation-icon')).toBeInTheDocument();
    u3();

    render(<AutopilotModeBanner mode="frozen" compact />);
    expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();
  });
});
