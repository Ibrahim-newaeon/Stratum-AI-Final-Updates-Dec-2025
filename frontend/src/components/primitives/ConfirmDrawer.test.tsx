import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConfirmDrawer } from './ConfirmDrawer';

// Radix Dialog uses pointer-events / focus traps that jsdom partially supports.
describe('ConfirmDrawer', () => {
  it('does not render when closed', () => {
    render(
      <ConfirmDrawer
        open={false}
        onOpenChange={() => {}}
        title="X"
        onConfirm={() => {}}
      />
    );
    expect(screen.queryByText('X')).not.toBeInTheDocument();
  });

  it('renders title + description when open', () => {
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="Pause 14 campaigns"
        description="$48k of daily spend will stop."
        onConfirm={() => {}}
      />
    );
    expect(screen.getByText('Pause 14 campaigns')).toBeInTheDocument();
    expect(screen.getByText('$48k of daily spend will stop.')).toBeInTheDocument();
  });

  it('renders the destructive banner for variant=destructive', () => {
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="X"
        variant="destructive"
        onConfirm={() => {}}
      />
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/cannot be undone/i);
  });

  it('renders preview children inside the body', () => {
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="X"
        onConfirm={() => {}}
      >
        <div data-testid="preview">14 campaigns</div>
      </ConfirmDrawer>
    );
    expect(screen.getByTestId('preview')).toBeInTheDocument();
  });

  it('calls onConfirm when the confirm button is clicked', async () => {
    const handler = vi.fn();
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="X"
        confirmLabel="Yes"
        onConfirm={handler}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /^Yes$/ }));
    await waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
  });

  it('disables the confirm button while loading', () => {
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="X"
        confirmLabel="Yes"
        onConfirm={() => {}}
        loading
      />
    );
    const confirm = screen.getByRole('button', { name: /Working/i });
    expect(confirm).toBeDisabled();
  });

  it('disables the confirm button when disabled=true', () => {
    render(
      <ConfirmDrawer
        open
        onOpenChange={() => {}}
        title="X"
        confirmLabel="Go"
        onConfirm={() => {}}
        disabled
      />
    );
    expect(screen.getByRole('button', { name: 'Go' })).toBeDisabled();
  });
});
