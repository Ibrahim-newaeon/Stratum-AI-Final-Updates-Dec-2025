import { useState, useMemo, useCallback } from 'react'
import { Calculator, TrendingUp, DollarSign, Users, BarChart3, Clock } from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'

interface CDPROICalculatorProps {
  className?: string
  /** Currency code (e.g., 'USD', 'SAR', 'EUR') */
  currency?: string
  /** Locale for number formatting (e.g., 'en-US', 'ar-SA') */
  locale?: string
}

interface CalculatorInputs {
  monthlySessions: number
  conversionRate: number
  averageOrderValue: number
  grossMarginPercent: number
  currentMatchRate: number
  expectedMatchRateImprovement: number
  monthlyPlatformFee: number
}

interface CalculatorOutputs {
  currentAttributedConversions: number
  projectedAttributedConversions: number
  incrementalConversions: number
  incrementalRevenue: number
  incrementalGrossProfit: number
  monthlyROI: number
  paybackPeriodMonths: number
  annualValue: number
}

const defaultInputs: CalculatorInputs = {
  monthlySessions: 100000,
  conversionRate: 2.5,
  averageOrderValue: 500,
  grossMarginPercent: 40,
  currentMatchRate: 35,
  expectedMatchRateImprovement: 40,
  monthlyPlatformFee: 2000,
}

function calculateROI(inputs: CalculatorInputs): CalculatorOutputs {
  const {
    monthlySessions,
    conversionRate,
    averageOrderValue,
    grossMarginPercent,
    currentMatchRate,
    expectedMatchRateImprovement,
    monthlyPlatformFee,
  } = inputs

  // Current state
  const totalConversions = (monthlySessions * conversionRate) / 100
  const currentAttributedConversions = totalConversions * (currentMatchRate / 100)

  // Projected state with CDP
  const newMatchRate = Math.min(currentMatchRate + expectedMatchRateImprovement, 100)
  const projectedAttributedConversions = totalConversions * (newMatchRate / 100)

  // Incremental impact
  const incrementalConversions = projectedAttributedConversions - currentAttributedConversions
  const incrementalRevenue = incrementalConversions * averageOrderValue
  const incrementalGrossProfit = incrementalRevenue * (grossMarginPercent / 100)

  // ROI calculations
  const monthlyNetBenefit = incrementalGrossProfit - monthlyPlatformFee
  const monthlyROI = monthlyPlatformFee > 0 ? (monthlyNetBenefit / monthlyPlatformFee) * 100 : 0
  const paybackPeriodMonths = monthlyNetBenefit > 0 ? monthlyPlatformFee / monthlyNetBenefit : 999
  const annualValue = monthlyNetBenefit * 12

  return {
    currentAttributedConversions: Math.round(currentAttributedConversions),
    projectedAttributedConversions: Math.round(projectedAttributedConversions),
    incrementalConversions: Math.round(incrementalConversions),
    incrementalRevenue,
    incrementalGrossProfit,
    monthlyROI,
    paybackPeriodMonths: Math.max(0, paybackPeriodMonths),
    annualValue,
  }
}

