"""Saves a live stream's history (session summary + commentary lines) to the database.

Runs in worker threads, outside Django's request cycle, so connections are closed
explicitly: ``finish`` closes the stream thread's, and ``line`` closes the
commentary thread's after each write. Otherwise every stream would leak one.
"""

from collections import Counter

from django.db import connection
from django.utils import timezone

from vision.commentary import CommentaryLine as Line
from vision.pipeline import Step

from .models import CommentaryLine, Session


class SessionRecorder:
    def __init__(self, session: Session):
        self.session = session
        self._frames = 0
        self._events = 0
        self._last_timestamp = 0.0
        self._peak: Counter[str] = Counter()

    @classmethod
    def begin(cls, **fields) -> "SessionRecorder":
        return cls(Session.objects.create(**fields))

    def opened(self, width: int, height: int, fps: float) -> None:
        Session.objects.filter(pk=self.session.pk).update(width=width, height=height, fps=fps)

    def frame(self, step: Step) -> None:
        """Kept in memory; written once in ``finish`` instead of on every frame."""
        self._frames += 1
        self._events += len(step.events)
        self._last_timestamp = step.frame.timestamp
        for label, n in step.counts.items():
            if n > self._peak[label]:
                self._peak[label] = n

    def line(self, line: Line) -> None:
        try:
            CommentaryLine.objects.create(
                session_id=self.session.pk,
                timestamp=line.timestamp,
                text=line.text,
                latency=line.latency,
            )
        finally:
            connection.close()

    def finish(self, status: str, error: str = "") -> None:
        try:
            Session.objects.filter(pk=self.session.pk).update(
                status=status,
                error=error,
                ended_at=timezone.now(),
                duration=round(self._last_timestamp, 2),
                frames_processed=self._frames,
                events_count=self._events,
                peak_counts=dict(self._peak.most_common()),
            )
        finally:
            connection.close()
