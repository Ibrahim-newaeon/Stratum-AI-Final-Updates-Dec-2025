import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import { EmergencyStop } from './EmergencyStop';

vi.mock('@/api/autopilot', () => ({
  useEnforcementSettings: vi.fn(),
  useSetFreeze: vi.fn(),
}));

vi.mock('@/components/ui/use-toast', () => ({
  useToast: vi.fn(() => ({ toast: vi.fn() })),
}));

import { useEnforcementSettings, useSetFreeze } from '@/api/autopilot';

const mockUseEnforcementSettings = useEnforcementSettings as ReturnType<typeof vi.fn>;
const mockUseSetFreeze = useSetFreeze as ReturnType<typeof vi.fn>;

const mutateAsync = vi.fn();

function setSettings({
  frozen = false,
  isLoading = false,
  isError = false,
}: { frozen?: boolean; isLoading?: boolean; isError?: boolean } = {}) {
  mockUseEnforcementSettings.mockReturnValue({
    data:
      isLoading || isError
        ? undefined
        : { enforcement_enabled: true, autopilot_frozen: frozen, default_mode: 'advisory' },
    isLoading,
    isError,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mutateAsync.mockResolvedValue({ autopilot_frozen: true, message: 'ok' });
  mockUseSetFreeze.mockReturnValue({ mutateAsync, isPending: false });
  setSettings({ frozen: false });
});

describe('EmergencyStop', () => {
  it('renders the active (not frozen) state', () => {
    render(<EmergencyStop tenantId={1} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Freeze autopilot' })).toBeInTheDocument();
  });

  it('renders the frozen state', () => {
    setSettings({ frozen: true });
    render(<EmergencyStop tenantId={1} />);
    expect(screen.getByText('Frozen')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Resume autopilot' })).toBeInTheDocument();
  });

  it('freezes through the confirm drawer', async () => {
    render(<EmergencyStop tenantId={1} />);

    fireEvent.click(screen.getByRole('button', { name: 'Freeze autopilot' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Freeze all autopilot execution')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: 'Freeze autopilot' }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ frozen: true, reason: undefined })
    );
  });

  it('captures an audited reason when provided', async () => {
    render(<EmergencyStop tenantId={1} />);

    fireEvent.click(screen.getByRole('button', { name: 'Freeze autopilot' }));
    const dialog = await screen.findByRole('dialog');

    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Meta reporting outage' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Freeze autopilot' }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        frozen: true,
        reason: 'Meta reporting outage',
      })
    );
  });

  it('resumes when already frozen', async () => {
    setSettings({ frozen: true });
    render(<EmergencyStop tenantId={1} />);

    fireEvent.click(screen.getByRole('button', { name: 'Resume autopilot' }));
    const dialog = await screen.findByRole('dialog');

    fireEvent.click(within(dialog).getByRole('button', { name: 'Resume autopilot' }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ frozen: false, reason: undefined })
    );
  });

  it('disables the toggle while settings are loading', () => {
    setSettings({ isLoading: true });
    render(<EmergencyStop tenantId={1} />);
    // aria-label falls back to "Freeze autopilot" (frozen defaults false)
    expect(screen.getByRole('button', { name: 'Freeze autopilot' })).toBeDisabled();
  });
});
