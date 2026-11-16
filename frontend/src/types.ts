// Messages from the backend WebSocket (backend/live/streaming.py).

export type Detection = {
  track_id: number | null
  label: string
  confidence: number
  box: [number, number, number, number] // x1, y1, x2, y2 in source pixels
}

export type SessionMessage = {
  type: 'session'
  session_id: number // saved session, see /api/sessions/
  width: number
  height: number
  fps: number
  live: boolean
  commentary: boolean
}

export type FrameMessage = {
  type: 'frame'
  index: number
  timestamp: number
  fps: number
  image: string // base64 JPEG, possibly downscaled from width x height
  detections: Detection[]
  counts: Record<string, number>
}

export type EventMessage = {
  type: 'event'
  kind: 'entered' | 'left'
  track_id: number
  label: string
  timestamp: number
}

export type CommentaryMessage = {
  type: 'commentary'
  timestamp: number
  text: string
  latency: number
}

export type ServerMessage =
  | SessionMessage
  | FrameMessage
  | EventMessage
  | CommentaryMessage
  | { type: 'error'; message: string }
  | { type: 'end' }

export type Sources = { videos: string[]; webcam: boolean }

// Saved sessions (backend/live/serializers.py).

export type SessionStatus = 'running' | 'completed' | 'stopped' | 'failed'

export type SessionSummary = {
  id: number
  source: string
  kind: 'file' | 'webcam' | 'stream'
  status: SessionStatus
  error: string
  started_at: string
  ended_at: string | null
  width: number | null
  height: number | null
  fps: number | null
  duration: number
  frames_processed: number
  events_count: number
  peak_counts: Record<string, number>
  commentary_enabled: boolean
  yolo_model: string
  vlm_model: string
  lines_count: number
  preview: string
}

export type SavedLine = { id: number; timestamp: number; text: string; latency: number }

export type SessionDetail = SessionSummary & { lines: SavedLine[] }

export type Page<T> = { count: number; next: string | null; results: T[] }
