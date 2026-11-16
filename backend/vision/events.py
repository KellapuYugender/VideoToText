"""Turns per-frame tracks into scene events (object entered / left).

These events are cheap facts the commentary model can lean on, e.g.
"person #3 entered at 12.4s".
"""

from collections import Counter
from dataclasses import dataclass

from .detector import Detection


@dataclass(frozen=True)
class Event:
    kind: str  # "entered" | "left"
    track_id: int
    label: str
    timestamp: float

    def describe(self) -> str:
        return f"{self.label} #{self.track_id} {self.kind} at {self.timestamp:.1f}s"


class EventTracker:
    """Emits an event when a track first appears or has been gone for ``lost_after`` seconds."""

    def __init__(self, lost_after: float = 1.5):
        self.lost_after = lost_after
        self._active: dict[int, tuple[str, float]] = {}  # track_id -> (label, last_seen)

    def update(self, detections: list[Detection], timestamp: float) -> list[Event]:
        events = []
        for det in detections:
            if det.track_id is None:
                continue
            if det.track_id not in self._active:
                events.append(Event("entered", det.track_id, det.label, timestamp))
            self._active[det.track_id] = (det.label, timestamp)

        for track_id, (label, last_seen) in list(self._active.items()):
            if timestamp - last_seen > self.lost_after:
                events.append(Event("left", track_id, label, timestamp))
                del self._active[track_id]
        return events

    def counts(self) -> Counter[str]:
        """Objects currently on screen, by label."""
        return Counter(label for label, _ in self._active.values())
