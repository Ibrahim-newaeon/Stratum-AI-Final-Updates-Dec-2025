import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KPI } from './KPI';

describe('KPI', () => {
  it('renders the label and value', () => {
    render(<KPI label="ROAS (7d)" value="4.2x" />);
    expect(screen.getByText('ROAS (7d)')).toBeInTheDocument();
    expect(screen.getByText('4.2x')).toBeInTheDocument();
  });

  it('renders the empty placeholder when value is null', () => {
    render(<KPI label="ROAS" value={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('renders a custom empty placeholder', () => {
    render(<KPI label="ROAS" value={undefined} empty="Telemetry pending" />);
    expect(screen.getByText('Telemetry pending')).toBeInTheDocument();
  });

  it('renders a loading skeleton', () => {
    const { container } = render(<KPI label="ROAS" loading />);
    const skel = container.querySelector('.animate-pulse');
    expect(skel).not.toBeNull();
  });

  it('renders an error message and falls back the value', () => {
    render(<KPI label="ROAS" value="4.2x" error="Couldn't load" />);
    expect(screen.getByText("Couldn't load")).toBeInTheDocument();
    // value text is replaced by em dash on error
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('renders a positive percent delta', () => {
    render(<KPI label="x" value="100" delta={{ value: 12.4 }} />);
    expect(screen.getByText('+12.4%')).toBeInTheDocument();
  });

  it('renders a negative percent delta with figure-dash sign', () => {
    render(<KPI label="x" value="100" delta={{ value: -3.5 }} />);
    expect(screen.getByText(/3\.5%/)).toBeInTheDocument();
  });

  it('inverts tone when invert=true (down is good)', () => {
    // CAC fell — that's good. invert=true means negative-value → success.
    render(<KPI label="CAC" value="$42" delta={{ value: -8, invert: true }} />);
    const deltaText = screen.getByText(/8.0%/);
    expect(deltaText.className).toContain('text-success');
  });

  it('renders an absolute-format delta', () => {
    render(<KPI label="Predictions" value="12,345" delta={{ value: 240, format: 'absolute' }} />);
    expect(screen.getByText('+240')).toBeInTheDocument();
  });

  it('renders a footnote', () => {
    render(<KPI label="x" value="1" footnote="vs. last week" />);
    expect(screen.getByText('vs. last week')).toBeInTheDocument();
  });

  it('renders a status pill in the top-right slot', () => {
    render(
      <KPI
        label="Trust Gate"
        value="Pass"
        status={{ label: 'Operational', variant: 'healthy', pulse: true }}
      />
    );
    expect(screen.getByText('Operational')).toBeInTheDocument();
  });

  it('does not render delta when loading', () => {
    render(<KPI label="x" loading delta={{ value: 5 }} />);
    expect(screen.queryByText('+5.0%')).not.toBeInTheDocument();
  });
});
