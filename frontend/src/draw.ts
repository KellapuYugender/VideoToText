import type { Detection } from './types'

export function colorFor(trackId: number | null): string {
  return trackId === null ? 'hsl(0 0% 80%)' : `hsl(${(trackId * 67) % 360} 85% 60%)`
}

/**
 * Draws the frame and its boxes. Boxes are in source pixels, while the image may
 * have been downscaled for streaming, so they are scaled to the canvas.
 */
export function drawFrame(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  detections: Detection[],
  sourceWidth: number,
  showBoxes: boolean,
) {
  if (canvas.width !== image.naturalWidth || canvas.height !== image.naturalHeight) {
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.drawImage(image, 0, 0)
  if (!showBoxes) return

  const scale = canvas.width / sourceWidth
  const font = Math.max(12, Math.round(canvas.width / 55))
  ctx.font = `600 ${font}px system-ui, sans-serif`
  ctx.lineWidth = Math.max(2, canvas.width / 400)
  ctx.textBaseline = 'top'

  for (const det of detections) {
    const [x1, y1, x2, y2] = det.box.map((v) => v * scale)
    const color = colorFor(det.track_id)
    ctx.strokeStyle = color
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    const tag = det.track_id === null ? det.label : `${det.label} #${det.track_id}`
    const pad = 4
    const width = ctx.measureText(tag).width + pad * 2
    const height = font + pad * 2
    const top = y1 - height >= 0 ? y1 - height : y1
    ctx.fillStyle = color
    ctx.fillRect(x1, top, width, height)
    ctx.fillStyle = '#0b0f17'
    ctx.fillText(tag, x1 + pad, top + pad)
  }
}
