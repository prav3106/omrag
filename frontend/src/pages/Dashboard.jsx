import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { IconRefresh } from '../components/Icons.jsx'
import { Bar, Card, Spinner, Stat, StatusDot } from '../components/Primitives.jsx'

const MODALITIES = [
  { key: 'text',  label: 'Document chunks' },
  { key: 'image', label: 'Image chunks' },
  { key: 'audio', label: 'Audio segments' },
]

export default function Dashboard({ onNavigate, refreshKey, onRefresh }) {
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let live = true
    setLoading(true)
    Promise.all([api.status(), api.config()])
      .then(([s, c]) => { if (live) { setStatus(s); setConfig(c) } })
      .catch(() => {})
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [refreshKey])

  const stats = status?.stats
  const byModality = stats?.by_modality || {}
  const maxChunks = Math.max(1, ...MODALITIES.map((m) => byModality[m.key] || 0))

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <p className="mt-0.5 text-sm text-ink-500">
            Pipeline health and index composition, computed entirely on this machine.
          </p>
        </div>
        <button className="btn-ghost" onClick={onRefresh}>
          {loading ? <Spinner /> : <IconRefresh size={15} />} Refresh
        </button>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Documents" value={stats?.documents ?? '—'} hint="ingested sources" />
        <Stat label="Indexed chunks" value={stats?.chunks?.toLocaleString() ?? '—'} hint="across all modalities" />
        <Stat label="Collection" value={stats?.collection ?? '—'} hint="Qdrant, local" />
        <Stat
          label="Vector spaces"
          value={stats?.vector_schema?.length ?? '—'}
          hint={stats?.vector_schema?.map((v) => `${v.name} ${v.dim}d`).join(' · ') || 'not created yet'}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Index composition" subtitle="Chunks by modality" className="lg:col-span-2">
          {stats?.chunks ? (
            <div className="space-y-4">
              {MODALITIES.map(({ key, label }) => (
                <div key={key}>
                  <div className="mb-1.5 flex items-baseline justify-between">
                    <span className="text-sm">{label}</span>
                    <span className="text-sm font-medium tabular-nums">
                      {(byModality[key] || 0).toLocaleString()}
                    </span>
                  </div>
                  <Bar value={byModality[key] || 0} max={maxChunks} />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-ink-500">Nothing indexed yet.</p>
              <button className="btn-primary mt-3" onClick={() => onNavigate('knowledge')}>
                Ingest your first files
              </button>
            </div>
          )}
        </Card>

        <Card title="Dependencies" subtitle="Local services and binaries">
          <div className="space-y-2.5">
            {(status?.dependencies || []).map((d) => (
              <div key={d.name} className="flex items-center gap-2.5">
                <StatusDot ok={d.ok} />
                <span className="flex-1 truncate text-sm">{d.name}</span>
              </div>
            ))}
            {!status && <p className="text-sm text-ink-500">Contacting backend…</p>}
          </div>
          <button className="btn-ghost mt-4 w-full" onClick={() => onNavigate('status')}>
            Full system status
          </button>
        </Card>
      </div>

      <Card title="Active models" subtitle="Loaded from the local cache; no API calls">
        <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['Text embeddings', config?.text_model],
            ['Image embeddings', config?.image_model],
            ['Cross-encoder reranker', config?.rerank_enabled ? config?.reranker_model : 'disabled'],
            ['Transcription', config?.whisper_model],
            ['Generation', config?.llm_model],
            ['Vision description', config?.vision_describe_enabled ? config?.vision_model : 'disabled'],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="label">{k}</dt>
              <dd className="mt-1 break-all font-mono text-xs text-ink-700 dark:text-ink-300">
                {v || '—'}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  )
}
