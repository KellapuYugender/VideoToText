import base64

import cv2
import numpy as np
import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from live import engines
from live.routing import websocket_urlpatterns
from live.sources import resolve_source
from vision.detector import Detection


@pytest.fixture
def video_dir(tmp_path, settings):
    settings.VIDEO_DIR = tmp_path
    settings.COMMENTARY_INTERVAL = 0.2
    writer = cv2.VideoWriter(
        str(tmp_path / "clip.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 20, (64, 48)
    )
    for i in range(20):
        writer.write(np.full((48, 64, 3), i * 10, np.uint8))
    writer.release()
    return tmp_path


@pytest.fixture
def fake_models(monkeypatch):
    """Person #1 is visible for the first 5 frames; the VLM always says the same thing."""

    class FakeTracker:
        calls = 0

        def __call__(self, image):
            self.calls += 1
            if self.calls <= 5:
                return [Detection(1, "person", 0.9, (1.0, 2.0, 30.0, 40.0))]
            return []

    monkeypatch.setattr(engines, "make_tracker", FakeTracker)
    monkeypatch.setattr(engines, "comment", lambda images, prompt: "What a moment!")


def test_resolve_source_accepts_files_webcams_and_urls(video_dir):
    assert resolve_source("clip.mp4") == str((video_dir / "clip.mp4").resolve())
    assert resolve_source("0") == 0
    assert resolve_source("rtsp://cam/stream") == "rtsp://cam/stream"


@pytest.mark.parametrize("raw", ["", "../secret.mp4", "missing.mp4", "notes.txt", "C:/x.mp4"])
def test_resolve_source_rejects_unsafe_or_missing(video_dir, raw):
    with pytest.raises(ValueError):
        resolve_source(raw)


def test_resolve_source_webcam_can_be_disabled(video_dir, settings):
    settings.ALLOW_WEBCAM = False
    with pytest.raises(ValueError):
        resolve_source("0")


def test_sources_endpoint_lists_videos(client, video_dir):
    response = client.get(reverse("live-sources"))
    assert response.json() == {"videos": ["clip.mp4"], "webcam": True}


async def receive_until_end(communicator, limit=200):
    messages = []
    for _ in range(limit):
        message = await communicator.receive_json_from(timeout=10)
        messages.append(message)
        if message["type"] == "end":
            return messages
    raise AssertionError("stream never ended")


@pytest.mark.asyncio
async def test_stream_sends_session_frames_events_commentary(video_dir, fake_models):
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/live/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"action": "start", "source": "clip.mp4"})
    messages = await receive_until_end(communicator)
    await communicator.disconnect()

    by_type = {}
    for m in messages:
        by_type.setdefault(m["type"], []).append(m)

    session = by_type["session"][0]
    assert (session["width"], session["height"]) == (64, 48)
    assert session["commentary"] is True

    frames = by_type["frame"]
    assert frames, "no frames streamed"
    first = frames[0]
    assert first["detections"][0]["label"] == "person"
    assert first["counts"] == {"person": 1}
    assert base64.b64decode(first["image"])[:2] == b"\xff\xd8"  # JPEG magic

    assert [e["kind"] for e in by_type["event"]][:1] == ["entered"]
    assert by_type["commentary"][0]["text"] == "What a moment!"
    assert "error" not in by_type


@pytest.mark.asyncio
async def test_stream_rejects_bad_source_and_unknown_action(video_dir, fake_models):
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/live/")
    await communicator.connect()

    await communicator.send_json_to({"action": "start", "source": "../../etc/passwd"})
    assert (await communicator.receive_json_from())["type"] == "error"

    await communicator.send_json_to({"action": "dance"})
    assert (await communicator.receive_json_from())["type"] == "error"
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_stop_ends_stream_early(video_dir, fake_models):
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/live/")
    await communicator.connect()
    await communicator.send_json_to({"action": "start", "source": "clip.mp4", "commentary": False})
    assert (await communicator.receive_json_from(timeout=10))["type"] == "session"

    await communicator.send_json_to({"action": "stop"})
    messages = await receive_until_end(communicator)
    await communicator.disconnect()

    assert len([m for m in messages if m["type"] == "frame"]) < 20


def test_upload_saves_video_without_overwriting(client, video_dir):
    url = reverse("live-upload")
    first = client.post(url, {"file": SimpleUploadedFile("my match.mp4", b"data")})
    second = client.post(url, {"file": SimpleUploadedFile("my match.mp4", b"more")})

    assert first.status_code == 201 and first.json() == {"name": "my_match.mp4"}
    assert second.status_code == 201 and second.json()["name"] != "my_match.mp4"
    assert (video_dir / "my_match.mp4").read_bytes() == b"data"


def test_upload_rejects_other_types_and_large_files(client, video_dir, settings):
    url = reverse("live-upload")
    bad_type = client.post(url, {"file": SimpleUploadedFile("evil.py", b"print()")})
    assert bad_type.status_code == 400
    assert client.post(url, {}).status_code == 400

    settings.MAX_UPLOAD_MB = 0
    too_big = client.post(url, {"file": SimpleUploadedFile("big.mp4", b"x")})
    assert too_big.status_code == 413
    assert not (video_dir / "evil.py").exists()
