import { User, Bot, AlertCircle } from 'lucide-react'

interface ChatMessageProps {
  message: { role: string; content: string }
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const isError = message.role === 'system' || message.content.startsWith('Error:')

  if (isUser) {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[80%] bg-accent-500/20 border border-accent-500/30 rounded-xl px-4 py-2.5">
          <p className="text-sm text-white">{message.content}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-accent-300 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-white" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isError ? 'bg-red-500/20' : 'bg-surface-300'
      }`}>
        {isError ? (
          <AlertCircle className="w-4 h-4 text-red-400" />
        ) : (
          <Bot className="w-4 h-4 text-accent-300" />
        )}
      </div>
      <div className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
        isError ? 'bg-red-500/10 border border-red-500/20' : 'bg-surface-200 border border-white/5'
      }`}>
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  )
}
