/**
 * Stratum AI - Profit ROAS Page
 *
 * Manages products, COGS, margins, and profit calculations for True ROAS.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useProducts,
  useMarginRules,
  useProfitSummary,
  useTrueROAS,
  useCOGSUploads,
  useUploadCOGS,
} from '@/api/hooks'
import {
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  DocumentArrowUpIcon,
  PlusIcon,
  CalculatorIcon,
  ShoppingBagIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type TabType = 'overview' | 'products' | 'margins' | 'cogs'

export default function ProfitROAS() {
  useParams<{ tenantId: string }>()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [dateRange] = useState({
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  })

  const { data: products } = useProducts()
  const { data: marginRules } = useMarginRules()
  const { data: profitSummary } = useProfitSummary(dateRange)
  const { data: trueROAS } = useTrueROAS(dateRange)
  const { data: cogsUploads } = useCOGSUploads()
  const uploadCOGS = useUploadCOGS()

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview' },
    { id: 'products' as TabType, label: 'Products' },
    { id: 'margins' as TabType, label: 'Margin Rules' },
    { id: 'cogs' as TabType, label: 'COGS Upload' },
  ]

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadCOGS.mutate(file)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Profit ROAS</h1>
          <p className="text-muted-foreground">
            Track true profitability with COGS, margins, and profit-based ROAS
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
          <PlusIcon className="h-4 w-4" />
          Add Product
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* ROAS Comparison */}
          {trueROAS && (
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <h2 className="text-lg font-semibold mb-4">ROAS Comparison</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground mb-1">Standard ROAS</p>
                  <p className="text-4xl font-bold">{trueROAS.standardRoas.toFixed(2)}x</p>
                  <p className="text-xs text-muted-foreground mt-1">Revenue / Ad Spend</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-primary/10 border-2 border-primary">
                  <p className="text-sm text-muted-foreground mb-1">True ROAS</p>
                  <p className="text-4xl font-bold text-primary">{trueROAS.trueRoas.toFixed(2)}x</p>
                  <p className="text-xs text-muted-foreground mt-1">Gross Profit / Ad Spend</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                  <p className="text-sm text-muted-foreground mb-1">Profit ROAS</p>
                  <p className="text-4xl font-bold text-emerald-600">{trueROAS.profitRoas.toFixed(2)}x</p>
                  <p className="text-xs text-muted-foreground mt-1">Net Profit / Ad Spend</p>
                </div>
              </div>
            </div>
          )}

          {/* Profit Summary */}
          {profitSummary && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                    <CurrencyDollarIcon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Revenue</p>
                    <p className="text-2xl font-bold">${profitSummary.totalRevenue.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/20">
                    <ShoppingBagIcon className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total COGS</p>
                    <p className="text-2xl font-bold">${profitSummary.totalCogs.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                    <CalculatorIcon className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Gross Profit</p>
                    <p className="text-2xl font-bold">${profitSummary.grossProfit.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/20">
                    <ArrowTrendingUpIcon className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Net Profit</p>
                    <p className="text-2xl font-bold">${profitSummary.netProfit.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Margin Breakdown */}
          {profitSummary && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <h3 className="font-medium mb-4">Gross Margin</h3>
                <div className="flex items-center justify-center">
                  <div className="relative w-32 h-32">
                    <svg className="w-full h-full -rotate-90">
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        className="text-muted"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        strokeDasharray={`${(profitSummary.grossMarginPct / 100) * 351.86} 351.86`}
                        className="text-primary"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl font-bold">{profitSummary.grossMarginPct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <h3 className="font-medium mb-4">Net Margin</h3>
                <div className="flex items-center justify-center">
                  <div className="relative w-32 h-32">
                    <svg className="w-full h-full -rotate-90">
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        className="text-muted"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        strokeDasharray={`${(profitSummary.netMarginPct / 100) * 351.86} 351.86`}
                        className="text-emerald-500"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl font-bold">{profitSummary.netMarginPct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Products Tab */}
      {activeTab === 'products' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Product</th>
                <th className="px-4 py-3 text-left text-sm font-medium">SKU</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Category</th>
                <th className="px-4 py-3 text-right text-sm font-medium">COGS</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Margin %</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {products?.items.map((product) => (
                <tr key={product.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{product.name}</p>
                    {product.brand && (
                      <p className="text-sm text-muted-foreground">{product.brand}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm font-mono">{product.sku}</td>
                  <td className="px-4 py-3 text-sm">{product.category || '-'}</td>
                  <td className="px-4 py-3 text-right font-medium">
                    {product.currency} {product.defaultCogs.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {product.defaultMarginPct.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs',
                        product.status === 'active' && 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
                        product.status === 'inactive' && 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300',
                        product.status === 'discontinued' && 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                      )}
                    >
                      {product.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Margin Rules Tab */}
      {activeTab === 'margins' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted">
              <PlusIcon className="h-4 w-4" />
              Add Rule
            </button>
          </div>
          <div className="rounded-xl border bg-card shadow-card overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Rule Name</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Applies To</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Margin Type</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Value</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">Priority</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {marginRules?.map((rule) => (
                  <tr key={rule.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <p className="font-medium">{rule.name}</p>
                      {rule.description && (
                        <p className="text-sm text-muted-foreground truncate max-w-xs">
                          {rule.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm capitalize">{rule.appliesTo}</td>
                    <td className="px-4 py-3 text-sm capitalize">{rule.marginType}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      {rule.marginType === 'percentage' ? `${rule.marginValue}%` : `$${rule.marginValue}`}
                    </td>
                    <td className="px-4 py-3 text-center">{rule.priority}</td>
                    <td className="px-4 py-3 text-center">
                      {rule.isActive ? (
                        <span className="px-2 py-1 rounded-full text-xs bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300">
                          Inactive
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* COGS Upload Tab */}
      {activeTab === 'cogs' && (
        <div className="space-y-6">
          {/* Upload Area */}
          <div className="rounded-xl border border-dashed bg-card p-12 text-center">
            <DocumentArrowUpIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-medium mb-2">Upload COGS Data</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Upload a CSV file with SKU and COGS columns to update product costs
            </p>
            <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              Choose File
            </label>
          </div>

          {/* Upload History */}
          <div className="rounded-xl border bg-card shadow-card overflow-hidden">
            <div className="p-4 border-b">
              <h3 className="font-medium">Upload History</h3>
            </div>
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Filename</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Uploaded</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Rows</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Success</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Errors</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {cogsUploads?.map((upload) => (
                  <tr key={upload.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{upload.filename}</td>
                    <td className="px-4 py-3 text-sm">
                      {new Date(upload.uploadedAt).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">{upload.rowCount}</td>
                    <td className="px-4 py-3 text-right text-emerald-600">{upload.successCount}</td>
                    <td className="px-4 py-3 text-right text-red-600">{upload.errorCount}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs',
                          upload.status === 'completed' && 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
                          upload.status === 'processing' && 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
                          upload.status === 'failed' && 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300',
                          upload.status === 'pending' && 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300'
                        )}
                      >
                        {upload.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
