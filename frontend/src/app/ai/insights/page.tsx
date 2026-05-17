'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

interface InsightsData {
  campaigns: {
    total: number
    completed: number
    failed: number
    success_rate: number
    avg_duration_ms: number
  }
  exceptions: {
    total: number
    pending: number
    resolved: number
    by_type: Array<{ type: string; count: number }>
  }
  agent_performance: Array<{
    agent: string
    avg_duration_ms: number
    total_calls: number
  }>
  recent_campaigns: Array<{
    campaign_id: string
    brief: string
    status: string
    duration_ms: number | null
    created_at: string | null
  }>
  publishing?: {
    by_channel: Array<{ channel: string; published: number; failed: number; total: number }>
    recent_failures: Array<{ channel: string; error: string; campaign_id: string }>
  }
}

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <motion.div variants={itemVariants}>
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">{title}</p>
              <p className={cn('text-3xl font-bold mt-1', color)}>{value}</p>
              {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
            </div>
            <div className={cn('p-3 rounded-xl', color.replace('text-', 'bg-').replace('600', '100').replace('700', '100'))}>
              <Icon className={cn('h-6 w-6', color)} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function AgentPerformanceRow({ agent, avg_duration_ms, total_calls }: {
  agent: string
  avg_duration_ms: number
  total_calls: number
}) {
  const maxDuration = 15000 // 15s max for bar width
  const barWidth = Math.min((avg_duration_ms / maxDuration) * 100, 100)

  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{agent}</p>
        <p className="text-xs text-gray-500">{total_calls} calls</p>
      </div>
      <div className="flex-1">
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-cornflower to-brand-purple rounded-full transition-all"
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
      <div className="text-right shrink-0 w-20">
        <p className="text-sm font-mono font-medium text-gray-700">
          {(avg_duration_ms / 1000).toFixed(1)}s
        </p>
      </div>
    </div>
  )
}

function CampaignRow({ campaign }: { campaign: InsightsData['recent_campaigns'][0] }) {
  const statusColors: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700',
    completed_with_exceptions: 'bg-amber-100 text-amber-700',
    failed: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
  }

  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{campaign.brief}</p>
        <p className="text-xs text-gray-500">{campaign.campaign_id}</p>
      </div>
      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium shrink-0', statusColors[campaign.status] || 'bg-gray-100 text-gray-600')}>
        {campaign.status.replace(/_/g, ' ')}
      </span>
      {campaign.duration_ms && (
        <span className="text-xs font-mono text-gray-500 shrink-0">
          {(campaign.duration_ms / 1000).toFixed(1)}s
        </span>
      )}
    </div>
  )
}

export default function AIInsightsPage() {
  const [data, setData] = useState<InsightsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function loadInsights() {
      try {
        const result = await apiClient.get<InsightsData>('/api/ai/insights')
        setData(result)
      } catch (error) {
        console.error('Failed to load insights:', error)
      } finally {
        setIsLoading(false)
      }
    }
    loadInsights()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Icons.activity className="h-12 w-12 text-gray-300 mb-4" />
        <h3 className="text-lg font-semibold text-gray-600">No data yet</h3>
        <p className="text-sm text-gray-400 mt-1">Run your first campaign to see insights here.</p>
      </div>
    )
  }

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-display-3 font-bold tracking-tight text-brand-navy lg:text-display-2">
          AI Insights
        </h1>
        <p className="mt-1 text-lg text-muted-foreground">
          Live execution data, agent performance, and campaign metrics.
        </p>
      </motion.div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Campaigns"
          value={data.campaigns.total}
          subtitle={`${data.campaigns.success_rate}% success rate`}
          icon={Icons.layers}
          color="text-brand-navy"
        />
        <StatCard
          title="Avg Duration"
          value={`${(data.campaigns.avg_duration_ms / 1000).toFixed(1)}s`}
          subtitle="per campaign"
          icon={Icons.clock}
          color="text-blue-600"
        />
        <StatCard
          title="Exceptions Caught"
          value={data.exceptions.total}
          subtitle={`${data.exceptions.pending} pending`}
          icon={Icons.alertTriangle}
          color="text-amber-600"
        />
        <StatCard
          title="Resolved"
          value={data.exceptions.resolved}
          subtitle="human-in-the-loop"
          icon={Icons.check}
          color="text-emerald-600"
        />
      </div>

      {/* Agent Performance + Recent Campaigns */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Agent Performance */}
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icons.activity className="h-5 w-5 text-brand-cornflower" />
                Agent Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.agent_performance.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">No agent data yet</p>
              ) : (
                <div>
                  {data.agent_performance.map((agent) => (
                    <AgentPerformanceRow key={agent.agent} {...agent} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Campaigns */}
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icons.clock className="h-5 w-5 text-brand-cornflower" />
                Recent Campaigns
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.recent_campaigns.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">No campaigns yet</p>
              ) : (
                <div>
                  {data.recent_campaigns.map((campaign) => (
                    <CampaignRow key={campaign.campaign_id} campaign={campaign} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Exception Breakdown */}
      {data.exceptions.by_type.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icons.shield className="h-5 w-5 text-amber-500" />
                Exception Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {data.exceptions.by_type.map((item) => (
                  <div key={item.type} className="text-center p-4 bg-gray-50 rounded-xl">
                    <p className="text-2xl font-bold text-brand-navy">{item.count}</p>
                    <p className="text-xs text-gray-500 mt-1 capitalize">{item.type.replace(/_/g, ' ')}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Publishing Stats & Failures */}
      {data.publishing && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icons.zap className="h-5 w-5 text-emerald-500" />
                Publishing Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Channel Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {data.publishing.by_channel.map((ch: { channel: string; published: number; failed: number; total: number }) => (
                  <div key={ch.channel} className="p-3 bg-gray-50 rounded-xl text-center">
                    <p className="text-xs text-gray-500 capitalize mb-1">{ch.channel.replace('_', '/')}</p>
                    <p className="text-lg font-bold text-emerald-600">{ch.published}</p>
                    <p className="text-[10px] text-gray-400">{ch.failed > 0 ? `${ch.failed} failed` : 'all success'}</p>
                  </div>
                ))}
              </div>

              {/* Recent Failures */}
              {data.publishing.recent_failures && data.publishing.recent_failures.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-red-600 mb-2">Recent Failures</h4>
                  <div className="space-y-2">
                    {data.publishing.recent_failures.map((f: { channel: string; error: string; campaign_id: string }, i: number) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-red-700 capitalize">{f.channel}</span>
                          <span className="text-xs text-gray-400">({f.campaign_id})</span>
                        </div>
                        <span className="text-xs text-red-500 max-w-[250px] truncate">{f.error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
