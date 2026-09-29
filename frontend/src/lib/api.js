// Single place where the frontend talks to the backend. Relative URLs only —
// in dev these are proxied by Vite, in production they are served from the
// same origin, so the app never references a remote host.
const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  status: (deep = false) => request(`/status?deep=${deep ? 'true' : 'false'}`),
  config: () => request('/status/config'),
  stats: () => request('/index/stats'),
  documents: () => request('/index/documents'),
  documentChunks: (id) => request(`/index/documents/${id}/chunks`),
  deleteDocument: (id) => request(`/index/documents/${id}`, { method: 'DELETE' }),
  resetIndex: () => request('/index/reset', { method: 'POST' }),
  history: (limit = 20) => request(`/query/history?limit=${limit}`),
  imageUrl: (path) => `${BASE}/index/image?path=${encodeURIComponent(path)}`,

  ingest(files) {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    return request('/ingest', { method: 'POST', body: form })
  },

  query(payload) {
    return request('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
}

export function formatBytes(n) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)))
  return `${(n / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`
}

export function formatSeconds(s) {
  if (s == null) return ''
  const total = Math.floor(s)
  const m = Math.floor(total / 60)
  const sec = total % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}