export function CDPROICalculator({
  className,
  currency = 'USD',
  locale = 'en-US',
}: CDPROICalculatorProps) {
  const [inputs, setInputs] = useState<CalculatorInputs>(defaultInputs)

  const outputs = useMemo(() => calculateROI(inputs), [inputs])

  const updateInput = (key: keyof CalculatorInputs, value: number) => {
    setInputs((prev) => ({ ...prev, [key]: value }))
  }

  // Memoized currency formatter using locale/currency props
  const format = useCallback(
    (value: number) => formatCurrency(value, currency, locale),
    [currency, locale]
  )

  return (
    <div className={cn('bg-card border border-border rounded-xl p-6', className)}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-primary/10">
          <Calculator className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-lg">CDP ROI Calculator</h3>
          <p className="text-sm text-muted-foreground">
            Estimate the impact of improved identity resolution
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Inputs */}
        <div className="space-y-5">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
            Your Metrics
          </h4>

          {/* Monthly Sessions */}
          <div>
            <label
              id="monthly-sessions-label"
              className="flex items-center justify-between text-sm mb-2"
            >
              <span>Monthly Website Sessions</span>
              <span className="font-mono text-primary">
                {inputs.monthlySessions.toLocaleString()}
              </span>
            </label>
            <input
              type="range"
              min="10000"
              max="1000000"
              step="10000"
              value={inputs.monthlySessions}
              onChange={(e) => updateInput('monthlySessions', Number(e.target.value))}
              className="w-full accent-primary"
              aria-labelledby="monthly-sessions-label"
              aria-valuemin={10000}
              aria-valuemax={1000000}
              aria-valuenow={inputs.monthlySessions}
              aria-valuetext={`${inputs.monthlySessions.toLocaleString()} sessions`}
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1" aria-hidden="true">
              <span>10K</span>
              <span>500K</span>
              <span>1M</span>
            </div>
          </div>

          {/* Conversion Rate */}
          <div>
            <label id="conversion-rate-label" className="flex items-center justify-between text-sm mb-2">
              <span>Conversion Rate</span>
              <span className="font-mono text-primary">{inputs.conversionRate}%</span>
            </label>
            <input
              type="range"
              min="0.5"
              max="10"
              step="0.1"
              value={inputs.conversionRate}
              onChange={(e) => updateInput('conversionRate', Number(e.target.value))}
              className="w-full accent-primary"
              aria-labelledby="conversion-rate-label"
              aria-valuemin={0.5}
              aria-valuemax={10}
              aria-valuenow={inputs.conversionRate}
              aria-valuetext={`${inputs.conversionRate}%`}
            />
          </div>

          {/* Average Order Value */}
          <div>
            <label id="aov-label" className="flex items-center justify-between text-sm mb-2">
              <span>Average Order Value</span>
              <span className="font-mono text-primary">{format(inputs.averageOrderValue)}</span>
            </label>
            <input
              type="range"
              min="50"
              max="5000"
              step="50"
              value={inputs.averageOrderValue}
              onChange={(e) => updateInput('averageOrderValue', Number(e.target.value))}
              className="w-full accent-primary"
              aria-labelledby="aov-label"
              aria-valuemin={50}
              aria-valuemax={5000}
              aria-valuenow={inputs.averageOrderValue}
              aria-valuetext={format(inputs.averageOrderValue)}
            />
          </div>

          {/* Gross Margin */}
          <div>
            <label id="gross-margin-label" className="flex items-center justify-between text-sm mb-2">
              <span>Gross Margin</span>
              <span className="font-mono text-primary">{inputs.grossMarginPercent}%</span>
            </label>
            <input
              type="range"
              min="10"
              max="80"
              step="5"
              value={inputs.grossMarginPercent}
              onChange={(e) => updateInput('grossMarginPercent', Number(e.target.value))}
              className="w-full accent-primary"
              aria-labelledby="gross-margin-label"
              aria-valuemin={10}
              aria-valuemax={80}
              aria-valuenow={inputs.grossMarginPercent}
              aria-valuetext={`${inputs.grossMarginPercent}%`}
            />
          </div>

          {/* Current Match Rate */}
          <div>
            <label id="current-match-rate-label" className="flex items-center justify-between text-sm mb-2">
              <span>Current Identity Match Rate</span>
              <span className="font-mono text-amber-500">{inputs.currentMatchRate}%</span>
            </label>
            <input
              type="range"
              min="10"
              max="70"
              step="5"
              value={inputs.currentMatchRate}
              onChange={(e) => updateInput('currentMatchRate', Number(e.target.value))}
              className="w-full accent-amber-500"
              aria-labelledby="current-match-rate-label"
              aria-valuemin={10}
              aria-valuemax={70}
              aria-valuenow={inputs.currentMatchRate}
              aria-valuetext={`${inputs.currentMatchRate}%`}
            />
          </div>

          {/* Expected Improvement */}
          <div>
            <label id="improvement-label" className="flex items-center justify-between text-sm mb-2">
              <span>Expected Match Rate Improvement</span>
              <span className="font-mono text-green-500">+{inputs.expectedMatchRateImprovement}%</span>
            </label>
            <input
              type="range"
              min="10"
              max="60"
              step="5"
              value={inputs.expectedMatchRateImprovement}
              onChange={(e) => updateInput('expectedMatchRateImprovement', Number(e.target.value))}
              className="w-full accent-green-500"
              aria-labelledby="improvement-label"
              aria-valuemin={10}
              aria-valuemax={60}
              aria-valuenow={inputs.expectedMatchRateImprovement}
              aria-valuetext={`+${inputs.expectedMatchRateImprovement}%`}
            />
          </div>

          {/* Monthly Fee */}
          <div>
            <label id="monthly-fee-label" className="flex items-center justify-between text-sm mb-2">
              <span>Monthly CDP Cost</span>
              <span className="font-mono text-muted-foreground">{format(inputs.monthlyPlatformFee)}</span>
            </label>
            <input
              type="range"
              min="500"
              max="10000"
              step="500"
              value={inputs.monthlyPlatformFee}
              onChange={(e) => updateInput('monthlyPlatformFee', Number(e.target.value))}
              className="w-full accent-muted-foreground"
              aria-labelledby="monthly-fee-label"
              aria-valuemin={500}
              aria-valuemax={10000}
              aria-valuenow={inputs.monthlyPlatformFee}
              aria-valuetext={format(inputs.monthlyPlatformFee)}
            />
          </div>
        </div>

        {/* Outputs */}
        <div className="space-y-5">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
            Projected Impact
          </h4>

          {/* Match Rate Comparison */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-amber-500" />
                <span className="text-xs text-muted-foreground">Current Attributed</span>
              </div>
              <p className="text-2xl font-bold text-amber-500">
                {outputs.currentAttributedConversions.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">conversions/mo</p>
            </div>
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-green-500" />
                <span className="text-xs text-muted-foreground">Projected Attributed</span>
              </div>
              <p className="text-2xl font-bold text-green-500">
                {outputs.projectedAttributedConversions.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">conversions/mo</p>
            </div>
          </div>

          {/* Incremental Impact */}
          <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Incremental Impact</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Additional Conversions</p>
                <p className="text-xl font-bold text-primary">
                  +{outputs.incrementalConversions.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Incremental Revenue</p>
                <p className="text-xl font-bold text-primary">
                  +{format(outputs.incrementalRevenue)}
                </p>
              </div>
            </div>
          </div>

          {/* ROI Metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Monthly ROI</span>
              </div>
              <p className={cn(
                'text-2xl font-bold',
                outputs.monthlyROI >= 100 ? 'text-green-500' : outputs.monthlyROI >= 0 ? 'text-amber-500' : 'text-red-500'
              )}>
                {outputs.monthlyROI.toFixed(0)}%
              </p>
            </div>
            <div className="p-4 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Payback Period</span>
              </div>
              <p className={cn(
                'text-2xl font-bold',
                outputs.paybackPeriodMonths <= 1 ? 'text-green-500' : outputs.paybackPeriodMonths <= 3 ? 'text-amber-500' : 'text-muted-foreground'
              )}>
                {outputs.paybackPeriodMonths < 1 ? '<1' : outputs.paybackPeriodMonths.toFixed(1)} mo
              </p>
            </div>
          </div>

          {/* Annual Value */}
          <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-primary" />
              <span className="text-sm font-medium">12-Month Net Value</span>
            </div>
            <p className={cn(
              'text-3xl font-bold',
              outputs.annualValue >= 0 ? 'text-primary' : 'text-red-500'
            )}>
              {format(outputs.annualValue)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              After CDP costs ({format(inputs.monthlyPlatformFee * 12)}/year)
            </p>
          </div>

          {/* Summary */}
          <div className="p-4 rounded-lg bg-muted/20 border border-border">
            <p className="text-sm text-muted-foreground leading-relaxed">
              By improving identity match rate from{' '}
              <span className="font-medium text-amber-500">{inputs.currentMatchRate}%</span> to{' '}
              <span className="font-medium text-green-500">
                {Math.min(inputs.currentMatchRate + inputs.expectedMatchRateImprovement, 100)}%
              </span>
              , you could recover{' '}
              <span className="font-medium text-primary">
                {outputs.incrementalConversions.toLocaleString()} conversions
              </span>{' '}
              per month that are currently unattributed.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
