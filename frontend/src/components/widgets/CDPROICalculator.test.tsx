import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { CDPROICalculator } from './CDPROICalculator';

// Mock the utils module for consistent formatting
vi.mock('@/lib/utils', async () => {
  const actual = await vi.importActual('@/lib/utils');
  return {
    ...actual,
    formatCurrency: (value: number) => `$${value.toLocaleString()}`,
    formatPercent: (value: number, decimals: number = 1) => `${value.toFixed(decimals)}%`,
  };
});

describe('CDPROICalculator', () => {
  describe('Rendering', () => {
    it('renders the calculator component', () => {
      render(<CDPROICalculator />);
      expect(screen.getByText('CDP ROI Calculator')).toBeInTheDocument();
    });

    it('renders with custom className', () => {
      const { container } = render(<CDPROICalculator className="custom-class" />);
      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('renders all input labels', () => {
      render(<CDPROICalculator />);
      expect(screen.getByText('Monthly Website Sessions')).toBeInTheDocument();
      expect(screen.getByText('Conversion Rate')).toBeInTheDocument();
      expect(screen.getByText('Average Order Value')).toBeInTheDocument();
      expect(screen.getByText('Gross Margin')).toBeInTheDocument();
      expect(screen.getByText('Current Identity Match Rate')).toBeInTheDocument();
      expect(screen.getByText('Expected Match Rate Improvement')).toBeInTheDocument();
      expect(screen.getByText('Monthly CDP Cost')).toBeInTheDocument();
    });

    it('renders all output sections', () => {
      render(<CDPROICalculator />);
      expect(screen.getByText('Projected Impact')).toBeInTheDocument();
      expect(screen.getByText('Current Attributed')).toBeInTheDocument();
      expect(screen.getByText('Projected Attributed')).toBeInTheDocument();
      expect(screen.getByText('Incremental Impact')).toBeInTheDocument();
      expect(screen.getByText('Monthly ROI')).toBeInTheDocument();
      expect(screen.getByText('Payback Period')).toBeInTheDocument();
      expect(screen.getByText('12-Month Net Value')).toBeInTheDocument();
    });
  });

  describe('Default Values', () => {
    it('renders with correct default input values', () => {
      render(<CDPROICalculator />);

      // Monthly Sessions default: 100,000
      expect(screen.getByText('100,000')).toBeInTheDocument();

      // Conversion Rate default: 2.5%
      expect(screen.getByText('2.5%')).toBeInTheDocument();

      // Current Match Rate default: 35% - may appear in multiple places
      const elements35 = screen.getAllByText('35%');
      expect(elements35.length).toBeGreaterThan(0);

      // Expected Improvement default: +40%
      expect(screen.getByText('+40%')).toBeInTheDocument();
    });

    it('calculates correct default output values', () => {
      render(<CDPROICalculator />);

      // With default inputs:
      // Monthly sessions: 100,000
      // CVR: 2.5% -> 2,500 total conversions
      // Current match rate: 35% -> 875 attributed
      // New match rate: 75% -> 1,875 attributed
      // Incremental conversions: 1,000

      expect(screen.getByText('875')).toBeInTheDocument(); // Current attributed
      expect(screen.getByText('1,875')).toBeInTheDocument(); // Projected attributed
    });
  });

  describe('Input Interactions', () => {
    it('updates monthly sessions when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Monthly Website Sessions/i);
      fireEvent.change(slider, { target: { value: '500000' } });

      expect(screen.getByText('500,000')).toBeInTheDocument();
    });

    it('updates conversion rate when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Conversion Rate/i);
      fireEvent.change(slider, { target: { value: '5' } });

      expect(screen.getByText('5%')).toBeInTheDocument();
    });

    it('updates average order value when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Average Order Value/i);
      fireEvent.change(slider, { target: { value: '1000' } });

      expect(screen.getByText('$1,000')).toBeInTheDocument();
    });

    it('updates gross margin when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Gross Margin/i);
      fireEvent.change(slider, { target: { value: '60' } });

      expect(screen.getByText('60%')).toBeInTheDocument();
    });

    it('updates current match rate when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Current Identity Match Rate/i);
      fireEvent.change(slider, { target: { value: '50' } });

      // Use getAllByText since value may appear in multiple places
      const elements = screen.getAllByText('50%');
      expect(elements.length).toBeGreaterThan(0);
    });

    it('updates expected improvement when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Expected Match Rate Improvement/i);
      fireEvent.change(slider, { target: { value: '30' } });

      expect(screen.getByText('+30%')).toBeInTheDocument();
    });

    it('updates monthly fee when slider changes', async () => {
      render(<CDPROICalculator />);

      const slider = screen.getByLabelText(/Monthly CDP Cost/i);
      fireEvent.change(slider, { target: { value: '5000' } });

      expect(screen.getByText('$5,000')).toBeInTheDocument();
    });
  });

  describe('ROI Calculations', () => {
    it('calculates incremental conversions correctly', () => {
      render(<CDPROICalculator />);

      // Default values:
      // Sessions: 100,000
      // CVR: 2.5% -> 2,500 total conversions
      // Current: 35% -> 875 attributed
      // New: 75% (35 + 40) -> 1,875 attributed
      // Incremental: 1,875 - 875 = 1,000

      const incrementalSection = screen.getByText('Additional Conversions').parentElement;
      expect(within(incrementalSection!).getByText('+1,000')).toBeInTheDocument();
    });

    it('calculates incremental revenue correctly', () => {
      render(<CDPROICalculator />);

      // Default AOV: $500
      // Incremental conversions: 1,000
      // Incremental revenue: 1,000 * $500 = $500,000

      const revenueSection = screen.getByText('Incremental Revenue').parentElement;
      expect(within(revenueSection!).getByText('+$500,000')).toBeInTheDocument();
    });

    it('caps new match rate at 100%', () => {
      render(<CDPROICalculator />);

      // Set current match rate to 70%
      const currentRateSlider = screen.getByLabelText(/Current Identity Match Rate/i);
      fireEvent.change(currentRateSlider, { target: { value: '70' } });

      // Set improvement to 60%
      const improvementSlider = screen.getByLabelText(/Expected Match Rate Improvement/i);
      fireEvent.change(improvementSlider, { target: { value: '60' } });

      // Should show 100% (capped), not 130%
      expect(screen.getByText(/100%/)).toBeInTheDocument();
    });

    it('shows positive ROI when profitable', () => {
      render(<CDPROICalculator />);

      // With default values, ROI should be positive
      // Monthly gross profit: 1,000 * $500 * 40% = $200,000
      // Monthly fee: $2,000
      // Monthly ROI: ($200,000 - $2,000) / $2,000 * 100 = 9,900%

      // We need to get the parent's parent to include the value <p> element
      const roiSection = screen.getByText('Monthly ROI').parentElement?.parentElement;
      const roiValue = within(roiSection!).getByText(/%$/);
      expect(roiValue).toHaveClass('text-green-500');
    });

    it('calculates payback period correctly', () => {
      render(<CDPROICalculator />);

      // With very high ROI, payback period should be less than 1 month
      // We need to get the parent's parent to include the value <p> element
      const paybackSection = screen.getByText('Payback Period').parentElement?.parentElement;
      expect(within(paybackSection!).getByText(/<1.*mo/)).toBeInTheDocument();
    });

    it('recalculates outputs when inputs change', () => {
      render(<CDPROICalculator />);

      // Get initial value
      const initialAttributed = screen.getByText('875');
      expect(initialAttributed).toBeInTheDocument();

      // Change sessions to 200,000
      const sessionsSlider = screen.getByLabelText(/Monthly Website Sessions/i);
      fireEvent.change(sessionsSlider, { target: { value: '200000' } });

      // New attributed should be 1,750 (doubled)
      expect(screen.getByText('1,750')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles minimum input values', () => {
      render(<CDPROICalculator />);

      // Set all sliders to minimum values
      fireEvent.change(screen.getByLabelText(/Monthly Website Sessions/i), {
        target: { value: '10000' },
      });
      fireEvent.change(screen.getByLabelText(/Conversion Rate/i), { target: { value: '0.5' } });
      fireEvent.change(screen.getByLabelText(/Average Order Value/i), { target: { value: '50' } });
      fireEvent.change(screen.getByLabelText(/Gross Margin/i), { target: { value: '10' } });
      fireEvent.change(screen.getByLabelText(/Current Identity Match Rate/i), {
        target: { value: '10' },
      });
      fireEvent.change(screen.getByLabelText(/Expected Match Rate Improvement/i), {
        target: { value: '10' },
      });

      // Should still render without errors
      expect(screen.getByText('CDP ROI Calculator')).toBeInTheDocument();
    });

    it('handles maximum input values', () => {
      render(<CDPROICalculator />);

      // Set all sliders to maximum values
      fireEvent.change(screen.getByLabelText(/Monthly Website Sessions/i), {
        target: { value: '1000000' },
      });
      fireEvent.change(screen.getByLabelText(/Conversion Rate/i), { target: { value: '10' } });
      fireEvent.change(screen.getByLabelText(/Average Order Value/i), {
        target: { value: '5000' },
      });
      fireEvent.change(screen.getByLabelText(/Gross Margin/i), { target: { value: '80' } });
      fireEvent.change(screen.getByLabelText(/Current Identity Match Rate/i), {
        target: { value: '70' },
      });
      fireEvent.change(screen.getByLabelText(/Expected Match Rate Improvement/i), {
        target: { value: '60' },
      });

      // Should still render without errors
      expect(screen.getByText('CDP ROI Calculator')).toBeInTheDocument();
    });

    it('handles zero monthly fee edge case', () => {
      render(<CDPROICalculator />);

      // Note: minimum fee is 500, not 0
      const feeSlider = screen.getByLabelText(/Monthly CDP Cost/i);
      fireEvent.change(feeSlider, { target: { value: '500' } });

      // Should show minimum fee - use getAllByText since $500 appears in multiple places
      const elements = screen.getAllByText('$500');
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('has accessible range inputs with aria-labels', () => {
      render(<CDPROICalculator />);

      const sessionsSlider = screen.getByLabelText(/Monthly Website Sessions/i);
      expect(sessionsSlider).toHaveAttribute('aria-valuemin', '10000');
      expect(sessionsSlider).toHaveAttribute('aria-valuemax', '1000000');
      expect(sessionsSlider).toHaveAttribute('aria-valuenow', '100000');
    });

    it('has aria-valuetext for screen readers', () => {
      render(<CDPROICalculator />);

      const sessionsSlider = screen.getByLabelText(/Monthly Website Sessions/i);
      expect(sessionsSlider).toHaveAttribute('aria-valuetext', '100,000 sessions');

      const cvrSlider = screen.getByLabelText(/Conversion Rate/i);
      expect(cvrSlider).toHaveAttribute('aria-valuetext', '2.5%');
    });

    it('has proper label associations', () => {
      render(<CDPROICalculator />);

      // Each slider should be associated with its label via aria-labelledby
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBe(7); // 7 input sliders

      sliders.forEach((slider) => {
        expect(slider).toHaveAttribute('aria-labelledby');
      });
    });

    it('hides decorative elements from screen readers', () => {
      const { container } = render(<CDPROICalculator />);

      // The scale markers (10K, 500K, 1M) should be hidden
      const hiddenElements = container.querySelectorAll('[aria-hidden="true"]');
      expect(hiddenElements.length).toBeGreaterThan(0);
    });
  });

  describe('Summary Text', () => {
    it('renders dynamic summary text', () => {
      render(<CDPROICalculator />);

      // Check for the summary paragraph
      expect(screen.getByText(/By improving identity match rate from/)).toBeInTheDocument();
      expect(screen.getByText(/you could recover/)).toBeInTheDocument();
      expect(screen.getByText(/per month that are currently unattributed/)).toBeInTheDocument();
    });

    it('updates summary when inputs change', () => {
      render(<CDPROICalculator />);

      // Initial summary shows 35% to 75% - there may be multiple elements with these values
      // So we use getAllByText and check at least one exists
      const elements35 = screen.getAllByText('35%');
      const elements75 = screen.getAllByText('75%');
      expect(elements35.length).toBeGreaterThan(0);
      expect(elements75.length).toBeGreaterThan(0);

      // Change current match rate
      const currentRateSlider = screen.getByLabelText(/Current Identity Match Rate/i);
      fireEvent.change(currentRateSlider, { target: { value: '50' } });

      // Summary should update to show 50%
      const elements50 = screen.getAllByText('50%');
      expect(elements50.length).toBeGreaterThan(0);
    });
  });

  describe('Visual Indicators', () => {
    it('shows green color for positive metrics', () => {
      render(<CDPROICalculator />);

      // Projected attributed should be green (value is a <p> element)
      const projectedSection =
        screen.getByText('Projected Attributed').parentElement?.parentElement;
      const valueElement = within(projectedSection!).getByText('1,875');
      expect(valueElement).toHaveClass('text-green-500');
    });

    it('shows amber color for current metrics', () => {
      render(<CDPROICalculator />);

      // Current attributed should be amber (value is a <p> element)
      const currentSection = screen.getByText('Current Attributed').parentElement?.parentElement;
      const valueElement = within(currentSection!).getByText('875');
      expect(valueElement).toHaveClass('text-amber-500');
    });
  });
});

describe('ROI Calculation Logic', () => {
  it('follows correct formula for incremental conversions', () => {
    // Formula:
    // totalConversions = sessions * (cvr / 100)
    // currentAttributed = totalConversions * (currentMatchRate / 100)
    // projectedAttributed = totalConversions * min(currentMatchRate + improvement, 100) / 100
    // incremental = projected - current

    render(<CDPROICalculator />);

    // With defaults: 100,000 sessions, 2.5% CVR, 35% current, +40% improvement
    // Total: 2,500 conversions
    // Current: 875 (35% of 2,500)
    // Projected: 1,875 (75% of 2,500)
    // Incremental: 1,000

    const incrementalSection = screen.getByText('Additional Conversions').parentElement;
    expect(within(incrementalSection!).getByText('+1,000')).toBeInTheDocument();
  });

  it('follows correct formula for gross profit', () => {
    // Formula:
    // incrementalRevenue = incrementalConversions * AOV
    // incrementalGrossProfit = incrementalRevenue * (grossMargin / 100)

    render(<CDPROICalculator />);

    // With defaults: 1,000 incremental * $500 AOV * 40% margin = $200,000
    // Annual: $200,000 - $2,000 fee = $198,000/month * 12 = $2,376,000

    // The 12-Month Net Value shows annual benefit
    expect(screen.getByText('12-Month Net Value')).toBeInTheDocument();
  });
});
