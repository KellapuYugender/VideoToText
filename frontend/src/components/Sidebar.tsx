import { formatTime } from '../api'
import { colorFor } from '../draw'
import type { CommentaryMessage, EventMessage } from '../types'

type Props = {
  lines: CommentaryMessage[]
  events: EventMessage[]
  counts: Record<string, number>
  waitingForCommentary: boolean
}

export function Sidebar({ lines, events, counts, waitingForCommentary }: Props) {
  const onScreen = Object.entries(counts).sort((a, b) => b[1] - a[1])

  return (
    <aside className="sidebar">
      <section className="panel commentary">
        <h2>Commentary</h2>
        {lines.length === 0 ? (
          <p className="empty">
            {waitingForCommentary
              ? 'Warming up the commentator… the first line can take 20 s or more on a CPU.'
              : 'Commentary appears here once a stream starts.'}
          </p>
        ) : (
          <ol className="lines" aria-live="polite">
            {lines.map((line) => (
              <li key={`${line.timestamp}-${line.text}`}>
                <time>{formatTime(line.timestamp)}</time>
                <p>{line.text}</p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="panel">
        <h2>On screen</h2>
        {onScreen.length === 0 ? (
          <p className="empty">Nothing detected yet.</p>
        ) : (
          <ul className="chips">
            {onScreen.map(([label, n]) => (
              <li key={label}>
                <strong>{n}</strong> {label}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel events">
        <h2>Events</h2>
        {events.length === 0 ? (
          <p className="empty">Objects entering and leaving show up here.</p>
        ) : (
          <ul>
            {events.map((e) => (
              <li key={`${e.timestamp}-${e.kind}-${e.track_id}`}>
                <time>{formatTime(e.timestamp)}</time>
                <span className="dot" style={{ background: colorFor(e.track_id) }} />
                {e.label} #{e.track_id} <span className={`kind ${e.kind}`}>{e.kind}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  )
}
