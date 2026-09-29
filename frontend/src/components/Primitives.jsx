import { IconCheck, IconX } from './Icons.jsx'

export function Card({ title, subtitle, right, children, className = '', pad = true }) {
  return (
    <section className={`surface ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 border-b border-ink-200 px-4 py-3 dark:border-ink-800">
          <div>
            {title && <h2 className="text-sm font-semibold">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={`flex min-h-0 flex-1 flex-col ${pad ? 'p-4' : ''}`}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, hint }) {
  return (
    <div className="surface p-4">
      <p className="label">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-500">{hint}</p>}
    </div>
  )
}

export function StatusDot({ ok }) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
        ok ? 'bg-emerald-500' : 'bg-rose-500'
      }`}
    />
  )
}

export function StatusRow({ name, ok, detail }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-ink-100 py-2.5 last:border-0 dark:border-ink-800">
      <div className="flex items-start gap-2.5">
        <span className={`mt-0.5 ${ok ? 'text-emerald-600' : 'text-rose-600'}`}>
          {ok ? <IconCheck size={15} /> : <IconX size={15} />}
        </span>
        <div>
          <p className="text-sm font-medium">{name}</p>
          {detail && <p className="mt-0.5 break-all font-mono text-[11px] text-ink-500">{detail}</p>}
        </div>
      </div>
      <span className={`chip shrink-0 ${
        ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400'
           : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-400'}`}>
        {ok ? 'ready' : 'unavailable'}
      </span>
    </div>
  )
}

const MODALITY_STYLES = {
  text:  'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300',
  image: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-300',
  audio: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300',
}

export function ModalityChip({ modality, children }) {
  return (
    <span className={`chip ${MODALITY_STYLES[modality] || MODALITY_STYLES.text}`}>
      {children || modality}
    </span>
  )
}

export function Empty({ icon, title, hint }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <span className="text-ink-300">{icon}</span>
      <p className="text-sm font-medium text-ink-600 dark:text-ink-300">{title}</p>
      {hint && <p className="max-w-sm text-xs text-ink-500">{hint}</p>}
    </div>
  )
}

export function Spinner({ size = 16 }) {
  return (
    <span
      style={{ width: size, height: size }}
      className="inline-block animate-spin rounded-full border-2 border-current border-r-transparent opacity-60"
    />
  )
}

export function Bar({ value, max, className = '' }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800 ${className}`}>
      <div className="h-full rounded-full bg-accent-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}
