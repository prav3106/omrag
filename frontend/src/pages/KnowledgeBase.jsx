import { useEffect, useState } from 'react'
import { api, formatBytes } from '../lib/api.js'
import Dropzone from '../components/Dropzone.jsx'
import { IconLibrary, IconTrash } from '../components/Icons.jsx'
import { modalityIcon } from '../components/Icons.jsx'
import { Card, Empty, ModalityChip, Spinner } from '../components/Primitives.jsx'

export default function KnowledgeBase({ refreshKey, onRefresh }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    api.documents()
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [refreshKey])

  const ingest = async (files) => {
    setBusy(true); setError(null); setReport(null)
    try {
      setReport(await api.ingest(files))
      load(); onRefresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (doc) => {
    if (!confirm(`Remove "${doc.file_name}" and its chunks from the index?`)) return
    try { await api.deleteDocument(doc.doc_id); load(); onRefresh() }
    catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Knowledge Base</h1>
        <p className="mt-0.5 text-sm text-ink-500">
          Ingest documents, images and recordings. Files are parsed, chunked, embedded and indexed locally.
        </p>
      </header>

      <Dropzone onFiles={ingest} busy={busy} />

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
          {error}
        </div>
      )}

      {report && (
        <Card title="Ingestion report" subtitle={`${report.total_chunks} new chunk(s) indexed`}>
          <ul className="space-y-2">
            {report.results.map((r, i) => (
              <li key={i} className="flex items-start justify-between gap-4 text-sm">
                <span className="truncate font-medium">{r.file_name}</span>
                <span className="shrink-0 text-xs text-ink-500">
                  {r.error
                    ? <span className="text-rose-600">{r.error}</span>
                    : `${r.chunks_created} new · ${r.chunks_skipped} duplicate · ${r.duration_ms} ms`}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Indexed sources" subtitle={`${docs.length} document(s)`} pad={false}>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-ink-500">
            <Spinner /> Loading index…
          </div>
        ) : docs.length === 0 ? (
          <Empty
            icon={<IconLibrary size={28} />}
            title="No sources indexed yet"
            hint="Drop a PDF, a screenshot or a recording above. Everything is processed on this machine."
          />
        ) : (
          <ul className="divide-y divide-ink-100 dark:divide-ink-800">
            {docs.map((d) => (
              <li key={d.doc_id} className="flex items-center gap-4 px-4 py-3">
                <span className="text-ink-400">{modalityIcon(d.modality, { size: 18 })}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{d.file_name}</p>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {formatBytes(d.file_size)} · {d.chunk_count} chunk(s) · {d.ingested_at.replace('T', ' ')}
                  </p>
                </div>
                <ModalityChip modality={d.modality} />
                <button
                  onClick={() => remove(d)}
                  title="Remove from index"
                  className="rounded-md p-1.5 text-ink-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950"
                >
                  <IconTrash size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
