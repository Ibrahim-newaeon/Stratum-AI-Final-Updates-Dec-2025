import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import GridLayout, { Layout } from 'react-grid-layout'
import {
  Settings,
  Plus,
  RotateCcw,
  Save,
  X,
  GripVertical,
  Trash2,
  LayoutDashboard,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { KPIWidget } from '@/components/widgets/KPIWidget'
import { ChartWidget } from '@/components/widgets/ChartWidget'
import { CampaignsWidget } from '@/components/widgets/CampaignsWidget'
import { PlatformBreakdownWidget } from '@/components/widgets/PlatformBreakdownWidget'
import { AlertsWidget } from '@/components/widgets/AlertsWidget'
import { QuickActionsWidget } from '@/components/widgets/QuickActionsWidget'
import { SimulatorWidget } from '@/components/widgets/SimulatorWidget'
import { WidgetConfig, WidgetType, defaultWidgets, availableWidgets } from '@/components/widgets'

import 'react-grid-layout/css/styles.css'

const GRID_COLS = 12
const ROW_HEIGHT = 80

const COST_WIDGET_TYPES = ['kpi-spend', 'kpi-revenue', 'kpi-roas', 'chart-revenue', 'chart-spend']

export function CustomDashboard() {
  const { t } = useTranslation()
  const { showPriceMetrics } = usePriceMetrics()
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(1200)
  const [widgets, setWidgets] = useState<WidgetConfig[]>(() => {
    const saved = localStorage.getItem('stratum-dashboard-layout')
    return saved ? JSON.parse(saved) : defaultWidgets
  })
  const [isEditing, setIsEditing] = useState(false)
  const [showAddWidget, setShowAddWidget] = useState(false)

  // Measure container width on mount and resize
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth)
      }
    }

    updateWidth()
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])

  const handleLayoutChange = useCallback((layout: Layout[]) => {
    if (!isEditing) return
    setWidgets((prev) =>
      prev.map((widget) => {
        const layoutItem = layout.find((l) => l.i === widget.id)
        if (layoutItem) {
          return { ...widget, x: layoutItem.x, y: layoutItem.y, w: layoutItem.w, h: layoutItem.h }
        }
        return widget
      })
    )
  }, [isEditing])

  const handleSave = () => {
    localStorage.setItem('stratum-dashboard-layout', JSON.stringify(widgets))
    setIsEditing(false)
  }

  const handleReset = () => {
    setWidgets(defaultWidgets)
    localStorage.removeItem('stratum-dashboard-layout')
  }

  const handleAddWidget = (type: WidgetType) => {
    const widgetDef = availableWidgets.find((w) => w.type === type)
    if (!widgetDef) return

    const newWidget: WidgetConfig = {
      id: `${type}-${Date.now()}`,
      type,
      title: widgetDef.title,
      x: 0,
      y: Infinity,
      w: widgetDef.defaultSize.w,
      h: widgetDef.defaultSize.h,
      minW: 2,
      minH: 2,
    }
    setWidgets((prev) => [...prev, newWidget])
    setShowAddWidget(false)
  }

  const handleRemoveWidget = (id: string) => {
    setWidgets((prev) => prev.filter((w) => w.id !== id))
  }

  const renderWidget = (widget: WidgetConfig) => {
    const type = widget.type

    if (type.startsWith('kpi-')) {
      const kpiType = type.replace('kpi-', '') as 'spend' | 'revenue' | 'roas' | 'conversions' | 'ctr' | 'impressions'
      return <KPIWidget type={kpiType} />
    }

    if (type.startsWith('chart-')) {
      const chartType = type.replace('chart-', '') as 'revenue' | 'spend' | 'performance'
      return <ChartWidget type={chartType} />
    }

    switch (type) {
      case 'campaigns-top':
        return <CampaignsWidget />
      case 'platform-breakdown':
        return <PlatformBreakdownWidget />
      case 'alerts':
        return <AlertsWidget />
      case 'quick-actions':
        return <QuickActionsWidget />
      case 'simulator':
        return <SimulatorWidget />
      default:
        return <div className="p-4 text-muted-foreground">Unknown widget</div>
    }
  }

  const visibleWidgets = showPriceMetrics
    ? widgets
    : widgets.filter((w) => !COST_WIDGET_TYPES.includes(w.type))

  const layout: Layout[] = visibleWidgets.map((widget) => ({
    i: widget.id,
    x: widget.x,
    y: widget.y,
    w: widget.w,
    h: widget.h,
    minW: widget.minW || 2,
    minH: widget.minH || 2,
    maxW: widget.maxW,
    maxH: widget.maxH,
  }))

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <LayoutDashboard className="w-7 h-7 text-primary" />
            {t('dashboard.title')}
          </h1>
          <p className="text-muted-foreground">{t('dashboard.welcome')}</p>
        </div>

        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={() => setShowAddWidget(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Widget
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Save className="w-4 h-4" />
                Save Layout
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              <Settings className="w-4 h-4" />
              Customize
            </button>
          )}
        </div>
      </div>

      {isEditing && (
        <div className="p-3 rounded-lg bg-primary/10 border border-primary/20 text-sm">
          <strong>Edit Mode:</strong> Drag widgets to rearrange, resize from corners, or remove widgets.
        </div>
      )}

      {/* Grid Layout */}
      <div ref={containerRef} className="w-full">
        <GridLayout
          className="layout"
          layout={layout}
          cols={GRID_COLS}
          rowHeight={ROW_HEIGHT}
          width={containerWidth}
          isDraggable={isEditing}
          isResizable={isEditing}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".widget-drag-handle"
          compactType="vertical"
          preventCollision={false}
        >
        {visibleWidgets.map((widget) => (
          <div
            key={widget.id}
            className={cn(
              'rounded-xl border bg-card overflow-hidden',
              isEditing && 'ring-2 ring-primary/20'
            )}
          >
            {/* Widget Header */}
            <div className={cn(
              'flex items-center justify-between px-4 py-2 border-b bg-muted/30',
              isEditing && 'cursor-move widget-drag-handle'
            )}>
              <div className="flex items-center gap-2">
                {isEditing && <GripVertical className="w-4 h-4 text-muted-foreground" />}
                <span className="font-medium text-sm">{widget.title}</span>
              </div>
              {isEditing && (
                <button
                  onClick={() => handleRemoveWidget(widget.id)}
                  className="p-1 rounded hover:bg-destructive/10 text-destructive transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Widget Content */}
            <div className="h-[calc(100%-40px)]">
              {renderWidget(widget)}
            </div>
          </div>
        ))}
        </GridLayout>
      </div>

      {/* Add Widget Modal */}
      {showAddWidget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-xl p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Add Widget</h2>
              <button
                onClick={() => setShowAddWidget(false)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {availableWidgets.map((widget) => (
                <button
                  key={widget.type}
                  onClick={() => handleAddWidget(widget.type)}
                  className="p-4 rounded-lg border hover:border-primary hover:bg-primary/5 transition-colors text-left"
                >
                  <p className="font-medium">{widget.title}</p>
                  <p className="text-xs text-muted-foreground mt-1">{widget.description}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CustomDashboard
