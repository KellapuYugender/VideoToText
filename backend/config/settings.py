"""
Django settings for the VideoToText backend.

Values that differ between machines (secrets, database, model names) are read from
environment variables, or from a `.env` file next to manage.py. See `.env.example`.

https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "daphne",  # ASGI runserver with WebSocket support; must come first
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "corsheaders",
    "rest_framework",
    "channels",
    # Local
    "videos",
    "live",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database (PostgreSQL), e.g. postgres://videototext:password@localhost:5433/videototext

DATABASES = {"default": env.db("DATABASE_URL")}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static and uploaded files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploads above this size are streamed to a temp file instead of held in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# CORS: allow the Vite dev server to call the API

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")


# Live pipeline (see the vision package)

# Files a client may stream live from are looked up under this folder.
VIDEO_DIR = env.path("VIDEO_DIR", default=MEDIA_ROOT / "videos")
ALLOW_WEBCAM = env.bool("ALLOW_WEBCAM", default=True)

TORCH_DEVICE = env("TORCH_DEVICE", default="cpu")  # "cuda" on a GPU machine
YOLO_MODEL = env("YOLO_MODEL", default=str(BASE_DIR / "weights" / "yolo11n.pt"))
YOLO_CONF = env.float("YOLO_CONF", default=0.35)
VLM_MODEL = env("VLM_MODEL", default="HuggingFaceTB/SmolVLM2-256M-Video-Instruct")
COMMENTARY_INTERVAL = env.float("COMMENTARY_INTERVAL", default=3.0)

# Frames are re-encoded as JPEG for the browser.
STREAM_MAX_WIDTH = env.int("STREAM_MAX_WIDTH", default=640)
STREAM_JPEG_QUALITY = env.int("STREAM_JPEG_QUALITY", default=70)
