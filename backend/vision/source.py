"""Frame sources: video files, webcams and network streams via OpenCV."""

import time
from collections.abc import Iterator
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class Frame:
    index: int
    timestamp: float  # seconds since the start of the source
    image: np.ndarray  # BGR


class FrameSource:
    """Wraps ``cv2.VideoCapture``.

    ``source`` may be a webcam index ("0"), a file path, or an RTSP/HTTP URL.
    """

    def __init__(self, source: str | int):
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise OSError(f"Could not open video source: {source!r}")
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps and fps > 0 else 30.0
        self.is_live = isinstance(source, int) or str(source).startswith(("rtsp://", "http"))

    @property
    def size(self) -> tuple[int, int]:
        return (
            int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def frames(self, realtime: bool = False) -> Iterator[Frame]:
        """Yield frames in order.

        With ``realtime``, a file is paced like a live feed: frames are skipped when the
        consumer falls behind the wall clock, and delivery waits when it is ahead.
        The clock starts once the first frame has been consumed, so slow model
        warm-up on that frame doesn't skip the start of the video.
        """
        index = 0
        started: float | None = None
        while True:
            if realtime and not self.is_live and started is not None:
                elapsed = time.perf_counter() - started
                behind = int(elapsed * self.fps) - index
                for _ in range(behind):
                    if not self.cap.grab():
                        return
                    index += 1
                wait = index / self.fps - elapsed
                if wait > 0:
                    time.sleep(wait)
            ok, image = self.cap.read()
            if not ok:
                break
            pos_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp = pos_ms / 1000 if pos_ms > 0 else index / self.fps
            yield Frame(index=index, timestamp=timestamp, image=image)
            index += 1
            if started is None:
                started = time.perf_counter() - index / self.fps

    def close(self) -> None:
        self.cap.release()

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
