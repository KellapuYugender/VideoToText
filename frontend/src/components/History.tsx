import { useEffect, useState } from 'react'
import { deleteSession, fetchSession, fetchSessions, formatTime } from '../api'
import type { SessionDetail, SessionStatus, SessionSummary } from '../types'

const KIND_LABEL = { file: 'Video', webcam: 'Webcam', stream: 'Stream' } as const

const STATUS_LABEL: Record<SessionStatus, string> = {
  running: 'Running',
  completed: 'Completed',
  stopped: 'Stopped',
  failed: 'Failed',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function transcript(session: SessionDetail): string {
  const header = `${session.source} · ${formatDate(session.started_at)}`
  const body = session.lines.map((l) => `[${formatTime(l.timestamp)}] ${l.text}`)
  return [header, '', ...body].join('\n')
}

type Props = { initialId: number | null }

export function History({ initialId }: Props) {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(initialId)
  const [detail, setDetail] = useState<SessionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchSessions()
      .then((page) => {
        setSessions(page.results)
        setNext(page.next)
        setSelectedId((prev) => prev ?? page.results[0]?.id ?? null)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedId === null) return
    let cancelled = false
    fetchSession(selectedId)
      .then((d) => !cancelled && setDetail(d))
      .catch((e: Error) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const loadMore = async () => {
    if (!next) return
    try {
      const page = await fetchSessions(next)
      setSessions((prev) => [...prev, ...page.results])
      setNext(page.next)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const remove = async (session: SessionDetail) => {
    if (!window.confirm(`Delete the session for ${session.source}? This can't be undone.`)) return
    try {
      await deleteSession(session.id)
      const rest = sessions.filter((s) => s.id !== session.id)
      setSessions(rest)
      setDetail(null)
      setSelectedId(rest[0]?.id ?? null)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const copy = async (session: SessionDetail) => {
    await navigator.clipboard.writeText(transcript(session))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const download = (session: SessionDetail) => {
    const blob = new Blob([transcript(session)], { type: 'text/plain' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `commentary-${session.id}.txt`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (loading) return <p className="empty history-empty">Loading sessions…</p>
  if (sessions.length === 0) {
    return (
      <div className="panel history-empty">
        {error ? (
          <p role="alert">{error}</p>
        ) : (
          <p className="empty">
            No saved sessions yet. Every live stream is saved here automatically.
          </p>
        )}
      </div>
    )
  }

  const shown = detail && detail.id === selectedId ? detail : null

  return (
    <div className="history">
      <nav className="session-list" aria-label="Saved sessions">
        <ul>
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className={s.id === selectedId ? 'session-card active' : 'session-card'}
                onClick={() => setSelectedId(s.id)}
                aria-current={s.id === selectedId}
              >
                <span className="session-title">
                  <strong>{s.kind === 'webcam' ? 'Webcam' : s.source}</strong>
                  <span className={`badge ${s.status}`}>{STATUS_LABEL[s.status]}</span>
                </span>
                <span className="session-meta">
                  {formatDate(s.started_at)} · {formatTime(s.duration)} · {s.lines_count}{' '}
                  {s.lines_count === 1 ? 'line' : 'lines'}
                </span>
                {s.preview && <span className="session-preview">“{s.preview}”</span>}
              </button>
            </li>
          ))}
        </ul>
        {next && (
          <button type="button" className="secondary load-more" onClick={loadMore}>
            Load more
          </button>
        )}
      </nav>

      <section className="panel session-detail" aria-live="polite">
        {error && (
          <p className="banner" role="alert">
            {error}
          </p>
        )}
        {!shown ? (
          <p className="empty">Loading…</p>
        ) : (
          <>
            <header className="detail-head">
              <div>
                <h2 className="detail-title">
                  {shown.kind === 'webcam' ? 'Webcam' : shown.source}
                </h2>
                <p className="session-meta">
                  {KIND_LABEL[shown.kind]} · {formatDate(shown.started_at)} ·{' '}
                  <span className={`badge ${shown.status}`}>{STATUS_LABEL[shown.status]}</span>
                </p>
              </div>
              <div className="detail-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => copy(shown)}
                  disabled={!shown.lines.length}
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => download(shown)}
                  disabled={!shown.lines.length}
                >
                  Download .txt
                </button>
                <button type="button" className="danger" onClick={() => remove(shown)}>
                  Delete
                </button>
              </div>
            </header>

            {shown.error && <p className="banner">{shown.error}</p>}

            <dl className="stats">
              <div>
                <dt>Duration</dt>
                <dd>{formatTime(shown.duration)}</dd>
              </div>
              <div>
                <dt>Frames</dt>
                <dd>{shown.frames_processed.toLocaleString()}</dd>
              </div>
              <div>
                <dt>Events</dt>
                <dd>{shown.events_count}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>{shown.width ? `${shown.width}×${shown.height}` : '—'}</dd>
              </div>
            </dl>

            {Object.keys(shown.peak_counts).length > 0 && (
              <>
                <h3 className="subhead">Most on screen at once</h3>
                <ul className="chips">
                  {Object.entries(shown.peak_counts).map(([label, n]) => (
                    <li key={label}>
                      <strong>{n}</strong> {label}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <h3 className="subhead">Transcript</h3>
            {shown.lines.length === 0 ? (
              <p className="empty">
                {shown.commentary_enabled
                  ? 'The stream ended before the first commentary line.'
                  : 'Commentary was turned off for this session.'}
              </p>
            ) : (
              <ol className="lines transcript">
                {shown.lines.map((line) => (
                  <li key={line.id}>
                    <time>{formatTime(line.timestamp)}</time>
                    <p>{line.text}</p>
                  </li>
                ))}
              </ol>
            )}

            <p className="models">
              {shown.yolo_model}
              {shown.vlm_model && ` · ${shown.vlm_model}`}
            </p>
          </>
        )}
      </section>
    </div>
  )
}
