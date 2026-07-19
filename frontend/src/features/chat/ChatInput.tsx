import { Send } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  disabled?: boolean
}

export function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="border-t border-white/5 p-3 shrink-0">
      <div className="flex gap-2 items-end">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask MyAgent to help with your project..."
          rows={2}
          className="input-field resize-none flex-1"
          disabled={disabled}
        />
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="btn-primary h-[42px] w-[42px] flex items-center justify-center p-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-[10px] text-gray-600 mt-1.5">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
