import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRunDiff, updateFileStatus } from '../../services/diff'
import { DiffViewer } from './DiffViewer'
import { Terminal, Download, Check, X, GitCompare } from 'lucide-react'

interface DiffReviewPanelProps {
  runId: string
  onClose: () => void
}

export function DiffReviewPanel({ runId, onClose }: DiffReviewPanelProps) {
  const queryClient = useQueryClient()
  const [expandedFile, setExpandedFile] = useState<string | null>(null)
  const [isAcceptingAll, setIsAcceptingAll] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['run-diff', runId],
    queryFn: () => fetchRunDiff(runId),
    refetchInterval: 5000,
  })

  const acceptMutation = useMutation({
    mutationFn: (changeId: string) => updateFileStatus(runId, changeId, 'accepted'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['run-diff', runId] }),
  })

  const rejectMutation = useMutation({
    mutationFn: (changeId: string) => updateFileStatus(runId, changeId, 'rejected'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['run-diff', runId] }),
  })

  const handleAcceptAll = useCallback(async () => {
    if (!data) return
    setIsAcceptingAll(true)
    const pending = data.files.filter((f) => f.id && f.status === 'pending')
    await Promise.allSettled(pending.map((f) => acceptMutation.mutateAsync(f.id!)))
    setIsAcceptingAll(false)
  }, [data, acceptMutation])

  if (!data && isLoading) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
        Loading changes...
      </div>
    )
  }

  const pendingFiles = data?.files.filter((f) => f.status === 'pending') || []
  const acceptedCount = data?.files.filter((f) => f.status === 'accepted').length || 0
  const rejectedCount = data?.files.filter((f) => f.status === 'rejected').length || 0

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-11 border-b border-white/5 flex items-center px-4 gap-3 shrink-0">
        <Terminal className="w-4 h-4 text-accent-300" />
        <span className="text-sm font-medium">Review Changes</span>
        <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded">
          {data?.total_changes || 0} files · +{data?.total_added || 0}/-{data?.total_removed || 0}
        </span>
        {acceptedCount > 0 && (
          <span className="text-[10px] text-green-400">
            {acceptedCount} accepted
          </span>
        )}
        {rejectedCount > 0 && (
          <span className="text-[10px] text-red-400">
            {rejectedCount} rejected
          </span>
        )}
        <button onClick={onClose} className="btn-ghost ml-auto text-[11px]">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!data && (
          <div className="text-center py-16 text-gray-500">
            <GitCompare className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium text-gray-400">No changes to review</p>
            <p className="text-xs mt-1">Run an agent task first to see file changes here.</p>
            <button
              onClick={onClose}
              className="mt-4 text-[11px] text-accent-300 hover:text-white transition-colors"
            >
              Back to Chat →
            </button>
          </div>
        )}

        {/* Summary card */}
        {data && (
          <div className="glass-panel p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-gray-200">Changes Summary</h2>
              <button
                onClick={handleAcceptAll}
                disabled={pendingFiles.length === 0 || isAcceptingAll}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded text-[11px] transition-all disabled:opacity-50"
              >
                <Download className={`w-3 h-3 ${isAcceptingAll ? 'animate-pulse' : ''}`} />
                {isAcceptingAll ? 'Accepting...' : `Accept All (${pendingFiles.length})`}
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-surface-300/50 rounded-lg p-2">
                <div className="text-lg font-bold text-gray-200">{data?.total_changes || 0}</div>
                <div className="text-[10px] text-gray-500">Files Changed</div>
              </div>
              <div className="bg-surface-300/50 rounded-lg p-2">
                <div className="text-lg font-bold text-green-400">+{data?.total_added || 0}</div>
                <div className="text-[10px] text-gray-500">Additions</div>
              </div>
              <div className="bg-surface-300/50 rounded-lg p-2">
                <div className="text-lg font-bold text-red-400">-{data?.total_removed || 0}</div>
                <div className="text-[10px] text-gray-500">Deletions</div>
              </div>
            </div>
          </div>
        )}

        {/* File list */}
        {data?.files.length === 0 && data && (
          <div className="text-center py-12 text-gray-500">
            <Terminal className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No file changes for this run</p>
          </div>
        )}

        {data?.files.map((file) => {
          const isPending = file.status === 'pending'
          return (
            <div key={file.id || file.file_path} className="space-y-1">
              {/* File header with actions */}
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setExpandedFile(expandedFile === file.file_path ? null : file.file_path)}
                  className="flex items-center gap-2 text-xs text-gray-400 hover:text-white transition-colors"
                >
                  <span className="text-[10px]">{expandedFile === file.file_path ? '⏷' : '⏵'}</span>
                  <span className="font-mono">{file.file_path}</span>
                  {!isPending && (
                    <span className={`text-[9px] ${file.status === 'accepted' ? 'text-green-400' : 'text-red-400'}`}>
                      {file.status === 'accepted' ? '✓ Accepted' : '✗ Rejected'}
                    </span>
                  )}
                </button>
                {isPending && file.id && (
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => acceptMutation.mutate(file.id!)}
                      disabled={acceptMutation.isPending}
                      className="flex items-center gap-1 px-2 py-1 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded text-[10px] transition-all disabled:opacity-50"
                    >
                      <Check className="w-3 h-3" /> Accept
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(file.id!)}
                      disabled={rejectMutation.isPending}
                      className="flex items-center gap-1 px-2 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-[10px] transition-all disabled:opacity-50"
                    >
                      <X className="w-3 h-3" /> Reject
                    </button>
                  </div>
                )}
              </div>

              {/* Diff viewer */}
              {expandedFile === file.file_path && (
                <DiffViewer file={file} />
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom bar */}
      {data && pendingFiles.length > 0 && (
        <div className="h-10 border-t border-white/5 flex items-center justify-center px-4 shrink-0">
          <p className="text-[10px] text-gray-500">
            {pendingFiles.length} file{pendingFiles.length > 1 ? 's' : ''} pending review
          </p>
        </div>
      )}
    </div>
  )
}
