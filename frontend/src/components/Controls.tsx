import { useEffect, useRef, useState } from 'react'
import { fetchSources, uploadVideo } from '../api'
import type { Sources } from '../types'

const WEBCAM = '0'
const URL_OPTION = '__url__'

type Props = {
  running: boolean
  speechSupported: boolean
  options: { commentary: boolean; voice: boolean; boxes: boolean; sport: string }
  onOptionsChange: (options: Props['options']) => void
  onStart: (source: string) => void
  onStop: () => void
}

export function Controls({
  running,
  speechSupported,
  options,
  onOptionsChange,
  onStart,
  onStop,
}: Props) {
  const [sources, setSources] = useState<Sources>({ videos: [], webcam: false })
  const [choice, setChoice] = useState('')
  const [url, setUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const load = async (select?: string) => {
    try {
      const next = await fetchSources()
      setSources(next)
      setChoice((prev) => select ?? (prev || next.videos[0] || (next.webcam ? WEBCAM : '')))
      setMessage(null)
    } catch {
      setMessage('Could not reach the backend. Start it with: manage.py runserver')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const upload = async (file: File) => {
    setUploading(true)
    setMessage(`Uploading ${file.name}…`)
    try {
      const name = await uploadVideo(file)
      await load(name)
      setMessage(`Uploaded ${name}`)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const source = choice === URL_OPTION ? url.trim() : choice
  const toggle = (key: 'commentary' | 'voice' | 'boxes') =>
    onOptionsChange({ ...options, [key]: !options[key] })

  return (
    <section className="controls" aria-label="Stream controls">
      <div className="control-row">
        <label className="field">
          <span>Source</span>
          <select value={choice} onChange={(e) => setChoice(e.target.value)} disabled={running}>
            {sources.videos.length > 0 && (
              <optgroup label="Videos">
                {sources.videos.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label="Live">
              {sources.webcam && <option value={WEBCAM}>Webcam</option>}
              <option value={URL_OPTION}>Stream URL…</option>
            </optgroup>
          </select>
        </label>

        {choice === URL_OPTION && (
          <label className="field grow">
            <span>URL</span>
            <input
              type="url"
              placeholder="rtsp://… or https://…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={running}
            />
          </label>
        )}

        <label
          className="field sport"
          title="Leave empty for plain narration of any video; enter a sport (e.g. cricket) for sports commentary"
        >
          <span>Sport (optional)</span>
          <input
            type="text"
            placeholder="e.g. cricket"
            maxLength={40}
            value={options.sport}
            onChange={(e) => onOptionsChange({ ...options, sport: e.target.value })}
            disabled={running || !options.commentary}
          />
        </label>

        <input
          ref={fileInput}
          type="file"
          accept="video/*"
          hidden
          onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])}
        />
        <button
          type="button"
          className="secondary"
          onClick={() => fileInput.current?.click()}
          disabled={running || uploading}
        >
          {uploading ? 'Uploading…' : 'Upload video'}
        </button>

        {running ? (
          <button type="button" className="stop" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button
            type="button"
            className="start"
            onClick={() => onStart(source)}
            disabled={!source || uploading}
          >
            Start
          </button>
        )}
      </div>

      <div className="control-row toggles">
        <label>
          <input
            type="checkbox"
            checked={options.commentary}
            onChange={() => toggle('commentary')}
            disabled={running}
          />
          Commentary
        </label>
        <label title={speechSupported ? '' : 'This browser has no text-to-speech'}>
          <input
            type="checkbox"
            checked={options.voice}
            onChange={() => toggle('voice')}
            disabled={!speechSupported || !options.commentary}
          />
          Voice
        </label>
        <label>
          <input type="checkbox" checked={options.boxes} onChange={() => toggle('boxes')} />
          Boxes
        </label>
        {message && <span className="hint">{message}</span>}
      </div>
    </section>
  )
}
