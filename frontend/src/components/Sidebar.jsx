import {
  IconChat, IconDashboard, IconLab, IconLibrary,
  IconMoon, IconPulse, IconSun,
} from './Icons.jsx'

export const NAV = [
  { id: 'dashboard',  label: 'Dashboard',      Icon: IconDashboard },
  { id: 'knowledge',  label: 'Knowledge Base', Icon: IconLibrary },
  { id: 'chat',       label: 'Chat Workspace', Icon: IconChat },
  { id: 'lab',        label: 'Processor Lab',  Icon: IconLab },
  { id: 'status',     label: 'System Status',  Icon: IconPulse },
]

export default function Sidebar({ page, onNavigate, dark, onToggleTheme, chunkCount }) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-ink-200 bg-white dark:border-ink-800 dark:bg-ink-900">
      <div className="px-4 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent-600 text-xs font-bold text-white">
            RG
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold">Offline RAG</p>
            <p className="text-[11px] text-ink-500">Multimodal · local</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-2">
        {NAV.map(({ id, label, Icon }) => {
          const active = page === id
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                active
                  ? 'bg-accent-50 font-medium text-accent-700 dark:bg-accent-900/30 dark:text-accent-200'
                  : 'text-ink-600 hover:bg-ink-100 dark:text-ink-400 dark:hover:bg-ink-800'
              }`}
            >
              <Icon size={17} />
              {label}
            </button>
          )
        })}
      </nav>

      <div className="space-y-3 border-t border-ink-200 p-3 dark:border-ink-800">
        <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-2.5 py-2 dark:bg-emerald-950/40">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
            Local processing only
          </span>
        </div>
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] tabular-nums text-ink-500">
            {chunkCount != null ? `${chunkCount.toLocaleString()} chunks` : '—'}
          </span>
          <button
            onClick={onToggleTheme}
            title="Toggle theme"
            className="rounded-md p-1.5 text-ink-500 hover:bg-ink-100 dark:hover:bg-ink-800"
          >
            {dark ? <IconSun size={15} /> : <IconMoon size={15} />}
          </button>
        </div>
      </div>
    </aside>
  )
}
