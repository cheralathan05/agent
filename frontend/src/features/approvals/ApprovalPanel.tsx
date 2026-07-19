import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPendingApprovals, approveApproval, denyApproval } from '../../services/approvals'
import { Shield, ShieldCheck, ShieldX, Loader2, AlertTriangle } from 'lucide-react'
import { useState } from 'react'

function RiskBadge({ risk }: { risk: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-500/10 text-red-400 border-red-500/30',
    medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/10 text-green-400 border-green-500/30',
  }
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${colors[risk] || colors.low}`}>
      {risk}
    </span>
  )
}

export function ApprovalPanel() {
  const queryClient = useQueryClient()
  const [permissionType, setPermissionType] = useState('once')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['pending-approvals'],
    queryFn: fetchPendingApprovals,
    refetchInterval: 3000,
  })

  const approveMutation = useMutation({
    mutationFn: (params: { id: string; type: string }) =>
      approveApproval(params.id, params.type),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-approvals'] }),
  })

  const denyMutation = useMutation({
    mutationFn: (id: string) => denyApproval(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-approvals'] }),
  })

  const approvals = data?.approvals || []

  // If loading and no data yet, show nothing (it will appear when approvals come in)
  if (!data && isLoading) return null
  if (approvals.length === 0) return null

  return (
    <div className="fixed bottom-12 right-4 z-50 w-96 max-h-[70vh] flex flex-col glass-panel border-accent-500/30 shadow-2xl shadow-accent-500/10">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-yellow-400" />
          <span className="text-xs font-semibold">Pending Approvals ({approvals.length})</span>
        </div>
        <button
          onClick={() => refetch()}
          className="text-[10px] text-gray-500 hover:text-white transition-colors"
        >
          refresh
        </button>
      </div>

      {/* Approval list */}
      <div className="overflow-y-auto flex-1 p-2 space-y-2">
        {approvals.map((a) => (
          <div
            key={a.id}
            className="bg-surface-300/80 border border-white/5 rounded-lg p-3 space-y-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">{a.tool_name}</span>
                <RiskBadge risk={a.risk} />
              </div>
              <span className="text-[9px] text-gray-500 font-mono">
                {a.id.slice(0, 8)}
              </span>
            </div>

            <p className="text-[11px] text-gray-400">{a.reason || a.action}</p>

            {/* Permission type selector */}
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-gray-500">Allow:</span>
              {['once', 'session', 'always'].map((pt) => (
                <button
                  key={pt}
                  onClick={() => setPermissionType(pt)}
                  className={`text-[9px] px-2 py-0.5 rounded-full border transition-all ${
                    permissionType === pt
                      ? 'bg-accent-500/20 border-accent-400 text-accent-300'
                      : 'border-white/10 text-gray-500 hover:text-white'
                  }`}
                >
                  {pt}
                </button>
              ))}
            </div>

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => approveMutation.mutate({ id: a.id, type: permissionType })}
                disabled={approveMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded text-[11px] transition-all disabled:opacity-50"
              >
                {approveMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <ShieldCheck className="w-3 h-3" />
                )}
                Approve
              </button>
              <button
                onClick={() => denyMutation.mutate(a.id)}
                disabled={denyMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-[11px] transition-all disabled:opacity-50"
              >
                {denyMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <ShieldX className="w-3 h-3" />
                )}
                Deny
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
