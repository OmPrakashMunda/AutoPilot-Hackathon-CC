'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

interface Policy {
  id: number
  name: string
  category: string
  rule_text: string
  severity: string
  is_active: boolean
  created_at: string | null
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    block: 'bg-red-100 text-red-700 border-red-200',
    flag: 'bg-amber-100 text-amber-700 border-amber-200',
    warn: 'bg-blue-100 text-blue-700 border-blue-200',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium border', colors[severity] || colors.flag)}>
      {severity}
    </span>
  )
}

function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    banned_term: 'bg-red-50 text-red-600',
    brand_voice_rule: 'bg-purple-50 text-purple-600',
    posting_limit: 'bg-blue-50 text-blue-600',
    custom: 'bg-gray-50 text-gray-600',
  }
  const labels: Record<string, string> = {
    banned_term: 'Banned Term',
    brand_voice_rule: 'Brand Voice',
    posting_limit: 'Posting Limit',
    custom: 'Custom',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', colors[category] || colors.custom)}>
      {labels[category] || category}
    </span>
  )
}

export default function AIPoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [showAddForm, setShowAddForm] = useState(false)
  const [newPolicy, setNewPolicy] = useState({ name: '', category: 'banned_term', rule_text: '', severity: 'block' })
  const [isAdding, setIsAdding] = useState(false)

  const loadPolicies = useCallback(async () => {
    setIsLoading(true)
    try {
      const params = filter !== 'all' ? `?category=${filter}` : ''
      const data = await apiClient.get<{ policies: Policy[]; total: number }>(`/api/ai/policies${params}`)
      setPolicies(data.policies)
    } catch (error) {
      console.error('Failed to load policies:', error)
      setPolicies([])
    } finally {
      setIsLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadPolicies()
  }, [loadPolicies])

  const handleAddPolicy = async () => {
    if (!newPolicy.rule_text.trim()) return
    setIsAdding(true)
    try {
      await apiClient.post('/api/ai/policies', {
        name: newPolicy.name || newPolicy.category,
        category: newPolicy.category,
        rule_text: newPolicy.rule_text,
        severity: newPolicy.severity,
        is_active: true,
      })
      setNewPolicy({ name: '', category: 'banned_term', rule_text: '', severity: 'block' })
      setShowAddForm(false)
      await loadPolicies()
    } catch (error) {
      console.error('Failed to add policy:', error)
    } finally {
      setIsAdding(false)
    }
  }

  const handleDeletePolicy = async (id: number) => {
    try {
      await apiClient.delete(`/api/ai/policies/${id}`)
      await loadPolicies()
    } catch (error) {
      console.error('Failed to delete policy:', error)
    }
  }

  const handleSeedPolicies = async () => {
    try {
      await apiClient.post('/api/ai/seed')
      await loadPolicies()
    } catch (error) {
      console.error('Failed to seed policies:', error)
    }
  }

  // Stats
  const stats = {
    total: policies.length,
    banned_terms: policies.filter(p => p.category === 'banned_term').length,
    brand_voice: policies.filter(p => p.category === 'brand_voice_rule').length,
    posting_limits: policies.filter(p => p.category === 'posting_limit').length,
  }

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
            AI Policies
          </h1>
          <p className="mt-1 text-lg text-muted-foreground">
            Brand safety rules enforced by the AI workforce. Changes sync to Dropbox in real-time.
          </p>
        </div>
        <div className="flex gap-2">
          {policies.length === 0 && (
            <Button variant="outline" onClick={handleSeedPolicies}>
              <Icons.zap className="mr-2 h-4 w-4" />
              Load Defaults
            </Button>
          )}
          <Button variant="gradient" onClick={() => setShowAddForm(!showAddForm)}>
            <Icons.plus className="mr-2 h-4 w-4" />
            Add Policy
          </Button>
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { value: stats.total, label: 'Total Policies', icon: Icons.layers, color: 'text-brand-navy', bg: 'bg-brand-navy/10' },
          { value: stats.banned_terms, label: 'Banned Terms', icon: Icons.shield, color: 'text-red-600', bg: 'bg-red-100' },
          { value: stats.brand_voice, label: 'Brand Voice', icon: Icons.sparkles, color: 'text-purple-600', bg: 'bg-purple-100' },
          { value: stats.posting_limits, label: 'Posting Limits', icon: Icons.clock, color: 'text-blue-600', bg: 'bg-blue-100' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className={cn('p-2 rounded-lg', stat.bg)}>
                <stat.icon className={cn('h-5 w-5', stat.color)} />
              </div>
              <div>
                <p className={cn('text-2xl font-bold', stat.color)}>{stat.value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Add Policy Form */}
      {showAddForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <Card className="border-brand-cornflower/30 bg-brand-cornflower/5">
            <CardContent className="p-6">
              <h3 className="font-semibold text-brand-navy mb-4">Add New Policy</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newPolicy.category}
                    onChange={(e) => setNewPolicy({ ...newPolicy, category: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                  >
                    <option value="banned_term">Banned Term</option>
                    <option value="brand_voice_rule">Brand Voice Rule</option>
                    <option value="posting_limit">Posting Limit</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {newPolicy.category === 'banned_term' ? 'Term to Ban' : 'Rule Description'}
                  </label>
                  <input
                    type="text"
                    value={newPolicy.rule_text}
                    onChange={(e) => setNewPolicy({ ...newPolicy, rule_text: e.target.value })}
                    placeholder={newPolicy.category === 'banned_term' ? 'e.g., Nescafe' : 'e.g., Max 2 emojis per post'}
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
                  <select
                    value={newPolicy.severity}
                    onChange={(e) => setNewPolicy({ ...newPolicy, severity: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                  >
                    <option value="block">Block (hard stop)</option>
                    <option value="flag">Flag (needs review)</option>
                    <option value="warn">Warn (log only)</option>
                  </select>
                </div>
                <div className="flex items-end gap-2">
                  <Button
                    variant="gradient"
                    onClick={handleAddPolicy}
                    disabled={!newPolicy.rule_text.trim() || isAdding}
                    className="flex-1"
                  >
                    {isAdding ? <Icons.loader className="h-4 w-4 animate-spin" /> : <Icons.plus className="h-4 w-4 mr-1" />}
                    Add
                  </Button>
                  <Button variant="ghost" onClick={() => setShowAddForm(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
              {newPolicy.category === 'banned_term' && (
                <p className="mt-3 text-xs text-gray-500">
                  Adding a banned term syncs it to Dropbox. The Brand Safety Checker will catch it on the next campaign run.
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Filter Tabs */}
      <motion.div variants={itemVariants} className="flex gap-2 flex-wrap">
        {[
          { id: 'all', label: 'All' },
          { id: 'banned_term', label: 'Banned Terms' },
          { id: 'brand_voice_rule', label: 'Brand Voice' },
          { id: 'posting_limit', label: 'Posting Limits' },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              filter === f.id ? 'bg-brand-navy text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {f.label}
          </button>
        ))}
      </motion.div>

      {/* Policies List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
        </div>
      ) : policies.length === 0 ? (
        <motion.div variants={itemVariants}>
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-cornflower/20 to-brand-purple/20">
                <Icons.shield className="h-8 w-8 text-brand-cornflower" />
              </div>
              <h3 className="font-display text-lg font-semibold text-brand-navy">No policies yet</h3>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Click &quot;Load Defaults&quot; to populate NovaBrew&apos;s brand safety policies, or add your own.
              </p>
              <Button variant="gradient" className="mt-6" onClick={handleSeedPolicies}>
                <Icons.zap className="mr-2 h-4 w-4" />
                Load NovaBrew Defaults
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <motion.div variants={itemVariants} className="space-y-3">
          {policies.map((policy) => (
            <motion.div
              key={policy.id}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="group"
            >
              <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center gap-2 shrink-0">
                    <CategoryBadge category={policy.category} />
                    <SeverityBadge severity={policy.severity} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{policy.rule_text}</p>
                    {policy.name && policy.name !== policy.category && (
                      <p className="text-xs text-gray-400">{policy.name}</p>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 hover:bg-red-50 transition-opacity"
                  onClick={() => handleDeletePolicy(policy.id)}
                >
                  <Icons.trash className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
