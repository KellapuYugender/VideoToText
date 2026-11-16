"""YOLO11 detection with ByteTrack IDs, returned as plain dataclasses."""

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO

# Downloaded on first use into backend/weights/ (gitignored).
DEFAULT_MODEL = str(Path(__file__).resolve().parent.parent / "weights" / "yolo11n.pt")


@dataclass(frozen=True)
class Detection:
    track_id: int | None
    label: str
    confidence: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def to_dict(self) -> dict:
        return asdict(self)


class Tracker:
    """Runs YOLO + ByteTrack on consecutive frames of one stream.

    Track IDs persist across calls, so use one instance per video source.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        conf: float = 0.35,
        imgsz: int = 640,
        classes: list[int] | None = None,
        device: str = "cpu",
    ):
        self.model = YOLO(model)
        self.conf = conf
        self.imgsz = imgsz
        self.classes = classes
        self.device = device

    @property
    def names(self) -> dict[int, str]:
        return self.model.names

    def __call__(self, image: np.ndarray) -> list[Detection]:
        result = self.model.track(
            image,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.conf,
            imgsz=self.imgsz,
            classes=self.classes,
            device=self.device,
            verbose=False,
        )[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        ids = boxes.id.int().tolist() if boxes.id is not None else [None] * len(boxes)
        return [
            Detection(
                track_id=tid,
                label=self.names[int(cls)],
                confidence=round(float(conf), 3),
                box=tuple(round(v, 1) for v in xyxy),
            )
            for tid, cls, conf, xyxy in zip(
                ids, boxes.cls.tolist(), boxes.conf.tolist(), boxes.xyxy.tolist(), strict=True
            )
        ]
