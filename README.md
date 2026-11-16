# VideoToText

Real-time video-to-text, like live sports commentary: point it at a video file, webcam or
stream and it tracks what is on screen and narrates it as it happens. All models run locally.

> Status: all five core pieces work end to end: live detection, commentary, the WebSocket
> API, the React UI, and saved sessions.

## How it works

1. **Capture**: OpenCV reads frames from a file, webcam or RTSP/HTTP stream. Files are paced
   like a live feed, dropping frames if processing falls behind.
2. **Detect and track** (every frame): YOLO11n + ByteTrack find objects and keep stable IDs;
   objects entering or leaving become scene events.
3. **Commentate** (every ~3 s, background thread): SmolVLM2 looks at recent frames, grounded
   by the tracker's counts and events, and writes one line of commentary.
4. **Stream**: Django Channels pushes frames, boxes, events and commentary to the browser
   over a WebSocket.
5. **Save**: every stream is stored in PostgreSQL as a session (status, duration, peak
   object counts, models used) with its full commentary transcript.

## Tech stack

| Layer | Choice |
|---|---|
| Vision | OpenCV, PyTorch, Ultralytics YOLO11 + ByteTrack |
| Commentary | SmolVLM2 via Hugging Face Transformers |
| Backend | Python 3.14, Django 5.2 LTS, Django REST Framework, Channels + Daphne |
| Database | PostgreSQL |
| Frontend | React, Vite, TypeScript |
| Quality | pytest, pytest-django, pytest-asyncio, Ruff |

## Backend setup (Windows)

Prerequisites: Python 3.12+ and PostgreSQL.

```powershell
cd backend
py -3.14 -m venv .venv
# CPU-only PyTorch (skip on a CUDA machine)
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Create the database (run in psql as the postgres superuser)
#   CREATE USER videototext WITH PASSWORD 'change-me';
#   CREATE DATABASE videototext OWNER videototext;

copy .env.example .env      # then edit DATABASE_URL and SECRET_KEY
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

Model weights download on first use (YOLO to `backend/weights/`, SmolVLM2 to the Hugging
Face cache).

Admin: http://127.0.0.1:8000/admin/

## Frontend setup

Prerequisites: Node.js 20+. Keep the Django server running, then:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, pick a video (or upload one, or use the webcam) and press
**Start**. The page shows the video with tracked boxes, a live commentary feed that is also
read aloud (browser text-to-speech), what is on screen, and enter/leave events. The
**History** tab lists saved sessions with their transcripts (copy, download as .txt, delete).
Vite proxies `/api` and `/ws` to Django on port 8000.

## Try the pipeline without the server

```powershell
cd backend
.venv\Scripts\python.exe -m vision.live --source 0                          # webcam
.venv\Scripts\python.exe -m vision.live --source match.mp4 --commentary     # file + commentary
```

## Live API

- `GET /api/live/sources/` lists the videos in `backend/media/videos/` that can be streamed.
- `POST /api/live/videos/` uploads a video (multipart field `file`) and returns its `name`.
- `GET /api/sessions/` lists saved sessions (newest first, paginated);
  `GET /api/sessions/<id>/` includes the transcript; `DELETE` removes one.
- WebSocket `ws://127.0.0.1:8000/ws/live/`:
  - send `{"action": "start", "source": "match.mp4", "commentary": true}`; `source` is a
    file in `media/videos/`, a webcam index such as `"0"`, or an `rtsp://`/`http(s)://` URL
  - send `{"action": "stop"}` to end it early
  - receive `session` (`session_id`, size, fps), then `frame` (base64 JPEG, `detections` with boxes in
    source pixels, `counts`), `event` (entered/left), `commentary`, and finally `end`;
    `error` carries a `message`

## Tests and linting

Tests run against SQLite (`config/settings_test.py`), so they don't need permission to
create a Postgres test database.

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
.venv\Scripts\ruff.exe check .
```
