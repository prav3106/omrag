import { useEffect, useState } from 'react'
import { api, formatSeconds } from '../lib/api.js'
import { IconLab, modalityIcon } from '../components/Icons.jsx'
import { Card, Empty, ModalityChip, Spinner } from '../components/Primitives.jsx'

/**
 * Inspect what the pipeline actually produced for a given source: the chunk
 * boundaries, the OCR / transcription output, and the provenance attached to
 * each chunk. This is the view used to debug a bad retrieval.
 */
export default function ProcessorLab({ refreshKey }) {
  const [docs, setDocs] = useState([])
  const [active, setActive] = useState(null)
  const [chunks, setChunks] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.documents().then(setDocs).catch(() => {}) }, [refreshKey])

  const open = (doc) => {
    setActive(doc); setLoading(true); setChunks([])
    api.documentChunks(doc.doc_id)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Processor Lab</h1>
        <p className="mt-0.5 text-sm text-ink-500">
          Inspect exactly what each loader extracted and how it was chunked before embedding.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card title="Sources" pad={false}>
          <ul className="max-h-[70vh] overflow-y-auto p-2">
            {docs.length === 0 && <p className="px-2 py-4 text-xs text-ink-500">Nothing indexed yet.</p>}
            {docs.map((d) => (
              <li key={d.doc_id}>
                <button
                  onClick={() => open(d)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs transition-colors ${
                    active?.doc_id === d.doc_id
                      ? 'bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300'
                      : 'hover:bg-ink-100 dark:hover:bg-ink-800'
                  }`}
                >
                  <span className="text-ink-400">{modalityIcon(d.modality, { size: 15 })}</span>
                  <span className="min-w-0 flex-1 truncate">{d.file_name}</span>
                  <span className="shrink-0 tabular-nums text-[10px] text-ink-400">{d.chunk_count}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          title={active ? active.file_name : 'Chunk inspector'}
          subtitle={active ? `${chunks.length} chunk(s) produced by the ingestion pipeline` : 'Select a source on the left'}
          pad={false}
        >
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-ink-500">
              <Spinner /> Loading chunks…
            </div>
          ) : !active ? (
            <Empty
              icon={<IconLab size={28} />}
              title="No source selected"
              hint="Pick an ingested file to see its extracted text, chunk boundaries and provenance metadata."
            />
          ) : (
            <ul className="max-h-[70vh] space-y-3 overflow-y-auto p-4">
              {chunks.map((c, i) => (
                <li key={c.chunk_id} className="rounded-lg border border-ink-200 p-3 dark:border-ink-800">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="grid h-5 w-5 place-items-center rounded bg-ink-100 text-[10px] font-bold text-ink-600 dark:bg-ink-800 dark:text-ink-300">
                      {i + 1}
                    </span>
                    <ModalityChip modality={c.modality} />
                    {c.page_number != null && (
                      <span className="text-[11px] text-ink-500">page {c.page_number}</span>
                    )}
                    {c.start_time != null && (
                      <span className="text-[11px] text-ink-500">
                        {formatSeconds(c.start_time)} – {formatSeconds(c.end_time)}
                      </span>
                    )}
                    <span className="ml-auto font-mono text-[10px] text-ink-400">
                      {c.chunk_text ? `${c.chunk_text.split(/\s+/).length} tokens` : 'no text'}
                    </span>
                  </div>

                  {c.image_path && (
                    <img
                      src={api.imageUrl(c.image_path)}
                      alt=""
                      className="mt-2 max-h-48 rounded border border-ink-200 object-contain dark:border-ink-800"
                    />
                  )}
                  {c.chunk_text && (
                    <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-ink-600 dark:text-ink-400">
                      {c.chunk_text}
                    </p>
                  )}
                  <p className="mt-2 break-all font-mono text-[10px] text-ink-400">
                    id {c.chunk_id}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
