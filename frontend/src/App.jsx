import { useCallback, useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import KnowledgeBase from './pages/KnowledgeBase.jsx'
import ChatWorkspace from './pages/ChatWorkspace.jsx'
import ProcessorLab from './pages/ProcessorLab.jsx'
import SystemStatus from './pages/SystemStatus.jsx'
import { api } from './lib/api.js'

const THEME_KEY = 'omrag.theme'

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [refreshKey, setRefreshKey] = useState(0)
  const [chunkCount, setChunkCount] = useState(null)
  const [dark, setDark] = useState(() => {
    try {
      const stored = localStorage.getItem(THEME_KEY)
      if (stored) return stored === 'dark'
    } catch { /* storage may be unavailable */ }
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light') } catch { /* ignore */ }
  }, [dark])

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  useEffect(() => {
    api.stats().then((s) => setChunkCount(s.chunks)).catch(() => setChunkCount(null))
  }, [refreshKey])

  const props = { refreshKey, onRefresh: refresh, onNavigate: setPage }

  return (
    <div className="flex h-full">
      <Sidebar
        page={page}
        onNavigate={setPage}
        dark={dark}
        onToggleTheme={() => setDark((d) => !d)}
        chunkCount={chunkCount}
      />
      <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto h-full max-w-[1400px] p-6">
          {page === 'dashboard' && <Dashboard {...props} />}
          {page === 'knowledge' && <KnowledgeBase {...props} />}
          {page === 'chat' && <ChatWorkspace {...props} />}
          {page === 'lab' && <ProcessorLab {...props} />}
          {page === 'status' && <SystemStatus {...props} />}
        </div>
      </main>
    </div>
  )
}
