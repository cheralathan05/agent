import { useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatWorkspace } from './features/chat/ChatWorkspace'
import { ModelManager } from './features/models/ModelManager'
import { Settings } from './features/settings/Settings'
import { StatusBar } from './components/StatusBar'
import { ApprovalPanel } from './features/approvals/ApprovalPanel'
import { useStore } from './stores/appStore'

type View = 'chat' | 'models' | 'settings'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const { health } = useStore()

  return (
    <div className="h-screen flex flex-col bg-surface-100 text-white overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentView={view} onViewChange={setView} />
        
        <main className="flex-1 flex flex-col overflow-hidden">
          {view === 'chat' && <ChatWorkspace />}
          {view === 'models' && <ModelManager />}
          {view === 'settings' && <Settings />}
        </main>
      </div>
      
      <ApprovalPanel />
      <StatusBar />
    </div>
  )
}
