import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'
import { useStore } from '../../stores/appStore'
import { Brain, Check, RefreshCw, Loader2 } from 'lucide-react'

export function ModelManager() {
  const { selectedModel, setSelectedModel } = useStore()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['models'],
    queryFn: api.listModels,
    refetchInterval: 30000,
  })

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Brain className="w-5 h-5 text-accent-300" />
              AI Models
            </h1>
            <p className="text-sm text-gray-500 mt-1">Select an Ollama model for the agent</p>
          </div>
          <button
            onClick={() => refetch()}
            className="btn-ghost flex items-center gap-1.5"
            disabled={isLoading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Current model */}
        <div className="glass-panel p-4 mb-4">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">Active Model</span>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm font-medium">{selectedModel}</span>
            <span className="text-[10px] text-green-400 bg-green-500/10 px-2 py-0.5 rounded">Active</span>
          </div>
        </div>

        {/* Model list */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
          </div>
        ) : (
          <div className="space-y-1">
            {data?.models?.map((model: any) => (
              <button
                key={model.name}
                onClick={() => setSelectedModel(model.name)}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-sm transition-all duration-150 ${
                  selectedModel === model.name
                    ? 'bg-accent-500/10 border border-accent-500/30'
                    : 'hover:bg-white/5 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  {selectedModel === model.name && (
                    <Check className="w-4 h-4 text-accent-300" />
                  )}
                  <div className="text-left">
                    <span className="text-white">{model.name}</span>
                    {model.size && (
                      <span className="text-[10px] text-gray-500 ml-2">
                        {(model.size / 1024 / 1024 / 1024).toFixed(1)} GB
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
            {(!data?.models || data.models.length === 0) && (
              <p className="text-sm text-gray-500 text-center py-8">
                No models found. Make sure Ollama is running.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
