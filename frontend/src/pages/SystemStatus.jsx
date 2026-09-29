import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { IconRefresh } from '../components/Icons.jsx'
import { Card, Spinner, StatusRow } from '../components/Primitives.jsx'

export default function SystemStatus({ refreshKey, onRefresh }) {
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState(null)
  const [deep, setDeep] = useState(false)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)

  const load = (deepCheck) => {
    setLoading(true)
    Promise.all([api.status(deepCheck), api.config()])
      .then(([s, c]) => { setStatus(s); setConfig(c) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }
  useEffect(() => { load(deep) }, [refreshKey, deep])

  const reset = async () => {
    if (!confirm('This clears the Qdrant collection, the SQLite registry and all uploaded files. Continue?')) return
    setResetting(true)
    try { await api.resetIndex(); onRefresh(); load(deep) } finally { setResetting(false) }
  }

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">System Status</h1>
          <p className="mt-0.5 text-sm text-ink-500">
            Health of every local dependency the pipeline relies on.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-ghost"
            onClick={() => setDeep((d) => !d)}
            title="Deep checks load the embedding and reranker models into memory"
          >
            {deep ? 'Deep checks on' : 'Run deep checks'}
          </button>
          <button className="btn-ghost" onClick={() => load(deep)}>
            {loading ? <Spinner /> : <IconRefresh size={15} />} Refresh
          </button>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Dependencies" subtitle={deep ? 'Including model load verification' : 'Fast checks only'}>
          {(status?.dependencies || []).map((d) => (
            <StatusRow key={d.name} name={d.name} ok={d.ok} detail={d.detail} />
          ))}
          {!status && <p className="py-4 text-sm text-ink-500">Contacting backend…</p>}
        </Card>

        <div className="space-y-4">
          <Card title="Vector schema" subtitle={status?.stats?.collection || 'collection not created'}>
            {status?.stats?.vector_schema?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-200 text-left dark:border-ink-800">
                    <th className="pb-2 font-medium text-ink-500">Name</th>
                    <th className="pb-2 font-medium text-ink-500">Dim</th>
                    <th className="pb-2 font-medium text-ink-500">Metric</th>
                  </tr>
                </thead>
                <tbody>
                  {status.stats.vector_schema.map((v) => (
                    <tr key={v.name} className="border-b border-ink-100 last:border-0 dark:border-ink-800">
                      <td className="py-2 font-mono text-xs">{v.name}</td>
                      <td className="py-2 tabular-nums">{v.dim}</td>
                      <td className="py-2">{v.metric}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-ink-500">Qdrant is not reachable, so the schema cannot be read.</p>
            )}
          </Card>

          <Card title="Pipeline configuration">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              {[
                ['Chunk size', `${config?.chunk_tokens} tokens`],
                ['Chunk overlap', `${config?.chunk_overlap} tokens`],
                ['Candidates (k)', config?.candidate_k],
                ['Final context (k)', config?.final_k],
                ['Dense weight', config?.weights?.dense],
                ['Rerank weight', config?.weights?.rerank],
                ['Diversity weight', config?.weights?.diversity],
                ['Reranking', config?.rerank_enabled ? 'enabled' : 'disabled'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <dt className="text-ink-500">{k}</dt>
                  <dd className="font-mono tabular-nums">{v ?? '—'}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      </div>

      <Card title="Danger zone" subtitle="Clears everything indexed on this machine">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-ink-500">
            Drops the Qdrant collection, empties the SQLite registry and deletes uploaded and extracted files.
          </p>
          <button
            onClick={reset}
            disabled={resetting}
            className="btn shrink-0 border border-rose-300 text-rose-700 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-400 dark:hover:bg-rose-950"
          >
            {resetting ? <Spinner /> : null} Reset index
          </button>
        </div>
      </Card>
    </div>
  )
}
