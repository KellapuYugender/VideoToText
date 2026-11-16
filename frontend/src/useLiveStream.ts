import { useCallback, useEffect, useRef, useState } from 'react'
import { liveSocketUrl } from './api'
import type {
  CommentaryMessage,
  EventMessage,
  FrameMessage,
  ServerMessage,
  SessionMessage,
} from './types'

export type Status = 'idle' | 'connecting' | 'live' | 'ended' | 'error'

const MAX_EVENTS = 30

/**
 * Owns the WebSocket for one stream at a time.
 *
 * Frames are handed to `onFrame` instead of being stored in state, so drawing
 * them doesn't re-render the whole app.
 */
export function useLiveStream(onFrame: (frame: FrameMessage, session: SessionMessage) => void) {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<SessionMessage | null>(null)
  const [lines, setLines] = useState<CommentaryMessage[]>([])
  const [events, setEvents] = useState<EventMessage[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [fps, setFps] = useState(0)
  const [position, setPosition] = useState(0)
  const [hasFrame, setHasFrame] = useState(false)

  const socketRef = useRef<WebSocket | null>(null)
  const sessionRef = useRef<SessionMessage | null>(null)
  const onFrameRef = useRef(onFrame)
  useEffect(() => {
    onFrameRef.current = onFrame
  })

  const handle = useCallback((message: ServerMessage) => {
    switch (message.type) {
      case 'session':
        sessionRef.current = message
        setSession(message)
        setStatus('live')
        break
      case 'frame':
        if (sessionRef.current) onFrameRef.current(message, sessionRef.current)
        setCounts(message.counts)
        setFps(message.fps)
        setPosition(message.timestamp)
        setHasFrame(true)
        break
      case 'event':
        setEvents((prev) => [message, ...prev].slice(0, MAX_EVENTS))
        break
      case 'commentary':
        setLines((prev) => [message, ...prev])
        break
      case 'error':
        setError(message.message)
        setStatus('error')
        break
      case 'end':
        setStatus((prev) => (prev === 'error' ? prev : 'ended'))
        socketRef.current?.close()
        break
    }
  }, [])

  const start = useCallback(
    (source: string, commentary: boolean) => {
      socketRef.current?.close()
      sessionRef.current = null
      setSession(null)
      setLines([])
      setEvents([])
      setCounts({})
      setFps(0)
      setPosition(0)
      setHasFrame(false)
      setError(null)
      setStatus('connecting')

      const socket = new WebSocket(liveSocketUrl())
      socketRef.current = socket
      socket.onopen = () => socket.send(JSON.stringify({ action: 'start', source, commentary }))
      socket.onmessage = (e) => handle(JSON.parse(e.data) as ServerMessage)
      socket.onerror = () => {
        if (socketRef.current !== socket) return
        setError('Lost connection to the backend. Is the Django server running?')
        setStatus('error')
      }
      socket.onclose = () => {
        if (socketRef.current !== socket) return
        socketRef.current = null
        setStatus((prev) => (prev === 'connecting' || prev === 'live' ? 'ended' : prev))
      }
    },
    [handle],
  )

  const stop = useCallback(() => {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action: 'stop' }))
  }, [])

  useEffect(() => () => socketRef.current?.close(), [])

  return { status, error, session, hasFrame, lines, events, counts, fps, position, start, stop }
}
