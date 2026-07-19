export interface DiffFile {
  id: string | null
  file_path: string
  change_type: string  // create, modify, delete
  old_content: string | null
  new_content: string | null
  diff: string | null
  lines_added: number
  lines_removed: number
  status: string  // pending, accepted, rejected
}

export interface DiffResponse {
  run_id: string
  files: DiffFile[]
  total_changes: number
  total_added: number
  total_removed: number
}

const API_BASE = '/api/v1'

export async function fetchRunDiff(runId: string): Promise<DiffResponse> {
  const res = await fetch(`${API_BASE}/runs/${runId}/diff`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateFileStatus(runId: string, changeId: string, status: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/diff/${changeId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
