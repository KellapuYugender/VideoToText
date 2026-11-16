from vision.detector import Detection
from vision.events import EventTracker


def det(track_id, label="person"):
    return Detection(track_id=track_id, label=label, confidence=0.9, box=(0, 0, 10, 10))


def test_enter_and_leave_events():
    tracker = EventTracker(lost_after=1.0)

    events = tracker.update([det(1), det(2, "ball")], timestamp=0.0)
    assert [(e.kind, e.track_id) for e in events] == [("entered", 1), ("entered", 2)]

    assert tracker.update([det(1), det(2, "ball")], timestamp=0.5) == []

    events = tracker.update([det(1)], timestamp=2.0)
    assert [(e.kind, e.track_id, e.label) for e in events] == [("left", 2, "ball")]
    assert tracker.counts() == {"person": 1}


def test_short_occlusion_is_not_a_leave():
    tracker = EventTracker(lost_after=1.5)
    tracker.update([det(7)], timestamp=0.0)
    assert tracker.update([], timestamp=1.0) == []
    assert tracker.update([det(7)], timestamp=1.2) == []


def test_untracked_detections_are_ignored():
    tracker = EventTracker()
    assert tracker.update([det(None)], timestamp=0.0) == []
    assert tracker.counts() == {}
