'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

interface Campaign {
  campaign_id: string
  brief: string
  status: string
  channels: string
  product_focus: string
  duration_ms: number | null
  created_at: string | null
  result: {
    published?: Array<{ channel: string; url: string; status: string; error?: string }>
    execution_trace?: Array<{ step: number; agent: string; status: string; duration_ms: number }>
    exceptions?: Array<{ id: string; type: string; channel: string; severity: string; violation_detail: string; suggestion: string; status: string }>
    topic?: string
    summary?: Record<string, number | string>
    status?: string
    abort_reason?: string
  } | null
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; color: string; icon: string }> = {
    completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: '●' },
    completed_with_exceptions: { label: 'Has Exceptions', color: 'bg-amber-100 text-amber-700', icon: '▲' },
    failed: { label: 'Failed', color: 'bg-red-100 text-red-700', icon: '✗' },
    aborted: { label: 'Aborted', color: 'bg-orange-100 text-orange-700', icon: '⊘' },
    running: { label: 'Running', color: 'bg-blue-100 text-blue-700', icon: '◌' },
    waiting: { label: 'Awaiting Review', color: 'bg-purple-100 text-purple-700', icon: '◎' },
  }
  const c = config[status] || { label: status, color: 'bg-gray-100 text-gray-600', icon: '•' }
  return (
    <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium', c.color)}>
      {c.icon} {c.label}
    </span>
  )
}

