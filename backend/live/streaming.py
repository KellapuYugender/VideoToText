"""Runs the vision pipeline for one client and turns it into JSON messages."""

import base64
import threading
from collections.abc import Callable
from dataclasses import asdict

import cv2
import numpy as np
from django.conf import settings

from vision import pipeline
from vision.commentary import CommentaryFeed, CommentaryLine
from vision.events import EventTracker
from vision.source import FrameSource

from . import engines

# send(message, wait): wait=True blocks until delivered, which throttles the loop
# to what the client can take.
Send = Callable[[dict, bool], None]


def encode_jpeg(image: np.ndarray, max_width: int, quality: int) -> str:
    h, w = image.shape[:2]
    if w > max_width:
        image = cv2.resize(image, (max_width, int(h * max_width / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def stream(source: str | int, send: Send, stop: threading.Event, commentary: bool) -> None:
    """Blocking; run it in a worker thread. Returns at end of video or when ``stop`` is set.

    Box coordinates are in source pixels (see the ``session`` message), even though
    frames are sent downscaled to ``STREAM_MAX_WIDTH``.
    """
    tracker = engines.make_tracker()
    events = EventTracker()
    feed = None

    if commentary:

        def on_line(line: CommentaryLine) -> None:
            if not stop.is_set():
                send({"type": "commentary", **line.to_dict()}, False)

        feed = CommentaryFeed(engines.comment, on_line, interval=settings.COMMENTARY_INTERVAL)

    try:
        with FrameSource(source) as src:
            width, height = src.size
            session = {"width": width, "height": height, "fps": src.fps, "live": src.is_live}
            send({"type": "session", **session, "commentary": commentary}, True)

            for step in pipeline.run(src, tracker, events, feed, realtime=True):
                if stop.is_set():
                    break
                image = encode_jpeg(
                    step.frame.image, settings.STREAM_MAX_WIDTH, settings.STREAM_JPEG_QUALITY
                )
                message = {
                    "type": "frame",
                    "index": step.frame.index,
                    "timestamp": round(step.frame.timestamp, 3),
                    "fps": round(step.fps, 1),
                    "image": image,
                    "detections": [d.to_dict() for d in step.detections],
                    "counts": dict(step.counts),
                }
                send(message, True)
                for event in step.events:
                    send({"type": "event", **asdict(event)}, True)
    finally:
        if feed is not None:
            # At the natural end, let the last line finish; on stop, don't wait for it.
            feed.close(wait=not stop.is_set())
