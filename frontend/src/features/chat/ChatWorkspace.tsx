import { useState, useRef, useEffect, useCallback } from 'react'
import { useStore } from '../../stores/appStore'
import { api } from '../../services/api'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { Terminal, Loader2 } from 'lucide-react'

export function ChatWorkspace() {
  const { messages, addMessage, isStreaming, setIsStreaming, selectedModel, currentSessionId, setCurrentSessionId } = useStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize session on mount
  useEffect(() => {
    if (!currentSessionId) {
      api.createSession().then((session) => {
        setCurrentSessionId(session.id)
      }).catch(() => {
        console.warn('Could not create session - backend may not be running')
      })
    }
  }, [currentSessionId, setCurrentSessionId])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMsg = input.trim()
    setInput('')
    addMessage({ role: 'user', content: userMsg })
    setIsStreaming(true)

    try {
      // Use streaming for better UX
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: userMsg }],
          model: selectedModel,
          stream: true,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      let assistantContent = ''
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.event === 'token') {
                assistantContent += data.data?.content || ''
              } else if (data.event === 'complete') {
                assistantContent = data.data?.content || ''
              } else if (data.event === 'error') {
                throw new Error(data.data?.content || 'Stream error')
              }
            } catch { /* skip malformed events */ }
          }
        }
      }

      if (assistantContent) {
        addMessage({ role: 'assistant', content: assistantContent })
      }
    } catch (err: any) {
      addMessage({ role: 'assistant', content: `Error: ${err.message}` })
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-11 border-b border-white/5 flex items-center px-4 gap-3 shrink-0">
        <Terminal className="w-4 h-4 text-accent-300" />
        <span className="text-sm font-medium">Agent Chat</span>
        <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded">
          {selectedModel}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <Terminal className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm">Start a conversation with MyAgent</p>
            <p className="text-xs mt-1">Ask me to help with your project</p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isStreaming && (
          <div className="flex items-center gap-2 text-gray-400 text-sm ml-11">
            <Loader2 className="w-4 h-4 animate-spin" />
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={isStreaming}
      />
    </div>
  )
}
