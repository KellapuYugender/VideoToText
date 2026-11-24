import { useCallback, useEffect, useRef, useState } from 'react'
import { formatTime } from './api'
import { Controls } from './components/Controls'
import { History } from './components/History'
import { Sidebar } from './components/Sidebar'
import { drawFrame } from './draw'
import type { FrameMessage, SessionMessage } from './types'
import { useLiveStream, type Status } from './useLiveStream'
import { useSpeech } from './useSpeech'

const STATUS_LABEL: Record<Status, string> = {
  idle: 'Idle',
  connecting: 'Connecting',
  live: 'Live',
  ended: 'Ended',
  error: 'Error',
}

export default function App() {
  const [options, setOptions] = useState({
    commentary: true,
    voice: true,
    boxes: true,
    sport: '',
  })
  const [view, setView] = useState<'live' | 'history'>('live')
  const [historyId, setHistoryId] = useState<number | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imageRef = useRef<HTMLImageElement | null>(null)
  const latestRef = useRef<{ frame: FrameMessage; session: SessionMessage } | null>(null)
  const showBoxesRef = useRef(options.boxes)

  const redraw = useCallback(() => {
    const canvas = canvasRef.current
    const image = imageRef.current
    const latest = latestRef.current
    if (!canvas || !image || !latest || !image.complete || image.naturalWidth === 0) return
    drawFrame(canvas, image, latest.frame.detections, latest.session.width, showBoxesRef.current)
  }, [])

  const onFrame = useCallback(
    (frame: FrameMessage, session: SessionMessage) => {
      latestRef.current = { frame, session }
      if (!imageRef.current) {
        imageRef.current = new Image()
        imageRef.current.onload = redraw
      }
      // A newer frame replaces one still decoding, so the view never lags behind.
      imageRef.current.src = `data:image/jpeg;base64,${frame.image}`
    },
    [redraw],
  )

  useEffect(() => {
    showBoxesRef.current = options.boxes
    redraw()
  }, [options.boxes, redraw])

  const stream = useLiveStream(onFrame)
  const { speak, supported: speechSupported } = useSpeech(options.voice && options.commentary)

  const latestLine = stream.lines[0]
  useEffect(() => {
    if (latestLine) speak(latestLine.text)
  }, [latestLine, speak])

  const running = stream.status === 'connecting' || stream.status === 'live'
  const hasPicture = stream.hasFrame

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden>
            ▶
          </span>
          <h1>VideoToText</h1>
          <span className="tagline">live AI commentary</span>
        </div>
        <nav className="tabs" aria-label="Views">
          <button
            type="button"
            className={view === 'live' ? 'tab active' : 'tab'}
            aria-current={view === 'live'}
            onClick={() => setView('live')}
          >
            Live
          </button>
          <button
            type="button"
            className={view === 'history' ? 'tab active' : 'tab'}
            aria-current={view === 'history'}
            onClick={() => {
              setHistoryId(null)
              setView('history')
            }}
          >
            History
          </button>
        </nav>
        <div className={`status ${stream.status}`}>
          <span className="pulse" aria-hidden />
          {STATUS_LABEL[stream.status]}
          {stream.status === 'live' && (
            <span className="meta">
              {formatTime(stream.position)} · {stream.fps.toFixed(1)} FPS
            </span>
          )}
        </div>
      </header>

      {view === 'history' && <History initialId={historyId} />}

      {/* Kept mounted while hidden so a running stream survives a look at History. */}
      <div className="live-view" hidden={view !== 'live'}>
        <Controls
          running={running}
          speechSupported={speechSupported}
          options={options}
          onOptionsChange={setOptions}
          onStart={(source) => stream.start(source, options.commentary, options.sport.trim())}
          onStop={stream.stop}
        />

        {stream.error && (
          <div className="banner" role="alert">
            {stream.error}
          </div>
        )}

        {stream.status === 'ended' && stream.session && (
          <div className="notice">
            Session saved.
            <button
              type="button"
              className="link"
              onClick={() => {
                setHistoryId(stream.session?.session_id ?? null)
                setView('history')
              }}
            >
              View transcript
            </button>
          </div>
        )}

        <main className="layout">
          <section className="stage">
            <canvas ref={canvasRef} className={hasPicture ? '' : 'hidden'} />
            {!hasPicture && (
              <div className="placeholder">
                {running
                  ? 'Loading models and opening the source…'
                  : 'Pick a video or the webcam, then press Start.'}
              </div>
            )}
            {latestLine && hasPicture && (
              <div className="caption" key={latestLine.timestamp}>
                {latestLine.text}
              </div>
            )}
          </section>

          <Sidebar
            lines={stream.lines}
            events={stream.events}
            counts={stream.counts}
            waitingForCommentary={running && options.commentary}
          />
        </main>
      </div>
    </div>
  )
}
