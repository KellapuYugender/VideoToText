from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .sources import list_videos


@api_view(["GET"])
def sources(request):
    """Video files a client may stream, and whether webcams are allowed."""
    return Response({"videos": list_videos(), "webcam": settings.ALLOW_WEBCAM})
