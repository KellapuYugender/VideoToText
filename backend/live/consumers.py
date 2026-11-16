import asyncio
import contextlib
import logging
import threading

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .sources import resolve_source
from .streaming import stream

log = logging.getLogger(__name__)

SEND_TIMEOUT = 10  # seconds a frame may wait for the client before the stream gives up


class LiveConsumer(AsyncJsonWebsocketConsumer):
    """One WebSocket runs at most one stream at a time.

    Client -> server: {"action": "start", "source": "...", "commentary": true}
                      {"action": "stop"}
    Server -> client: session, frame, event, commentary, error, end (see streaming.py)
    """

    async def connect(self):
        self.stop = threading.Event()
        self.task: asyncio.Task | None = None
        await self.accept()

    async def disconnect(self, code):
        self.stop.set()

    async def receive_json(self, content, **kwargs):
        action = content.get("action") if isinstance(content, dict) else None
        if action == "start":
            await self.start(content)
        elif action == "stop":
            self.stop.set()
        else:
            await self.send_json({"type": "error", "message": f"Unknown action: {action!r}"})

    async def start(self, content: dict):
        if self.task is not None and not self.task.done():
            await self.send_json({"type": "error", "message": "A stream is already running."})
            return
        try:
            source = resolve_source(str(content.get("source", "")))
        except ValueError as exc:
            await self.send_json({"type": "error", "message": str(exc)})
            return
        self.stop = threading.Event()
        commentary = bool(content.get("commentary", True))
        self.task = asyncio.create_task(self.run(source, commentary, self.stop))

    async def run(self, source, commentary: bool, stop: threading.Event):
        loop = asyncio.get_running_loop()

        def send(message: dict, wait: bool) -> None:
            future = asyncio.run_coroutine_threadsafe(self.send_json(message), loop)
            if wait:
                future.result(timeout=SEND_TIMEOUT)

        try:
            await asyncio.to_thread(stream, source, send, stop, commentary)
        except Exception as exc:
            log.exception("Live stream failed for source %r", source)
            with contextlib.suppress(Exception):
                await self.send_json({"type": "error", "message": str(exc)})
        with contextlib.suppress(Exception):  # the client may already be gone
            await self.send_json({"type": "end"})
