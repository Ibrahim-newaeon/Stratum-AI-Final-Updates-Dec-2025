export { KPIWidget } from './KPIWidget'
export { ChartWidget } from './ChartWidget'
export { CampaignsWidget } from './CampaignsWidget'
export { PlatformBreakdownWidget } from './PlatformBreakdownWidget'
export { AlertsWidget } from './AlertsWidget'
export { QuickActionsWidget } from './QuickActionsWidget'
export { SimulatorWidget } from './SimulatorWidget'
export { LivePredictionsWidget } from './LivePredictionsWidget'
export { ROASAlertsWidget } from './ROASAlertsWidget'
export { BudgetOptimizerWidget } from './BudgetOptimizerWidget'

export type WidgetType =
  | 'kpi-spend'
  | 'kpi-revenue'
  | 'kpi-roas'
  | 'kpi-conversions'
  | 'kpi-ctr'
  | 'kpi-impressions'
  | 'chart-revenue'
  | 'chart-spend'
  | 'chart-performance'
  | 'campaigns-top'
  | 'platform-breakdown'
  | 'alerts'
  | 'quick-actions'
  | 'simulator'
  | 'live-predictions'
  | 'roas-alerts'
  | 'budget-optimizer'

export interface WidgetConfig {
  id: string
  type: WidgetType
  title: string
  x: number
  y: number
  w: number
  h: number
  minW?: number
  minH?: number
  maxW?: number
  maxH?: number
}

export const defaultWidgets: WidgetConfig[] = [
  { id: 'kpi-spend', type: 'kpi-spend', title: 'Total Spend', x: 0, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
  { id: 'kpi-revenue', type: 'kpi-revenue', title: 'Revenue', x: 3, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
  { id: 'kpi-roas', type: 'kpi-roas', title: 'ROAS', x: 6, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
  { id: 'kpi-conversions', type: 'kpi-conversions', title: 'Conversions', x: 9, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
  { id: 'chart-revenue', type: 'chart-revenue', title: 'Revenue Trend', x: 0, y: 2, w: 8, h: 4, minW: 4, minH: 3 },
  { id: 'platform-breakdown', type: 'platform-breakdown', title: 'Platform Breakdown', x: 8, y: 2, w: 4, h: 4, minW: 3, minH: 3 },
  { id: 'campaigns-top', type: 'campaigns-top', title: 'Top Campaigns', x: 0, y: 6, w: 6, h: 4, minW: 4, minH: 3 },
  { id: 'simulator', type: 'simulator', title: 'What-If Simulator', x: 6, y: 6, w: 6, h: 4, minW: 4, minH: 3 },
]

export const availableWidgets: { type: WidgetType; title: string; description: string; defaultSize: { w: number; h: number } }[] = [
  { type: 'kpi-spend', title: 'Total Spend', description: 'Shows total ad spend', defaultSize: { w: 3, h: 2 } },
  { type: 'kpi-revenue', title: 'Revenue', description: 'Shows total revenue', defaultSize: { w: 3, h: 2 } },
  { type: 'kpi-roas', title: 'ROAS', description: 'Return on ad spend', defaultSize: { w: 3, h: 2 } },
  { type: 'kpi-conversions', title: 'Conversions', description: 'Total conversions', defaultSize: { w: 3, h: 2 } },
  { type: 'kpi-ctr', title: 'CTR', description: 'Click-through rate', defaultSize: { w: 3, h: 2 } },
  { type: 'kpi-impressions', title: 'Impressions', description: 'Total impressions', defaultSize: { w: 3, h: 2 } },
  { type: 'chart-revenue', title: 'Revenue Chart', description: 'Revenue trend over time', defaultSize: { w: 8, h: 4 } },
  { type: 'chart-spend', title: 'Spend Chart', description: 'Spend trend over time', defaultSize: { w: 8, h: 4 } },
  { type: 'chart-performance', title: 'Performance Chart', description: 'Overall performance metrics', defaultSize: { w: 8, h: 4 } },
  { type: 'campaigns-top', title: 'Top Campaigns', description: 'Best performing campaigns', defaultSize: { w: 6, h: 4 } },
  { type: 'platform-breakdown', title: 'Platform Breakdown', description: 'Spend by platform', defaultSize: { w: 4, h: 4 } },
  { type: 'alerts', title: 'Alerts', description: 'Recent alerts and notifications', defaultSize: { w: 4, h: 3 } },
  { type: 'quick-actions', title: 'Quick Actions', description: 'Common quick actions', defaultSize: { w: 3, h: 3 } },
  { type: 'simulator', title: 'What-If Simulator', description: 'Budget impact simulator', defaultSize: { w: 6, h: 4 } },
  { type: 'live-predictions', title: 'Live Predictions', description: 'AI-powered campaign predictions', defaultSize: { w: 6, h: 5 } },
  { type: 'roas-alerts', title: 'ROAS Alerts', description: 'Performance alerts and opportunities', defaultSize: { w: 6, h: 5 } },
  { type: 'budget-optimizer', title: 'Budget Optimizer', description: 'AI budget reallocation recommendations', defaultSize: { w: 6, h: 5 } },
]
