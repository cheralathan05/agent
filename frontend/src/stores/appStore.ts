import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface HealthStatus {
  status: string
  version: string
  llm?: { status: string; models: string[]; default_model_available: boolean }
  config?: { model: string; provider: string; database: string }
}

interface Message {
  id: string
  role: string
  content: string
}

interface AppState {
  health: HealthStatus | null
  selectedModel: string
  messages: Message[]
  isStreaming: boolean
  currentSessionId: string | null
  reviewRunId: string | null
  
  setHealth: (health: HealthStatus) => void
  setSelectedModel: (model: string) => void
  addMessage: (msg: { role: string; content: string }) => void
  setMessages: (messages: Message[]) => void
  setIsStreaming: (v: boolean) => void
  setCurrentSessionId: (id: string | null) => void
  setReviewRunId: (id: string | null) => void
  clearMessages: () => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      health: null,
      selectedModel: 'qwen2.5-coder',
      messages: [],
      isStreaming: false,
      currentSessionId: null,
      reviewRunId: null,

      setHealth: (health) => set({ health }),
      setSelectedModel: (model) => set({ selectedModel: model }),
      addMessage: (msg) =>
        set((state) => ({
          messages: [...state.messages, { ...msg, id: crypto.randomUUID() }],
        })),
      setMessages: (messages) => set({ messages }),
      setIsStreaming: (v) => set({ isStreaming: v }),
      setCurrentSessionId: (id) => set({ currentSessionId: id }),
      setReviewRunId: (id) => set({ reviewRunId: id }),
      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: 'myagent-store',
      partialize: (state) => ({
        selectedModel: state.selectedModel,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
)
