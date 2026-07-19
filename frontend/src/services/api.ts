const API_BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  health: () => request<{ status: string; version: string; llm: any; config: any }>('/health'),

  chat: (messages: { role: string; content: string }[], model?: string) =>
    request<{ content: string; model: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ messages, model, stream: false }),
    }),

  listModels: () => request<{ models: { name: string; size: number }[]; count: number }>('/models'),

  createSession: (title?: string) =>
    request<{ id: string; title: string }>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Session' }),
    }),

  listSessions: () =>
    request<{ sessions: { id: string; title: string; status: string }[] }>('/sessions'),

  listTools: () => request<{ tools: any[]; count: number }>('/tools'),

  startRun: (goal: string, sessionId: string) =>
    request<{ run_id: string; status: string }>('/agents/run', {
      method: 'POST',
      body: JSON.stringify({ goal, session_id: sessionId }),
    }),

  getRun: (runId: string) => request<{ id: string; status: string; goal: string }>(`/runs/${runId}`),
}
