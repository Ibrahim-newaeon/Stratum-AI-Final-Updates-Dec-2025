import { useState } from 'react'
import { Calculator, TrendingUp } from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'

interface SimulatorWidgetProps {
  className?: string
}

export function SimulatorWidget({ className }: SimulatorWidgetProps) {
  const [budgetChange, setBudgetChange] = useState(0)
  const currentBudget = 50000
  const currentROAS = 3.5

  const newBudget = currentBudget * (1 + budgetChange / 100)
  const predictedROAS = currentROAS * (1 - budgetChange * 0.005)
  const predictedRevenue = newBudget * predictedROAS

  return (
    <div className={cn('h-full p-4 flex flex-col', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Calculator className="w-5 h-5 text-primary" />
        <span className="font-medium">Budget Simulator</span>
      </div>

      <div className="flex-1 space-y-4">
        <div>
          <label className="text-sm text-muted-foreground">Budget Change: {budgetChange > 0 ? '+' : ''}{budgetChange}%</label>
          <input
            type="range"
            min="-50"
            max="100"
            value={budgetChange}
            onChange={(e) => setBudgetChange(Number(e.target.value))}
            className="w-full mt-2 accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>-50%</span>
            <span>0%</span>
            <span>+100%</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">New Budget</p>
            <p className="text-lg font-bold">{formatCurrency(newBudget)}</p>
          </div>
          <div className="p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Predicted ROAS</p>
            <p className={cn(
              'text-lg font-bold',
              predictedROAS >= currentROAS ? 'text-green-500' : 'text-amber-500'
            )}>
              {predictedROAS.toFixed(2)}x
            </p>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            <p className="text-xs text-muted-foreground">Predicted Revenue</p>
          </div>
          <p className="text-xl font-bold text-primary mt-1">{formatCurrency(predictedRevenue)}</p>
        </div>
      </div>
    </div>
  )
}
