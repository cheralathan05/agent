import { useState, useCallback, useRef, useEffect } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'
import { useStore } from '../../stores/appStore'
import { Terminal, CheckCircle, XCircle, Clock, Loader2, AlertTriangle, Activity, GitCompare } from 'lucide-react'

interface EventLog {
  id: number
  event: string
  data: Record<string, any>
  timestamp: Date
}

export function AgentProgressPanel() {
  const { currentSessionId, setReviewRunId } = useStore()
  const [events, setEvents] = useState<EventLog[]>([])
  const [isMinimized, setIsMinimized] = useState(true)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [lastCompletedRun, setLastCompletedRun] = useState<{ runId: string; data: Record<string, any> } | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const handleEvent = useCallback((evt: { event: string; data: Record<string, any> }) => {
    if (evt.event === 'run.started') {
      setCurrentRunId(evt.data?.run_id || null)
      setLastCompletedRun(null)
    }

    if (evt.event === 'run.completed') {
      setLastCompletedRun({ runId: evt.data?.run_id || '', data: evt.data })
    }

    setEvents((prev) => {
      const next = [...prev, { id: Date.now(), ...evt, timestamp: new Date() }]
      return next.slice(-100) // Keep last 100 events
    })

    // Auto-expand on new tool calls or approvals
    if (['tool.started', 'approval.required', 'tool.failed'].includes(evt.event)) {
      setIsMinimized(false)
    }
  }, [])

  useWebSocket(handleEvent, currentRunId)

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [events])

  const handleReviewChanges = useCallback(() => {
    if (lastCompletedRun) {
      setReviewRunId(lastCompletedRun.runId)
    }
  }, [lastCompletedRun, setReviewRunId])

  const getEventIcon = (event: string) => {
    if (event === 'run.started') return <Activity className="w-3 h-3 text-accent-300" />
    if (event === 'run.completed') return <CheckCircle className="w-3 h-3 text-green-400" />
    if (event === 'run.failed') return <XCircle className="w-3 h-3 text-red-400" />
    if (event === 'tool.started') return <Loader2 className="w-3 h-3 text-yellow-400 animate-spin" />
    if (event === 'tool.completed') return <CheckCircle className="w-3 h-3 text-green-400" />
    if (event === 'tool.failed') return <XCircle className="w-3 h-3 text-red-400" />
    if (event === 'approval.required') return <AlertTriangle className="w-3 h-3 text-yellow-400" />
    if (event === 'plan.created') return <Terminal className="w-3 h-3 text-accent-300" />
    if (event === 'model.thinking') return <Loader2 className="w-3 h-3 text-gray-500 animate-spin" />
    return <Clock className="w-3 h-3 text-gray-500" />
  }

  const getEventLabel = (evt: EventLog): string => {
    const d = evt.data
    switch (evt.event) {
      case 'run.started': return `Agent run started: ${d?.goal?.slice(0, 50)}...`
      case 'run.completed': return `Run completed (${d?.steps || '?'} steps, ${d?.file_changes || 0} files changed)`
      case 'run.failed': return `Run failed: ${d?.error}`
      case 'run.limit_reached': return `Step limit reached (${d?.step}/${d?.max_steps})`
      case 'tool.started': return `Running: ${d?.tool}`
      case 'tool.completed': return `${d?.tool} completed (${d?.duration_ms}ms) ${d?.success ? '✓' : '✗'}`
      case 'tool.failed': return `${d?.tool} failed: ${d?.error}`
      case 'approval.required': return `Approval needed: ${d?.tool}`
      case 'approval.resolved': return `Approval ${d?.status}: ${d?.tool || ''}`
      case 'plan.created': return `Plan created (${d?.tasks?.length || 0} tasks)`
      case 'plan.replanned': return 'Plan revised'
      case 'model.thinking': return `Thinking (step ${d?.step})`
      default: return `${evt.event}: ${JSON.stringify(evt.data).slice(0, 60)}`
    }
  }

  const getEventColor = (event: string): string => {
    if (event.includes('failed') || event === 'run.failed') return 'text-red-400'
    if (event.includes('completed') || event === 'run.completed') return 'text-green-400'
    if (event.includes('approval')) return 'text-yellow-400'
    if (event.includes('started') || event === 'run.started') return 'text-accent-300'
    return 'text-gray-400'
  }

  if (!currentSessionId && events.length === 0) return null

  return (
    <div className="fixed bottom-12 left-4 z-50 w-80 glass-panel border-white/5 shadow-lg max-h-[50vh] flex flex-col">
      {/* Header */}
      <button
        onClick={() => setIsMinimized(!isMinimized)}
        className="flex items-center justify-between px-3 py-2 border-b border-white/5 shrink-0 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-accent-300" />
          <span className="text-[11px] font-medium">Agent Activity</span>
        </div>
        <div className="flex items-center gap-1.5">
          {isMinimized && events.length > 0 && (
            <span className="text-[9px] text-gray-500">{events.length} events</span>
          )}
          <span className="text-[9px] text-gray-500">{isMinimized ? '⏵' : '⏷'}</span>
        </div>
      </button>

      {/* Event list */}
      {!isMinimized && (
        <div ref={listRef} className="overflow-y-auto flex-1 p-1.5 space-y-0.5 max-h-[40vh]">
          {events.length === 0 && (
            <p className="text-[10px] text-gray-500 text-center py-3">
              No agent activity yet. Start a chat to see events.
            </p>
          )}
          {events.map((evt) => (
            <div
              key={evt.id}
              className={`flex items-start gap-2 px-2 py-1 rounded hover:bg-white/5 transition-colors ${getEventColor(evt.event)}`}
            >
              <span className="mt-0.5 shrink-0">{getEventIcon(evt.event)}</span>
              <div className="min-w-0">
                <p className="text-[10px] leading-tight truncate">{getEventLabel(evt)}</p>
                <p className="text-[8px] text-gray-600">
                  {evt.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {/* Review Changes button after completed run */}
          {lastCompletedRun && (
            <div className="pt-2 px-2">
              <button
                onClick={handleReviewChanges}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent-300/20 hover:bg-accent-300/30 text-accent-300 rounded text-[11px] transition-all border border-accent-300/20 hover:border-accent-300/40"
              >
                <GitCompare className="w-3.5 h-3.5" />
                Review Changes
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
