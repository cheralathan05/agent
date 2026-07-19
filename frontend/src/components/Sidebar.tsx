import { MessageSquare, Brain, Settings, Activity, Database, Shield } from 'lucide-react'

const navItems = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'models', label: 'Models', icon: Brain },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const

type View = 'chat' | 'models' | 'settings'

interface SidebarProps {
  currentView: View
  onViewChange: (v: View) => void
}

export function Sidebar({ currentView, onViewChange }: SidebarProps) {
  return (
    <aside className="w-56 border-r border-white/5 flex flex-col bg-surface-200/50">
      {/* Logo */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-300 flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm">MyAgent</span>
        </div>
        <span className="text-[10px] text-gray-500 mt-1 block">AI Coding Agent</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onViewChange(id as View)}
            className={`sidebar-item w-full ${currentView === id ? 'active' : ''}`}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      {/* Bottom status */}
      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          <Shield className="w-3 h-3" />
          <span>Local · Ollama</span>
        </div>
      </div>
    </aside>
  )
}
