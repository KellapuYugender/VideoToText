"""Model instances used by live streams.

YOLO trackers hold per-stream track IDs, so each stream gets its own. The VLM is
large, so one instance is loaded on first use and shared, one request at a time.
"""

import threading
from functools import cache

import numpy as np
from django.conf import settings

from vision.commentary import Commentator
from vision.detector import Tracker

_vlm_lock = threading.Lock()


def make_tracker() -> Tracker:
    return Tracker(settings.YOLO_MODEL, conf=settings.YOLO_CONF, device=settings.TORCH_DEVICE)


@cache
def _commentator() -> Commentator:
    return Commentator(settings.VLM_MODEL, device=settings.TORCH_DEVICE)


def comment(images: list[np.ndarray], prompt: str) -> str:
    with _vlm_lock:
        return _commentator()(images, prompt)
