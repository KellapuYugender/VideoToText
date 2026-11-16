"""Live detection demo.

    python -m vision.live --source 0                 # webcam
    python -m vision.live --source match.mp4         # file
    python -m vision.live --source match.mp4 --no-show --save out.mp4

Press q or Esc in the window to stop.
"""

import argparse
import time

import cv2

from .detector import DEFAULT_MODEL, Detection, Tracker
from .events import EventTracker
from .source import FrameSource


def color_for(track_id: int | None) -> tuple[int, int, int]:
    if track_id is None:
        return (200, 200, 200)
    return ((track_id * 67) % 255, (track_id * 131) % 255, (track_id * 199) % 255)


def draw(image, detections: list[Detection], fps: float, counts) -> None:
    for det in detections:
        x1, y1, x2, y2 = map(int, det.box)
        color = color_for(det.track_id)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        tag = f"{det.label} #{det.track_id}" if det.track_id is not None else det.label
        cv2.putText(image, tag, (x1, max(y1 - 6, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    summary = ", ".join(f"{n} {label}" for label, n in counts.most_common(4))
    cv2.putText(
        image,
        f"{fps:4.1f} FPS  {summary}",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--source", default="0", help="webcam index, file path or stream URL")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--max-frames", type=int, default=0, help="stop after N frames (0 = all)")
    parser.add_argument("--no-show", action="store_true", help="don't open a window")
    parser.add_argument("--save", help="write annotated video to this path")
    args = parser.parse_args()

    tracker = Tracker(args.model, conf=args.conf, imgsz=args.imgsz)
    events = EventTracker()
    writer = None
    fps = 0.0
    processed = 0
    started = time.perf_counter()

    with FrameSource(args.source) as source:
        print(f"Source {args.source!r}: {source.size[0]}x{source.size[1]} @ {source.fps:.1f} FPS")
        for frame in source.frames():
            tick = time.perf_counter()
            detections = tracker(frame.image)
            for event in events.update(detections, frame.timestamp):
                print(event.describe())
            elapsed = time.perf_counter() - tick
            fps = 0.9 * fps + 0.1 * (1 / elapsed) if fps else 1 / elapsed

            draw(frame.image, detections, fps, events.counts())
            if args.save:
                if writer is None:
                    h, w = frame.image.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(args.save, fourcc, source.fps, (w, h))
                writer.write(frame.image)
            if not args.no_show:
                cv2.imshow("VideoToText - live detection", frame.image)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break

            processed += 1
            if args.max_frames and processed >= args.max_frames:
                break

    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()
    total = time.perf_counter() - started
    print(f"Processed {processed} frames in {total:.1f}s ({processed / max(total, 1e-9):.1f} FPS)")


if __name__ == "__main__":
    main()
