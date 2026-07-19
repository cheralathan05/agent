import { useState, useCallback } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatWorkspace } from './features/chat/ChatWorkspace'
import { ModelManager } from './features/models/ModelManager'
import { Settings } from './features/settings/Settings'
import { StatusBar } from './components/StatusBar'
import { ApprovalPanel } from './features/approvals/ApprovalPanel'
import { AgentProgressPanel } from './features/events/AgentProgressPanel'
import { DiffReviewPanel } from './features/diff/DiffReviewPanel'
import { useStore } from './stores/appStore'
import { GitCompare } from 'lucide-react'

type View = 'chat' | 'models' | 'settings' | 'review'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const { health, reviewRunId, setReviewRunId } = useStore()

  const handleViewChange = useCallback((v: View) => {
    setView(v)
    if (v !== 'review') {
      setReviewRunId(null)
    }
  }, [setReviewRunId])

  // When reviewRunId gets set (e.g. from AgentProgressPanel), switch to review view
  // Using a ref to store previous value to avoid infinite loops
  const [prevReviewRunId, setPrevReviewRunId] = useState<string | null>(null)
  if (reviewRunId && reviewRunId !== prevReviewRunId) {
    setPrevReviewRunId(reviewRunId)
    setView('review')
  }

  return (
    <div className="h-screen flex flex-col bg-surface-100 text-white overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentView={view} onViewChange={handleViewChange} />
        
        <main className="flex-1 flex flex-col overflow-hidden">
          {view === 'chat' && <ChatWorkspace />}
          {view === 'models' && <ModelManager />}
          {view === 'settings' && <Settings />}
          {view === 'review' && reviewRunId ? (
            <DiffReviewPanel
              runId={reviewRunId}
              onClose={() => { setView('chat'); setReviewRunId(null); setPrevReviewRunId(null) }}
            />
          ) : view === 'review' && !reviewRunId ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <GitCompare className="w-12 h-12 mx-auto mb-4 opacity-30" />
                <p className="text-sm font-medium text-gray-400">No changes to review</p>
                <p className="text-xs mt-2 text-gray-600">Run an agent task to see file changes here.</p>
                <button
                  onClick={() => handleViewChange('chat')}
                  className="mt-6 text-[11px] text-accent-300 hover:text-white transition-colors"
                >
                  Open Chat →
                </button>
              </div>
            </div>
          ) : null}
        </main>
      </div>
      
      <ApprovalPanel />
      <AgentProgressPanel />
      <StatusBar />
    </div>
  )
}
