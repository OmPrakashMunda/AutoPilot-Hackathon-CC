'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

interface WorkbenchException {
  id: string
  campaign_id: string
  type: string
  channel: string
  severity: string
  content_preview: string
  violation_detail: string
  suggestion: string
  status: string
  resolved_by: string | null
  resolution_note: string | null
  created_at: string | null
  resolved_at: string | null
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    block: 'bg-red-100 text-red-700 border-red-200',
    flag: 'bg-amber-100 text-amber-700 border-amber-200',
    warn: 'bg-blue-100 text-blue-700 border-blue-200',
    critical: 'bg-red-200 text-red-800 border-red-300',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium border', colors[severity] || colors.flag)}>
      {severity}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending_review: 'bg-amber-100 text-amber-700',
    approved_override: 'bg-green-100 text-green-700',
    approved_edited: 'bg-emerald-100 text-emerald-700',
    rejected: 'bg-gray-100 text-gray-600',
  }
  const labels: Record<string, string> = {
    pending_review: 'Pending Review',
    approved_override: 'Approved (Override)',
    approved_edited: 'Approved (Edited)',
    rejected: 'Rejected',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', colors[status] || 'bg-gray-100 text-gray-600')}>
      {labels[status] || status}
    </span>
  )
}

function ChannelIcon({ channel }: { channel: string }) {
  const icons: Record<string, string> = {
    linkedin: '💼',
    x_twitter: '𝕏',
    email: '📧',
    blog: '📝',
    system: '⚙️',
  }
  return <span className="text-lg">{icons[channel] || '📄'}</span>
}

export default function WorkbenchPage() {
  const [exceptions, setExceptions] = useState<WorkbenchException[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'pending_review' | 'resolved'>('all')
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const [pendingCount, setPendingCount] = useState(0)

  const loadExceptions = useCallback(async () => {
    setIsLoading(true)
    try {
      const statusParam = filter === 'all' ? '' : `?status=${filter === 'resolved' ? 'approved_override' : filter}`
      const data = await apiClient.get<{ exceptions: WorkbenchException[]; total: number; pending: number }>(
        `/api/ai/workbench${statusParam}`
      )
      setExceptions(data.exceptions)
      setPendingCount(data.pending)
    } catch (error) {
      console.error('Failed to load exceptions:', error)
      setExceptions([])
    } finally {
      setIsLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadExceptions()
  }, [loadExceptions])

  const handleResolve = async (exceptionId: string, action: 'approve' | 'edit_approve' | 'reject') => {
    setResolvingId(exceptionId)
    try {
      await apiClient.post(`/api/ai/workbench/${exceptionId}/resolve`, {
        action,
        resolution_note: action === 'approve' ? 'CMO override — approved as-is' : action === 'reject' ? 'Content rejected — not suitable' : 'Content edited and approved',
      })
      await loadExceptions()
    } catch (error) {
      console.error('Failed to resolve exception:', error)
    } finally {
      setResolvingId(null)
    }
  }

  const pendingExceptions = exceptions.filter(e => e.status === 'pending_review')
  const resolvedExceptions = exceptions.filter(e => e.status !== 'pending_review')

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-display-3 font-bold tracking-tight text-brand-navy lg:text-display-2">
            AI Workbench
          </h1>
          <p className="mt-1 text-lg text-muted-foreground">
            Review and resolve exceptions flagged by the AI workforce.
          </p>
        </div>
        {pendingCount > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg">
            <Icons.alertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-700">{pendingCount} pending review</span>
          </div>
        )}
      </motion.div>

      {/* Filter Tabs */}
      <motion.div variants={itemVariants} className="flex gap-2">
        {(['all', 'pending_review', 'resolved'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              filter === f ? 'bg-brand-navy text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {f === 'all' ? 'All' : f === 'pending_review' ? 'Pending' : 'Resolved'}
          </button>
        ))}
      </motion.div>

      {/* Exceptions List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
        </div>
      ) : exceptions.length === 0 ? (
        <motion.div variants={itemVariants}>
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-100 to-emerald-200">
                <Icons.check className="h-8 w-8 text-emerald-600" />
              </div>
              <h3 className="font-display text-lg font-semibold text-brand-navy">All clear!</h3>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                No exceptions to review. Your AI workforce is running smoothly.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <motion.div variants={itemVariants} className="space-y-4">
          {exceptions.map((exc) => (
            <motion.div
              key={exc.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <Card className={cn(
                'transition-all hover:shadow-md',
                exc.status === 'pending_review' && 'border-amber-200 bg-amber-50/30'
              )}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    {/* Left: Exception details */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-3">
                        <ChannelIcon channel={exc.channel} />
                        <span className="font-semibold text-brand-navy capitalize">{exc.channel.replace('_', '/')}</span>
                        <SeverityBadge severity={exc.severity} />
                        <StatusBadge status={exc.status} />
                      </div>

                      <div>
                        <p className="text-sm font-medium text-gray-700">{exc.violation_detail}</p>
                        {exc.content_preview && (
                          <p className="mt-1 text-sm text-gray-500 italic line-clamp-2">
                            &ldquo;{exc.content_preview}&rdquo;
                          </p>
                        )}
                      </div>

                      {exc.suggestion && (
                        <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                          <Icons.sparkles className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                          <p className="text-sm text-blue-700">{exc.suggestion}</p>
                        </div>
                      )}

                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        <span>Campaign: {exc.campaign_id}</span>
                        {exc.created_at && <span>Created: {new Date(exc.created_at).toLocaleString()}</span>}
                        {exc.resolved_at && <span>Resolved: {new Date(exc.resolved_at).toLocaleString()}</span>}
                      </div>
                    </div>

                    {/* Right: Actions */}
                    {exc.status === 'pending_review' && (
                      <div className="flex flex-col gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="default"
                          className="bg-emerald-600 hover:bg-emerald-700"
                          disabled={resolvingId === exc.id}
                          onClick={() => handleResolve(exc.id, 'approve')}
                        >
                          {resolvingId === exc.id ? <Icons.loader className="h-3 w-3 animate-spin" /> : <Icons.check className="h-3 w-3 mr-1" />}
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={resolvingId === exc.id}
                          onClick={() => handleResolve(exc.id, 'edit_approve')}
                        >
                          <Icons.edit className="h-3 w-3 mr-1" />
                          Edit & Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          disabled={resolvingId === exc.id}
                          onClick={() => handleResolve(exc.id, 'reject')}
                        >
                          <Icons.close className="h-3 w-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
