import { useEffect, useRef, useCallback } from 'react'

interface AgentEvent {
  event: string
  data: Record<string, any>
}

type EventHandler = (event: AgentEvent) => void

const WS_BASE = `ws://${window.location.hostname}:8000`

export function useWebSocket(onEvent: EventHandler, runId?: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const clientIdRef = useRef<string | null>(null)
  const runIdRef = useRef<string | null>(null)

  runIdRef.current = runId || null

  const sendSubscribe = useCallback((ws: WebSocket, rid: string) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe_run', run_id: rid }))
    }
  }, [])

  const sendUnsubscribe = useCallback((ws: WebSocket) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'unsubscribe_run' }))
    }
  }, [])

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>
    let isDisposed = false

    function connect() {
      if (isDisposed) return
      ws = new WebSocket(`${WS_BASE}/ws`)
      wsRef.current = ws

      ws.onopen = () => {
        // Subscription happens on connected acknowledgment, not here
      }

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data)
          if (data.event === 'connected') {
            clientIdRef.current = data.data?.client_id
            // Subscribe once we're connected and know our client_id
            if (runIdRef.current && ws?.readyState === WebSocket.OPEN) {
              sendSubscribe(ws, runIdRef.current)
            }
          }
          onEvent(data)
        } catch { /* skip malformed */ }
      }

      ws.onclose = () => {
        wsRef.current = null
        if (!isDisposed) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }

      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()

    return () => {
      isDisposed = true
      clearTimeout(reconnectTimer)
      if (ws) {
        sendUnsubscribe(ws)
        ws.close()
        wsRef.current = null
      }
    }
  }, [onEvent, sendSubscribe, sendUnsubscribe])

  // Reactively subscribe/unsubscribe when runId changes
  useEffect(() => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    sendUnsubscribe(ws)
    if (runId) {
      sendSubscribe(ws, runId)
      runIdRef.current = runId
    }
  }, [runId, sendSubscribe, sendUnsubscribe])

  return { clientId: clientIdRef.current }
}
