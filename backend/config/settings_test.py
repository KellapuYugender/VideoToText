"""Settings for the test suite: an SQLite database, so tests don't need Postgres rights."""

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test.sqlite3"}}  # noqa: F405
