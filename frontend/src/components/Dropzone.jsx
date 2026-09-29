import { useRef, useState } from 'react'
import { IconUpload } from './Icons.jsx'
import { Spinner } from './Primitives.jsx'

const ACCEPT = '.pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.wav,.mp3,.m4a,.flac,.ogg'

export default function Dropzone({ onFiles, busy }) {
  const [over, setOver] = useState(false)
  const input = useRef(null)

  const handle = (fileList) => {
    const files = Array.from(fileList || [])
    if (files.length) onFiles(files)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); handle(e.dataTransfer.files) }}
      onClick={() => !busy && input.current?.click()}
      className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        over
          ? 'border-accent-500 bg-accent-50 dark:bg-accent-900/20'
          : 'border-ink-200 hover:border-ink-300 dark:border-ink-700 dark:hover:border-ink-600'
      } ${busy ? 'pointer-events-none opacity-60' : ''}`}
    >
      <input
        ref={input} type="file" multiple accept={ACCEPT} className="hidden"
        onChange={(e) => { handle(e.target.files); e.target.value = '' }}
      />
      <div className="flex flex-col items-center gap-2">
        <span className="text-ink-400">{busy ? <Spinner size={22} /> : <IconUpload size={22} />}</span>
        <p className="text-sm font-medium">
          {busy ? 'Processing locally…' : 'Drop files here, or click to browse'}
        </p>
        <p className="text-xs text-ink-500">
          PDF · DOCX · TXT · PNG / JPG · WAV / MP3 — parsed, transcribed and embedded on this machine
        </p>
      </div>
    </div>
  )
}
