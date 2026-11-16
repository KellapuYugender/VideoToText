from django.urls import path

from . import views

urlpatterns = [
    path("live/sources/", views.sources, name="live-sources"),
    path("live/videos/", views.upload_video, name="live-upload"),
]
