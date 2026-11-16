"""Validates the video source a client asks the server to open."""

from pathlib import Path

from django.conf import settings

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
STREAM_SCHEMES = ("rtsp://", "rtmp://", "http://", "https://")


def video_dir() -> Path:
    return Path(settings.VIDEO_DIR)


def list_videos() -> list[str]:
    root = video_dir()
    if not root.is_dir():
        return []
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )


def resolve_source(raw: str) -> str | int:
    """Return something ``FrameSource`` can open, or raise ``ValueError``.

    Accepts a webcam index, a stream URL, or a video file inside ``VIDEO_DIR``;
    clients may not open arbitrary paths on the server.
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("No source given.")
    if raw.isdigit():
        if not settings.ALLOW_WEBCAM:
            raise ValueError("Webcam sources are disabled.")
        return int(raw)
    if raw.lower().startswith(STREAM_SCHEMES):
        return raw

    root = video_dir().resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Not an allowed video: {raw!r}")
    if not path.is_file():
        raise ValueError(f"Video not found: {raw!r}")
    return str(path)
