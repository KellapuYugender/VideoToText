import type { Sources } from './types'

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.error === 'string') return body.error
  } catch {
    // not JSON
  }
  return `Request failed (${response.status})`
}

export async function fetchSources(): Promise<Sources> {
  const response = await fetch('/api/live/sources/')
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

/** Uploads a video and returns the name to stream it by. */
export async function uploadVideo(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/live/videos/', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return (await response.json()).name
}

export function liveSocketUrl(): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${location.host}/ws/live/`
}

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
