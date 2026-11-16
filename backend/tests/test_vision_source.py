import time

import cv2
import numpy as np
import pytest

from vision.source import FrameSource


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 20, (32, 32))
    for i in range(40):  # 2 s at 20 FPS
        writer.write(np.full((32, 32, 3), i * 5, np.uint8))
    writer.release()
    return path


def test_all_frames_without_realtime(clip):
    with FrameSource(str(clip)) as source:
        assert [f.index for f in source.frames()] == list(range(40))


def test_realtime_does_not_skip_during_first_frame_warmup(clip):
    with FrameSource(str(clip)) as source:
        frames = source.frames(realtime=True)
        assert next(frames).index == 0
        time.sleep(0.5)  # like a model loading on the first frame
        assert next(frames).index == 1


def test_realtime_skips_frames_when_consumer_falls_behind(clip):
    with FrameSource(str(clip)) as source:
        frames = source.frames(realtime=True)
        next(frames)
        next(frames)
        time.sleep(0.5)  # 10 frames' worth at 20 FPS
        assert next(frames).index >= 8
