import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { IconChat, IconSend, modalityIcon } from '../components/Icons.jsx'
import { Card, Empty, ModalityChip, Spinner } from '../components/Primitives.jsx'

const ALL_MODALITIES = ['text', 'image', 'audio']

/** Renders [1][2] citation markers as clickable superscript pills. */
function AnswerText({ text, onCite }) {
  const parts = String(text).split(/(\[\d+\])/g)
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/)
        if (!m) return <span key={i}>{part}</span>
        return (
          <button
            key={i}
            onClick={() => onCite(Number(m[1]))}
            className="mx-0.5 -translate-y-0.5 rounded bg-accent-100 px-1 align-super text-[10px] font-semibold text-accent-700 hover:bg-accent-200 dark:bg-accent-900/50 dark:text-accent-300"
          >
            {m[1]}
          </button>
        )
      })}
    </p>
  )
}

function SourceCard({ source, highlighted }) {
  return (
    <li
      id={`source-${source.rank}`}
      className={`rounded-lg border p-3 transition-colors ${
        highlighted
          ? 'border-accent-400 bg-accent-50 dark:border-accent-600 dark:bg-accent-900/20'
          : 'border-ink-200 dark:border-ink-800'
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="grid h-5 w-5 shrink-0 place-items-center rounded bg-ink-900 text-[10px] font-bold text-white dark:bg-ink-100 dark:text-ink-900">
          {source.rank}
        </span>
        <span className="text-ink-400">{modalityIcon(source.modality, { size: 14 })}</span>
        <span className="min-w-0 flex-1 truncate text-xs font-medium">{source.citation}</span>
        <ModalityChip modality={source.modality} />
      </div>

      {source.image_path && (
        <img
          src={api.imageUrl(source.image_path)}
          alt={source.citation}
          className="mt-2 max-h-40 w-full rounded border border-ink-200 object-contain dark:border-ink-800"
        />
      )}

      {source.text && (
        <p className="mt-2 line-clamp-4 text-xs leading-relaxed text-ink-600 dark:text-ink-400">
          {source.text}
        </p>
      )}

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-ink-400">
        <span>dense {source.dense_score.toFixed(3)}</span>
        <span>bm25 {source.sparse_score.toFixed(2)}</span>
        <span>rerank {source.rerank_score.toFixed(3)}</span>
        <span className="font-semibold text-ink-600 dark:text-ink-300">
          final {source.final_score.toFixed(3)}
        </span>
      </div>
    </li>
  )
}

export default function ChatWorkspace({ refreshKey }) {
  const [docs, setDocs] = useState([])
  const [selected, setSelected] = useState(null)      // null = all sources
  const [modalities, setModalities] = useState(ALL_MODALITIES)
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState([])
  const [busy, setBusy] = useState(false)
  const [highlight, setHighlight] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { api.documents().then(setDocs).catch(() => {}) }, [refreshKey])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns, busy])

  const toggleModality = (m) =>
    setModalities((cur) => (cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m]))

  const toggleDoc = (name) =>
    setSelected((cur) => {
      if (cur === null) return docs.map((d) => d.file_name).filter((n) => n !== name)
      const next = cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name]
      return next.length === docs.length ? null : next
    })

  const ask = async () => {
    const q = question.trim()
    if (!q || busy) return
    setQuestion(''); setBusy(true)
    try {
      const res = await api.query({
        query: q,
        modalities: modalities.length === ALL_MODALITIES.length ? null : modalities,
        source_files: selected,
        generate: true,
      })
      setTurns((t) => [...t, res])
    } catch (e) {
      setTurns((t) => [...t, { query: q, answer: '', sources: [], warning: e.message, timings: {} }])
    } finally {
      setBusy(false)
    }
  }

  const latest = turns[turns.length - 1]
  const activeCount = selected === null ? docs.length : selected.length

  return (
    <div className="flex h-full flex-col gap-5">
      <header>
        <h1 className="text-xl font-semibold">Chat Workspace</h1>
        <p className="mt-0.5 text-sm text-ink-500">
          One question, retrieved across documents, images and audio at once. Every claim is cited.
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[230px_minmax(0,1fr)_320px]">
        {/* -------- source selection -------- */}
        <Card title="Active sources" subtitle={`${activeCount} of ${docs.length} selected`} pad={false}
              className="hidden min-h-0 flex-col overflow-hidden xl:flex">
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {docs.length === 0 && (
              <p className="px-2 py-4 text-xs text-ink-500">Nothing indexed yet.</p>
            )}
            {docs.map((d) => {
              const on = selected === null || selected.includes(d.file_name)
              return (
                <button
                  key={d.doc_id}
                  onClick={() => toggleDoc(d.file_name)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors ${
                    on ? 'text-ink-800 dark:text-ink-200' : 'text-ink-400 line-through'
                  } hover:bg-ink-100 dark:hover:bg-ink-800`}
                >
                  <span className={`h-3 w-3 shrink-0 rounded border ${
                    on ? 'border-accent-600 bg-accent-600' : 'border-ink-300 dark:border-ink-600'
                  }`} />
                  <span className="truncate">{d.file_name}</span>
                  <span className="ml-auto shrink-0 tabular-nums text-[10px] text-ink-400">
                    {d.chunk_count}
                  </span>
                </button>
              )
            })}
          </div>
          <div className="border-t border-ink-200 p-2 dark:border-ink-800">
            <div className="flex gap-1">
              {ALL_MODALITIES.map((m) => (
                <button
                  key={m}
                  onClick={() => toggleModality(m)}
                  className={`flex-1 rounded-md border px-1.5 py-1 text-[10px] font-medium capitalize transition-colors ${
                    modalities.includes(m)
                      ? 'border-accent-500 bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300'
                      : 'border-ink-200 text-ink-400 dark:border-ink-700'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* -------- conversation -------- */}
        <div className="surface flex min-h-0 flex-col overflow-hidden">
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
            {turns.length === 0 && !busy && (
              <Empty
                icon={<IconChat size={28} />}
                title="Ask a question over your indexed sources"
                hint="Answers are generated by a local model and cite the exact file, page or timestamp they came from."
              />
            )}

            {turns.map((t, i) => (
              <div key={i} className="animate-rise space-y-3">
                <div className="flex justify-end">
                  <p className="max-w-[80%] rounded-2xl rounded-br-sm bg-accent-600 px-3.5 py-2 text-sm text-white">
                    {t.query}
                  </p>
                </div>

                <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-ink-200 bg-ink-50 px-3.5 py-3 dark:border-ink-800 dark:bg-ink-950">
                  {t.warning && (
                    <p className="mb-2 text-xs font-medium text-amber-600 dark:text-amber-400">
                      {t.warning}
                    </p>
                  )}
                  {t.answer
                    ? <AnswerText text={t.answer} onCite={setHighlight} />
                    : !t.warning && <p className="text-sm text-ink-500">No answer generated.</p>}

                  {t.sources?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5 border-t border-ink-200 pt-2.5 dark:border-ink-800">
                      {t.sources.map((s) => (
                        <button
                          key={s.chunk_id}
                          onClick={() => setHighlight(s.rank)}
                          className="chip border-ink-200 text-ink-600 hover:border-accent-400 hover:text-accent-700 dark:border-ink-700 dark:text-ink-400"
                        >
                          [{s.rank}] {s.citation}
                        </button>
                      ))}
                    </div>
                  )}

                  {t.timings?.total_ms != null && (
                    <p className="mt-2 font-mono text-[10px] text-ink-400">
                      encode {t.timings.encode_ms}ms · search {t.timings.search_ms}ms · fuse {t.timings.fuse_ms}ms
                      · rerank {t.timings.rerank_ms}ms · generate {t.timings.generate_ms}ms
                      <span className="font-semibold"> · total {t.timings.total_ms}ms</span>
                    </p>
                  )}
                </div>
              </div>
            ))}

            {busy && (
              <div className="flex items-center gap-2 text-sm text-ink-500">
                <Spinner /> Retrieving and generating locally…
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-ink-200 p-3 dark:border-ink-800">
            <div className="flex gap-2">
              <input
                className="input"
                placeholder="Ask across your documents, images and recordings…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && ask()}
                disabled={busy}
              />
              <button className="btn-primary" onClick={ask} disabled={busy || !question.trim()}>
                <IconSend size={16} /> Ask
              </button>
            </div>
          </div>
        </div>

        {/* -------- retrieved evidence -------- */}
        <Card
          title="Retrieved evidence"
          subtitle={latest?.sources?.length ? `Top ${latest.sources.length} after reranking` : 'Nothing retrieved yet'}
          pad={false}
          className="hidden min-h-0 flex-col overflow-hidden xl:flex"
        >
          <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
            {(latest?.sources || []).map((s) => (
              <SourceCard key={s.chunk_id} source={s} highlighted={highlight === s.rank} />
            ))}
            {!latest?.sources?.length && (
              <p className="px-1 py-4 text-xs text-ink-500">
                Source chunks, their provenance and their per-stage scores appear here after a query.
              </p>
            )}
          </ul>
        </Card>
      </div>
    </div>
  )
}
