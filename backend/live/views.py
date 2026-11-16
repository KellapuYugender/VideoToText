from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Count, Prefetch
from django.utils.text import get_valid_filename
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import CommentaryLine, Session
from .serializers import SessionDetailSerializer, SessionSerializer
from .sources import VIDEO_EXTENSIONS, list_videos


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def sources(request):
    """Video files a client may stream, and whether webcams are allowed."""
    return Response({"videos": list_videos(), "webcam": settings.ALLOW_WEBCAM})


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_video(request):
    """Save an uploaded video into VIDEO_DIR so it can be streamed by name."""
    upload = request.FILES.get("file")
    if upload is None:
        return Response(
            {"error": "Send the video as the 'file' field."}, status.HTTP_400_BAD_REQUEST
        )

    name = get_valid_filename(Path(upload.name).name)
    if Path(name).suffix.lower() not in VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(VIDEO_EXTENSIONS))
        return Response(
            {"error": f"Unsupported file type. Use {allowed}."}, status.HTTP_400_BAD_REQUEST
        )
    if upload.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        return Response(
            {"error": f"File is larger than {settings.MAX_UPLOAD_MB} MB."},
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    # FileSystemStorage picks a fresh name instead of overwriting an existing file.
    saved = FileSystemStorage(location=settings.VIDEO_DIR).save(name, upload)
    return Response({"name": Path(saved).as_posix()}, status.HTTP_201_CREATED)


class SessionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Past live sessions, newest first; the detail view includes the full transcript.

    Sessions are created by the live stream itself, so there is no create/update.
    """

    def get_queryset(self):
        # Explicit order: Django drops Meta.ordering on aggregate queries.
        queryset = Session.objects.annotate(lines_count=Count("lines")).order_by(
            "-started_at", "-id"
        )
        if self.action == "list":
            first = CommentaryLine.objects.order_by("timestamp", "id")
            return queryset.prefetch_related(Prefetch("lines", first, to_attr="first_lines"))
        return queryset.prefetch_related("lines")

    def get_serializer_class(self):
        return SessionDetailSerializer if self.action == "retrieve" else SessionSerializer
