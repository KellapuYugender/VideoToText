from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sessions", views.SessionViewSet, basename="session")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("live/sources/", views.sources, name="live-sources"),
    path("live/videos/", views.upload_video, name="live-upload"),
    path("", include(router.urls)),
]
