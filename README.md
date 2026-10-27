# VideoToText

Upload a video and get a text description of the actions happening on screen: a timestamped
narrative plus a short summary. All AI runs locally and free via [Ollama](https://ollama.com).

> Status: early development. The Django backend skeleton is in place; the video pipeline,
> API and React frontend are next.

## How it works

1. **Probe** the video with `ffprobe` (duration, fps, resolution).
2. **Segment** it into 4–6 s windows using scene detection (PySceneDetect).
3. **Extract** 3 frames per segment with FFmpeg.
4. **Caption** each segment with a local vision model (`qwen2.5vl:3b`), sending consecutive
   frames together so the model can describe motion and actions.
5. **Compose** the segment captions into a timestamped narrative and summary with a local text
   model (`llama3.2:3b`).

Processing runs as a background job (django-tasks, stored in Postgres) and the frontend polls
for progress.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.14, Django 5.2 LTS, Django REST Framework |
| Database / job queue | PostgreSQL, django-tasks + django-tasks-db |
| AI runtime | Ollama (`qwen2.5vl:3b`, `llama3.2:3b`) |
| Video processing | FFmpeg, PySceneDetect |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Quality | pytest, pytest-django, Ruff |

## Backend setup (Windows)

Prerequisites: Python 3.12+ and PostgreSQL.

```powershell
cd backend
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Create the database (run in psql as the postgres superuser)
#   CREATE USER videototext WITH PASSWORD 'change-me';
#   CREATE DATABASE videototext OWNER videototext;

copy .env.example .env      # then edit DATABASE_URL and SECRET_KEY
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

In a second terminal, start the background worker:

```powershell
.venv\Scripts\python.exe manage.py db_worker
```

Admin: http://127.0.0.1:8000/admin/

## Tests and linting

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
.venv\Scripts\ruff.exe check .
```
