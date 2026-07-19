export interface Approval {
  id: string
  run_id: string
  tool_name: string
  action: string
  reason: string
  risk: string
  status: string
  permission_type: string
  created_at: string | null
}

const API_BASE = '/api/v1'

export async function fetchPendingApprovals(): Promise<{ approvals: Approval[]; count: number }> {
  const res = await fetch(`${API_BASE}/approvals?status=pending`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function approveApproval(id: string, permissionType: string = 'once'): Promise<void> {
  const res = await fetch(`${API_BASE}/approvals/${id}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ permission_type: permissionType }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
}

export async function denyApproval(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/approvals/${id}/deny`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
}
