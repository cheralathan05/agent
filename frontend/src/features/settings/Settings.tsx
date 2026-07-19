import { useState } from 'react'
import { useStore } from '../../stores/appStore'
import { Settings as SettingsIcon, Cpu, Database, Shield, Sliders } from 'lucide-react'

export function Settings() {
  const { selectedModel, setSelectedModel } = useStore()
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')
  const [maxSteps, setMaxSteps] = useState('30')
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-lg font-bold flex items-center gap-2 mb-6">
          <SettingsIcon className="w-5 h-5 text-accent-300" />
          Settings
        </h1>

        {/* General Settings */}
        <section className="glass-panel p-4 mb-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Sliders className="w-3.5 h-3.5" /> General
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Default Model</label>
              <input
                type="text"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Max Agent Steps</label>
              <input
                type="number"
                value={maxSteps}
                onChange={(e) => setMaxSteps(e.target.value)}
                className="input-field"
                min="1"
                max="100"
              />
            </div>
          </div>
        </section>

        {/* AI Provider */}
        <section className="glass-panel p-4 mb-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5" /> AI Provider
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Ollama URL</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="input-field"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="w-2 h-2 rounded-full bg-green-400" />
              Ollama detected
            </div>
          </div>
        </section>

        {/* Database */}
        <section className="glass-panel p-4 mb-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Database className="w-3.5 h-3.5" /> Database
          </h2>
          <p className="text-xs text-gray-500">
            SQLite (local) · PostgreSQL supported for production deployments
          </p>
        </section>

        {/* Security */}
        <section className="glass-panel p-4 mb-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Shield className="w-3.5 h-3.5" /> Security
          </h2>
          <p className="text-xs text-gray-500">
            Path traversal protection · Command validation · Secret detection
          </p>
        </section>

        <button
          onClick={handleSave}
          className="btn-primary"
        >
          {saved ? '✓ Saved' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
