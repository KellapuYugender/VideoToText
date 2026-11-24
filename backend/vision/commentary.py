"""Live commentary: a small VLM narrates recent frames, grounded by tracker facts.

The detection loop calls ``CommentaryFeed.push`` for every frame; the VLM runs on a
background thread so slow generation never stalls detection.
"""

import logging
import queue
import re
import threading
import time
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .events import Event
from .source import Frame

log = logging.getLogger(__name__)

DEFAULT_VLM = "HuggingFaceTB/SmolVLM2-256M-Video-Instruct"

# (frames oldest-first, prompt) -> one line of commentary
CommentFn = Callable[[list[np.ndarray], str], str]


@dataclass(frozen=True)
class CommentaryLine:
    timestamp: float  # video time the line refers to
    text: str
    latency: float  # seconds the VLM took

    def to_dict(self) -> dict:
        return asdict(self)


MAX_SPORT_LENGTH = 40


def clean_sport(raw: object) -> str:
    """A sport name safe to put in the prompt: one line, short, or "" for none."""
    text = " ".join(str(raw or "").split())
    return text[:MAX_SPORT_LENGTH].strip()


def build_prompt(
    events: list[Event], counts: Counter[str], previous: list[str], sport: str = ""
) -> str:
    if sport:
        # The detector only knows everyday objects (a cricket ball becomes a "frisbee"),
        # so when the sport is known its labels would mislead more than they help.
        parts = [
            f"You are an energetic live {sport} commentator. The images are consecutive "
            f"frames from the last few seconds of a {sport} match, oldest first."
        ]
    else:
        parts = [
            "You are an energetic live sports commentator. The images are consecutive "
            "frames from the last few seconds, oldest first."
        ]
        if counts:
            on_screen = ", ".join(f"{n} {label}" for label, n in counts.most_common())
            parts.append(f"Detected on screen: {on_screen}.")
        if events:
            parts.append("Just happened: " + "; ".join(e.describe() for e in events[-6:]) + ".")
    if previous:
        parts.append("Your previous lines (do not repeat them): " + " | ".join(previous))
    parts.append(
        "Give the next line of commentary: one short sentence about what is happening now."
    )
    return "\n".join(parts)


def clean_line(text: str) -> str:
    """First sentence of the first line; small models tend to ramble on."""
    line = text.strip().splitlines()[0] if text.strip() else ""
    line = line.strip().strip('"').strip()
    match = re.match(r"(.+?[.!?])(\s|$)", line)
    return match.group(1) if match else line


class Commentator:
    """SmolVLM2 (or another Hugging Face image-text-to-text model) as a ``CommentFn``."""

    def __init__(
        self,
        model_id: str = DEFAULT_VLM,
        device: str = "cpu",
        max_new_tokens: int = 40,
        max_side: int = 384,
    ):
        # Imported lazily: transformers is slow to import and only needed with --commentary.
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self._torch = torch
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.max_side = max_side
        dtype = torch.float32 if device == "cpu" else torch.bfloat16
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = (
            AutoModelForImageTextToText.from_pretrained(model_id, dtype=dtype).to(device).eval()
        )

    def _to_rgb(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        scale = self.max_side / max(h, w)
        if scale < 1:
            image = cv2.resize(
                image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def __call__(self, images: list[np.ndarray], prompt: str) -> str:
        from PIL import Image

        content = [{"type": "image", "image": Image.fromarray(self._to_rgb(im))} for im in images]
        content.append({"type": "text", "text": prompt})
        inputs = self.processor.apply_chat_template(
            [{"role": "user", "content": content}],
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            # Tiling multiplies image tokens ~10x; far too slow on CPU.
            processor_kwargs={"do_image_splitting": False},
        ).to(self.device)
        with self._torch.inference_mode():
            out = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                repetition_penalty=1.2,
            )
        new_tokens = out[:, inputs["input_ids"].shape[1] :]
        return clean_line(self.processor.batch_decode(new_tokens, skip_special_tokens=True)[0])


class CommentaryFeed:
    """Samples frames and events from the detection loop and narrates them in the background.

    A line is requested every ``interval`` seconds of video time, but only when the
    previous one has finished, so commentary never lags further behind than one call.
    ``on_line`` is invoked from the worker thread. With ``sport`` set, the prompt names
    the sport and leaves out the detector's labels and events (see ``build_prompt``).
    """

    def __init__(
        self,
        commentator: CommentFn,
        on_line: Callable[[CommentaryLine], None],
        interval: float = 3.0,
        frames_per_line: int = 2,
        history: int = 3,
        sport: str = "",
    ):
        self.commentator = commentator
        self.on_line = on_line
        self.interval = interval
        self.sport = clean_sport(sport)
        self._frame_gap = interval / frames_per_line
        self._frames: deque[np.ndarray] = deque(maxlen=frames_per_line)
        self._last_sample = float("-inf")
        self._next_due: float | None = None
        self._events: list[Event] = []
        self._history: deque[str] = deque(maxlen=history)
        self._jobs: queue.Queue = queue.Queue(maxsize=1)
        self._busy = threading.Event()
        self._thread = threading.Thread(target=self._run, name="commentary", daemon=True)
        self._thread.start()

    def push(self, frame: Frame, events: list[Event], counts: Counter[str]) -> None:
        self._events.extend(events)
        if frame.timestamp - self._last_sample >= self._frame_gap:
            self._frames.append(frame.image.copy())
            self._last_sample = frame.timestamp
        if self._next_due is None:
            self._next_due = frame.timestamp + self.interval
        if frame.timestamp < self._next_due or self._busy.is_set():
            return

        prompt = build_prompt(self._events, counts, list(self._history), self.sport)
        self._busy.set()
        self._jobs.put((frame.timestamp, list(self._frames), prompt))
        self._events = []
        self._next_due = frame.timestamp + self.interval

    def _run(self) -> None:
        while (job := self._jobs.get()) is not None:
            timestamp, images, prompt = job
            started = time.perf_counter()
            try:
                text = self.commentator(images, prompt)
            except Exception:
                log.exception("Commentary generation failed")
                text = ""
            if text:
                self._history.append(text)
                latency = round(time.perf_counter() - started, 2)
                self.on_line(CommentaryLine(timestamp, text, latency))
            self._busy.clear()

    def close(self, wait: bool = True) -> None:
        """Stop the worker; with ``wait`` the in-flight line is finished first."""
        self._jobs.put(None)
        if wait:
            self._thread.join()
