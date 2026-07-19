import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { useStore } from '../stores/appStore'
import { Activity, Cpu, Database, Wifi, WifiOff } from 'lucide-react'

export function StatusBar() {
  const { health, setHealth } = useStore()

  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 15000,
    retry: 2,
  })

  useEffect(() => {
    if (data) setHealth(data)
  }, [data, setHealth])

  const isConnected = health?.status === 'ok'

  return (
    <footer className="h-7 border-t border-white/5 bg-surface-200/80 flex items-center px-4 text-[11px] text-gray-500 gap-4 shrink-0">
      {isConnected ? (
        <span className="flex items-center gap-1.5 text-green-400">
          <Wifi className="w-3 h-3" /> Connected
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-red-400">
          <WifiOff className="w-3 h-3" /> Disconnected
        </span>
      )}

      <span className="flex items-center gap-1.5">
        <Cpu className="w-3 h-3" /> {health?.config?.model || 'N/A'}
      </span>

      <span className="flex items-center gap-1.5">
        <Database className="w-3 h-3" /> {health?.config?.database || 'N/A'}
      </span>

      <span className="flex items-center gap-1.5 ml-auto">
        <Activity className="w-3 h-3" /> v{health?.version || '1.0.0'}
      </span>
    </footer>
  )
}