function ChannelBadge({ channel }: { channel: string }) {
  const icons: Record<string, string> = {
    linkedin: '💼',
    email: '📧',
    blog: '📝',
  }
  if (channel === 'x_twitter') return null // Hide Twitter
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded text-xs font-medium text-gray-600">
      {icons[channel] || '📄'} {channel}
    </span>
  )
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const [expanded, setExpanded] = useState(false)

  // Convert raw destinations to clickable URLs
  const getDisplayUrl = (channel: string, url: string): { href: string; label: string } | null => {
    if (!url) return null
    
    // LinkedIn URN → clickable URL
    if (channel === 'linkedin' && url.includes('urn:li:share:')) {
      const urn = url.replace('URN: ', '').trim()
      return { href: `https://www.linkedin.com/feed/update/${urn}`, label: 'View on LinkedIn →' }
    }
    
    // Blog URL
    if (url.includes('blog.omprakash.me')) {
      return { href: url, label: url }
    }
    
    // Regular URLs
    if (url.startsWith('http')) {
      return { href: url, label: url.length > 50 ? url.slice(0, 50) + '...' : url }
    }
    
    // Email draft — not clickable
    if (channel === 'email' || url.includes('Draft ID') || url.includes('AQMk')) {
      return { href: '', label: '📧 Outlook Draft Created' }
    }
    
    // X/Twitter queue
    if (channel === 'x_twitter' || url.includes('Queue') || url.includes('Simulated')) {
      return { href: '', label: '📋 Queued for posting' }
    }
    
    return { href: '', label: url }
  }

  return (
    <motion.div variants={itemVariants}>
      <Card className={cn(
        'transition-all hover:shadow-md cursor-pointer border-0 shadow-sm',
        expanded && 'ring-2 ring-[#F5A623]/30'
      )}>
        <CardContent className="p-6" onClick={() => setExpanded(!expanded)}>
          {/* Header Row */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <StatusBadge status={campaign.result?.status || campaign.status} />
                {campaign.duration_ms && (
                  <span className="text-xs font-mono text-gray-400">
                    {(campaign.duration_ms / 1000).toFixed(0)}s
                  </span>
                )}
              </div>
              <h3 className="font-semibold text-[#1A1A1A] truncate">{campaign.brief}</h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-gray-400">{campaign.campaign_id}</span>
                <span className="text-xs text-gray-300">•</span>
                <span className="text-xs text-gray-400">
                  {campaign.created_at ? new Date(campaign.created_at).toLocaleString() : ''}
                </span>
              </div>
              {/* Channel badges */}
              <div className="flex gap-1.5 mt-3">
                {campaign.channels.split(',').map(ch => (
                  <ChannelBadge key={ch.trim()} channel={ch.trim()} />
                ))}
              </div>
            </div>
            <Icons.chevronDown className={cn(
              'h-5 w-5 text-gray-400 transition-transform shrink-0',
              expanded && 'rotate-180'
            )} />
          </div>

          {/* Expanded Details */}
          {expanded && campaign.result && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-6 pt-4 border-t border-gray-100 space-y-4"
            >
              {/* Abort Reason */}
              {(campaign.result.status === 'aborted' || campaign.result.abort_reason) && (
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center gap-2 mb-1">
                    <Icons.alertCircle className="h-4 w-4 text-orange-600" />
                    <span className="text-sm font-semibold text-orange-700">Campaign Aborted</span>
                  </div>
                  <p className="text-sm text-orange-600">{campaign.result.abort_reason || 'Topic relevance too low for the specified urgency level.'}</p>
                </div>
              )}
              {/* Published URLs */}
              {campaign.result.published && campaign.result.published.filter(p => p.channel !== 'x_twitter').length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Published Content</h4>
                  <div className="space-y-2">
                    {campaign.result.published.filter(p => p.channel !== 'x_twitter').map((pub, i) => {
                      const display = getDisplayUrl(pub.channel, pub.url)
                      const isFailed = pub.status === 'failed'
                      return (
                        <div key={i} className={cn(
                          "flex items-center justify-between p-3 rounded-lg",
                          isFailed ? "bg-red-50 border border-red-100" : "bg-emerald-50"
                        )}>
                          <div className="flex items-center gap-2">
                            <ChannelBadge channel={pub.channel} />
                            <span className={cn(
                              "text-xs font-medium",
                              isFailed ? "text-red-600" : "text-emerald-600"
                            )}>
                              {isFailed ? '❌ Failed' : pub.status}
                            </span>
                          </div>
                          {isFailed && pub.error ? (
                            <span className="text-xs text-red-500 max-w-[300px] truncate" title={pub.error}>
                              {pub.error}
                            </span>
                          ) : display && display.href ? (
                            <a
                              href={display.href}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-xs text-blue-600 hover:text-blue-800 underline font-medium"
                            >
                              {display.label}
                            </a>
                          ) : display ? (
                            <span className="text-xs text-gray-500">{display.label}</span>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Execution Trace */}
              {campaign.result.execution_trace && campaign.result.execution_trace.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Execution Trace</h4>
                  <div className="space-y-1">
                    {campaign.result.execution_trace.map((step, i) => (
                      <div key={i} className="flex items-center justify-between py-1.5 px-3 bg-gray-50 rounded">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-400 w-4">{step.step}</span>
                          <span className="text-xs font-medium text-gray-700">{step.agent}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={cn(
                            'text-xs',
                            step.status === 'success' || step.status === 'completed' ? 'text-emerald-600' : 'text-amber-600'
                          )}>
                            {step.status}
                          </span>
                          {step.duration_ms > 0 && (
                            <span className="text-xs font-mono text-gray-400">
                              {(step.duration_ms / 1000).toFixed(1)}s
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Exceptions / Problems */}
              {campaign.result.exceptions && campaign.result.exceptions.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-red-600 mb-2">⚠️ Exceptions & Issues</h4>
                  <div className="space-y-2">
                    {campaign.result.exceptions.map((exc: { id: string; type: string; channel: string; severity: string; violation_detail: string; suggestion: string; status: string }, i: number) => (
                      <div key={i} className="p-3 bg-red-50 rounded-lg border border-red-100">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-red-700">{exc.type}</span>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs text-gray-500 capitalize">{exc.channel}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded">{exc.severity}</span>
                        </div>
                        <p className="text-xs text-red-700">{exc.violation_detail}</p>
                        {exc.suggestion && (
                          <p className="text-xs text-gray-500 mt-1 italic">💡 {exc.suggestion}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Summary metrics - only show if meaningful data */}
              {campaign.result.summary && typeof campaign.result.summary === 'object' && 
               campaign.result.summary.variants_generated && (
                <div className="flex flex-wrap gap-3">
                  {campaign.result.summary.variants_generated && (
                    <div className="px-3 py-1.5 bg-gray-50 rounded-lg">
                      <span className="text-xs text-gray-500">Variants: </span>
                      <span className="text-xs font-semibold text-gray-700">{String(campaign.result.summary.variants_generated)}</span>
                    </div>
                  )}
                  {campaign.result.summary.approved && (
                    <div className="px-3 py-1.5 bg-emerald-50 rounded-lg">
                      <span className="text-xs text-gray-500">Approved: </span>
                      <span className="text-xs font-semibold text-emerald-700">{String(campaign.result.summary.approved)}</span>
                    </div>
                  )}
                  {campaign.result.summary.flagged && Number(campaign.result.summary.flagged) > 0 && (
                    <div className="px-3 py-1.5 bg-red-50 rounded-lg">
                      <span className="text-xs text-gray-500">Flagged: </span>
                      <span className="text-xs font-semibold text-red-700">{String(campaign.result.summary.flagged)}</span>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function loadCampaigns() {
      try {
        const data = await apiClient.get<{ campaigns: Campaign[] }>('/api/ai/campaigns')
        // Filter out non-campaign entries (help queries that accidentally triggered)
        const realCampaigns = (data.campaigns || []).filter(c => 
          !c.brief.toLowerCase().startsWith('what can') &&
          !c.brief.toLowerCase().startsWith('show me') &&
          !c.brief.toLowerCase().startsWith('help')
        )
        setCampaigns(realCampaigns)
      } catch (error) {
        console.error('Failed to load campaigns:', error)
        setCampaigns([])
      } finally {
        setIsLoading(false)
      }
    }
    loadCampaigns()
  }, [])

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-display-3 font-bold tracking-tight text-[#1A1A1A] lg:text-display-2">
            Campaigns
          </h1>
          <p className="mt-1 text-lg text-gray-500">
            All past campaign executions with published URLs and execution traces.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-lg">
          <Icons.layers className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-600">{campaigns.length} campaigns</span>
        </div>
      </motion.div>

      {/* Campaign List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Icons.loader className="h-8 w-8 animate-spin text-[#F5A623]" />
        </div>
      ) : campaigns.length === 0 ? (
        <motion.div variants={itemVariants}>
          <Card className="border-0 shadow-md">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F5A623]/10">
                <Icons.sparkles className="h-8 w-8 text-[#F5A623]" />
              </div>
              <h3 className="font-display text-lg font-semibold text-[#1A1A1A]">No campaigns yet</h3>
              <p className="mt-1 max-w-sm text-sm text-gray-400">
                Open the AI Manager (Cmd+J) and create your first campaign.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <CampaignCard key={campaign.campaign_id} campaign={campaign} />
          ))}
        </div>
      )}
    </motion.div>
  )
}
