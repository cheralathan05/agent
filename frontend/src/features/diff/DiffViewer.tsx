import { useMemo } from 'react'
import type { DiffFile } from '../../services/diff'

function parseDiff(diff: string | null): Array<{ type: 'add' | 'remove' | 'context'; content: string }> {
  if (!diff) return []
  const lines: Array<{ type: 'add' | 'remove' | 'context'; content: string }> = []
  for (const line of diff.split('\n')) {
    if (line.startsWith('+') && !line.startsWith('+++')) {
      lines.push({ type: 'add', content: line.slice(1) })
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      lines.push({ type: 'remove', content: line.slice(1) })
    } else if (line.startsWith('@@')) {
      lines.push({ type: 'context', content: line })
    } else {
      lines.push({ type: 'context', content: line })
    }
  }
  return lines
}

interface DiffViewerProps {
  file: DiffFile
}

function FileIcon({ path }: { path: string }) {
  const ext = path.split('.').pop()?.toLowerCase()
  const colors: Record<string, string> = {
    py: 'text-blue-400', ts: 'text-blue-300', tsx: 'text-cyan-300',
    js: 'text-yellow-400', jsx: 'text-cyan-300', rs: 'text-orange-400',
    go: 'text-cyan-400', java: 'text-red-400', rb: 'text-red-300',
    css: 'text-pink-400', html: 'text-orange-300', json: 'text-green-400',
    md: 'text-gray-400', yml: 'text-red-300', yaml: 'text-red-300',
    toml: 'text-yellow-300', sql: 'text-purple-400', sh: 'text-green-300',
  }
  return (
    <span className={`text-[10px] font-mono ${colors[ext || ''] || 'text-gray-400'}`}>
      .{ext || '?'}
    </span>
  )
}

function ChangeTypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    create: 'bg-green-500/20 text-green-400',
    modify: 'bg-yellow-500/20 text-yellow-400',
    delete: 'bg-red-500/20 text-red-400',
  }
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded ${styles[type] || 'bg-gray-500/20 text-gray-400'}`}>
      {type}
    </span>
  )
}

export function DiffViewer({ file }: DiffViewerProps) {
  const lines = useMemo(() => parseDiff(file.diff), [file.diff])
  const ext = file.file_path.split('.').pop()?.toLowerCase() || ''

  return (
    <div className="rounded-lg border border-white/5 overflow-hidden bg-surface-300/50">
      {/* File header */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface-200 border-b border-white/5">
        <div className="flex items-center gap-2 min-w-0">
          <FileIcon path={file.file_path} />
          <span className="text-xs font-mono text-gray-200 truncate">{file.file_path}</span>
          <ChangeTypeBadge type={file.change_type} />
        </div>
        <div className="flex items-center gap-2 text-[10px] text-gray-500 shrink-0">
          {file.lines_added > 0 && <span className="text-green-400">+{file.lines_added}</span>}
          {file.lines_removed > 0 && <span className="text-red-400">-{file.lines_removed}</span>}
        </div>
      </div>

      {/* Diff content */}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px] font-mono leading-[1.6]">
          <tbody>
            {lines.length === 0 && (
              <tr>
                <td colSpan={2} className="px-3 py-4 text-center text-gray-500 text-[10px]">
                  {file.change_type === 'create' ? 'New file (no diff available)' : 'No changes'}
                </td>
              </tr>
            )}
            {lines.map((line, i) => {
              const bgColor = line.type === 'add'
                ? 'bg-green-500/10'
                : line.type === 'remove'
                ? 'bg-red-500/10'
                : ''
              const textColor = line.type === 'add'
                ? 'text-green-300'
                : line.type === 'remove'
                ? 'text-red-300'
                : 'text-gray-300'
              const prefix = line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '

              return (
                <tr key={i} className={bgColor}>
                  <td className="text-right text-gray-600 select-none px-2 w-10 border-r border-white/5">
                    {i + 1}
                  </td>
                  <td className={`px-3 whitespace-pre ${textColor}`}>
                    {prefix}{line.content}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-3 px-3 py-1.5 bg-surface-200 border-t border-white/5 text-[9px] text-gray-500">
        <span>{lines.length} lines</span>
        {file.lines_added > 0 && <span className="text-green-400">+{file.lines_added} added</span>}
        {file.lines_removed > 0 && <span className="text-red-400">-{file.lines_removed} removed</span>}
      </div>
    </div>
  )
}
