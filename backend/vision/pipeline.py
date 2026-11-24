"""The per-frame loop shared by the CLI and the WebSocket stream."""

import time
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

from .commentary import CommentaryFeed
from .detector import Detection, Tracker
from .events import Event, EventTracker
from .source import Frame, FrameSource


@dataclass(frozen=True)
class Step:
    frame: Frame
    detections: list[Detection]
    events: list[Event]  # new this frame
    counts: Counter[str]  # objects on screen
    fps: float  # smoothed processing rate


def run(
    source: FrameSource,
    tracker: Tracker,
    events: EventTracker,
    feed: CommentaryFeed | None = None,
    realtime: bool = False,
) -> Iterator[Step]:
    fps = 0.0
    for frame in source.frames(realtime=realtime):
        tick = time.perf_counter()
        detections = tracker(frame.image)
        new_events = events.update(detections, frame.timestamp)
        counts = events.counts()
        if feed is not None:
            feed.push(frame)
        rate = 1 / max(time.perf_counter() - tick, 1e-6)
        fps = 0.9 * fps + 0.1 * rate if fps else rate
        yield Step(frame, detections, new_events, counts, fps)
