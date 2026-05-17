'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { useAI } from '@/context/AIContext'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

interface DashboardData {
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
}

function StatCard({ title, value, subtitle, icon: Icon, color, bgColor }: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
}) {
  return (
    <motion.div variants={itemVariants}>
      <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-0 shadow-md">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">{title}</p>
              <p className={cn('text-3xl font-bold mt-1', color)}>{value}</p>
              {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
            </div>
            <div className={cn('p-3 rounded-2xl', bgColor)}>
              <Icon className={cn('h-6 w-6', color)} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <Icons.check className="h-3.5 w-3.5 text-emerald-600" />
    case 'completed_with_exceptions':
      return <Icons.alertTriangle className="h-3.5 w-3.5 text-amber-600" />
    case 'failed':
      return <Icons.alertCircle className="h-3.5 w-3.5 text-red-600" />
    default:
      return <Icons.loader className="h-3.5 w-3.5 text-blue-600 animate-spin" />
  }
}

export default function HomePage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const { openManager } = useAI()

  const loadDashboard = async () => {
    try {
      const result = await apiClient.get<DashboardData>('/api/ai/insights')
      setData(result)
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await apiClient.get('/api/ai/campaigns/sync')
      await loadDashboard()
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <motion.div
      className="space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Hero Section */}
      <motion.div variants={itemVariants} className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#1A1A1A] via-[#2D2D2D] to-[#1A1A1A] p-8 lg:p-12">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#F5A623]/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-[#F5A623]/5 rounded-full blur-2xl" />
        
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold text-white tracking-tight">
              NovaBrew Command Center
            </h1>
            <p className="mt-2 text-lg text-gray-300 max-w-xl">
              Your AI marketing workforce. Orchestrate campaigns, enforce brand safety, and publish across channels — all from one place.
            </p>
            <div className="flex items-center gap-3 mt-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 rounded-full">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-xs font-medium text-emerald-300">6 Agents Online</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-[#F5A623]/20 rounded-full">
                <Icons.zap className="h-3 w-3 text-[#F5A623]" />
                <span className="text-xs font-medium text-[#F5A623]">Fuel Your Flow</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={handleSync}
              disabled={isSyncing}
              className="border-[#F5A623]/50 text-[#F5A623] hover:bg-[#F5A623]/10 hover:text-[#F5A623]"
            >
              {isSyncing ? <Icons.loader className="mr-2 h-4 w-4 animate-spin" /> : <Icons.refresh className="mr-2 h-4 w-4" />}
              Sync
            </Button>
            <Button
              onClick={openManager}
              className="bg-[#F5A623] hover:bg-[#E09000] text-black font-semibold px-6 py-3 rounded-xl shadow-lg shadow-[#F5A623]/25 transition-all hover:shadow-xl hover:shadow-[#F5A623]/30 hover:-translate-y-0.5"
            >
              <Icons.sparkles className="mr-2 h-5 w-5" />
              Launch Campaign
            </Button>
          </div>
        </div>
      </motion.div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Campaigns Run"
          value={data?.campaigns.total || 0}
          subtitle={`${data?.campaigns.success_rate || 0}% success`}
          icon={Icons.layers}
          color="text-[#1A1A1A]"
          bgColor="bg-[#1A1A1A]/10"
        />
        <StatCard
          title="Avg Duration"
          value={data?.campaigns.avg_duration_ms ? `${(data.campaigns.avg_duration_ms / 1000).toFixed(0)}s` : '--'}
          subtitle="per campaign"
          icon={Icons.clock}
          color="text-[#F5A623]"
          bgColor="bg-[#F5A623]/10"
        />
        <StatCard
          title="Exceptions Caught"
          value={data?.exceptions.total || 0}
          subtitle={`${data?.exceptions.pending || 0} pending review`}
          icon={Icons.shield}
          color="text-red-600"
          bgColor="bg-red-100"
        />
        <StatCard
          title="Policies Active"
          value="20"
          subtitle="brand safety rules"
          icon={Icons.brain}
          color="text-purple-600"
          bgColor="bg-purple-100"
        />
      </div>

      {/* Agent Status + Recent Campaigns */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Agent Workforce */}
        <motion.div variants={itemVariants}>
          <Card className="border-0 shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-[#1A1A1A]">
                <Icons.zap className="h-5 w-5 text-[#F5A623]" />
                AI Workforce Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: 'Campaign Orchestrator', role: 'Manager', icon: Icons.layers },
                  { name: 'Trend Analyser', role: 'Research', icon: Icons.activity },
                  { name: 'Content Adapter', role: 'Writing', icon: Icons.fileText },
                  { name: 'Brand Safety Checker', role: 'Compliance', icon: Icons.shield },
                  { name: 'Social Scheduler', role: 'Publishing', icon: Icons.share },
                  { name: 'Knowledge Base', role: 'Intelligence', icon: Icons.brain },
                ].map((agent) => (
                  <div key={agent.name} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 bg-emerald-50 rounded-lg">
                        <agent.icon className="h-3.5 w-3.5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-800">{agent.name}</p>
                        <p className="text-xs text-gray-400">{agent.role}</p>
                      </div>
                    </div>
                    <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                      online
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Campaigns */}
        <motion.div variants={itemVariants}>
          <Card className="border-0 shadow-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-[#1A1A1A]">
                <Icons.clock className="h-5 w-5 text-[#F5A623]" />
                Recent Campaigns
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => window.location.href = '/campaigns'} className="text-xs text-gray-500">
                View All
                <Icons.arrowRight className="ml-1 h-3 w-3" />
              </Button>
            </CardHeader>
            <CardContent>
              {!data?.recent_campaigns?.length ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Icons.sparkles className="h-10 w-10 text-gray-200 mb-3" />
                  <p className="text-sm text-gray-400">No campaigns yet</p>
                  <p className="text-xs text-gray-300 mt-1">Use the AI Manager to launch your first campaign</p>
                  <Button variant="outline" size="sm" className="mt-4" onClick={openManager}>
                    Launch Campaign
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {data.recent_campaigns.filter(c => !c.brief.toLowerCase().startsWith('what can')).slice(0, 5).map((campaign) => (
                    <div key={campaign.campaign_id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <StatusIcon status={campaign.status} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">{campaign.brief}</p>
                          <p className="text-xs text-gray-400">{campaign.campaign_id}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        <span className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-medium',
                          campaign.status === 'completed' ? 'text-emerald-600 bg-emerald-50' :
                          campaign.status === 'failed' ? 'text-red-600 bg-red-50' :
                          'text-amber-600 bg-amber-50'
                        )}>
                          {campaign.status.replace(/_/g, ' ')}
                        </span>
                        {campaign.duration_ms && (
                          <span className="text-xs font-mono text-gray-400">
                            {(campaign.duration_ms / 1000).toFixed(0)}s
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <Card className="border-0 shadow-md bg-gradient-to-r from-gray-50 to-white">
          <CardContent className="p-6">
            <h3 className="font-semibold text-[#1A1A1A] mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Button
                variant="outline"
                className="h-auto py-4 flex-col gap-2 hover:bg-[#F5A623]/5 hover:border-[#F5A623]/30"
                onClick={openManager}
              >
                <Icons.sparkles className="h-5 w-5 text-[#F5A623]" />
                <span className="text-xs">New Campaign</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto py-4 flex-col gap-2 hover:bg-red-50 hover:border-red-200"
                onClick={() => window.location.href = '/workbench'}
              >
                <Icons.alertTriangle className="h-5 w-5 text-red-500" />
                <span className="text-xs">Review Exceptions</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto py-4 flex-col gap-2 hover:bg-purple-50 hover:border-purple-200"
                onClick={() => window.location.href = '/ai/policies'}
              >
                <Icons.shield className="h-5 w-5 text-purple-500" />
                <span className="text-xs">Manage Policies</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto py-4 flex-col gap-2 hover:bg-blue-50 hover:border-blue-200"
                onClick={() => window.location.href = '/ai/insights'}
              >
                <Icons.activity className="h-5 w-5 text-blue-500" />
                <span className="text-xs">View Insights</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
