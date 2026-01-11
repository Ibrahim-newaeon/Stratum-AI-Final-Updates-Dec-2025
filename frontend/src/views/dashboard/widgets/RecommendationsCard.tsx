/**
 * RecommendationsCard - AI recommendations with approve/reject actions
 */

import { useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Eye,
  Loader2,
  Pause,
  Sparkles,
  TrendingUp,
  Wrench,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RecommendationItem, RecommendationType } from '@/api/dashboard'

interface RecommendationsCardProps {
  recommendations: RecommendationItem[]
  loading?: boolean
  onApprove: (id: string) => Promise<void>
  onReject: (id: string) => Promise<void>
  onViewAll?: () => void
}

export function RecommendationsCard({
  recommendations,
  loading = false,
  onApprove,
  onReject,
  onViewAll,
}: RecommendationsCardProps) {
  const [processingId, setProcessingId] = useState<string | null>(null)

  const getTypeConfig = (type: RecommendationType) => {
    switch (type) {
      case 'scale':
        return {
          icon: TrendingUp,
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          label: 'Scale',
        }
      case 'watch':
        return {
          icon: Eye,
          color: 'text-blue-500',
          bgColor: 'bg-blue-500/10',
          label: 'Watch',
        }
      case 'fix':
        return {
          icon: Wrench,
          color: 'text-orange-500',
          bgColor: 'bg-orange-500/10',
          label: 'Fix',
        }
      case 'pause':
        return {
          icon: Pause,
          color: 'text-red-500',
          bgColor: 'bg-red-500/10',
          label: 'Pause',
        }
      default:
        return {
          icon: AlertTriangle,
          color: 'text-muted-foreground',
          bgColor: 'bg-muted',
          label: type,
        }
    }
  }

  const handleApprove = async (id: string) => {
    setProcessingId(id)
    try {
      await onApprove(id)
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (id: string) => {
    setProcessingId(id)
    try {
      await onReject(id)
    } finally {
      setProcessingId(null)
    }
  }

  if (loading) {
    return (
      <div className="bg-card border rounded-lg p-5 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const pendingRecommendations = recommendations.filter((r) => r.status === 'pending')

  return (
    <div className="bg-card border rounded-lg">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">AI Recommendations</h3>
          {pendingRecommendations.length > 0 && (
            <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full font-medium">
              {pendingRecommendations.length}
            </span>
          )}
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            View all
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

      <div className="divide-y">
        {pendingRecommendations.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No pending recommendations</p>
          </div>
        ) : (
          pendingRecommendations.slice(0, 5).map((rec) => {
            const typeConfig = getTypeConfig(rec.type)
            const TypeIcon = typeConfig.icon
            const isProcessing = processingId === rec.id

            return (
              <div key={rec.id} className="p-4">
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                      typeConfig.bgColor
                    )}
                  >
                    <TypeIcon className={cn('w-4 h-4', typeConfig.color)} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          'text-xs px-1.5 py-0.5 rounded font-medium',
                          typeConfig.bgColor,
                          typeConfig.color
                        )}
                      >
                        {typeConfig.label}
                      </span>
                      <span className="text-xs text-muted-foreground">{rec.platform}</span>
                    </div>

                    <h4 className="text-sm font-medium mb-1 line-clamp-1">{rec.title}</h4>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {rec.description}
                    </p>

                    {rec.impact_estimate && (
                      <div className="mt-2 text-xs text-green-500 font-medium">
                        {rec.impact_estimate}
                      </div>
                    )}

                    {/* Confidence bar */}
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all',
                            rec.confidence >= 80
                              ? 'bg-green-500'
                              : rec.confidence >= 60
                                ? 'bg-yellow-500'
                                : 'bg-orange-500'
                          )}
                          style={{ width: `${rec.confidence}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">{rec.confidence}%</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {isProcessing ? (
                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                    ) : (
                      <>
                        <button
                          onClick={() => handleReject(rec.id)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
                          title="Reject"
                        >
                          <X className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleApprove(rec.id)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-green-500 hover:bg-green-500/10 transition-colors"
                          title="Approve"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {pendingRecommendations.length > 5 && (
        <div className="p-3 border-t text-center">
          <button
            onClick={onViewAll}
            className="text-sm text-primary hover:underline"
          >
            View {pendingRecommendations.length - 5} more recommendations
          </button>
        </div>
      )}
    </div>
  )
}
