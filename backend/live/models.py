from django.db import models


class Session(models.Model):
    """One live stream: where it came from, how it went, and a summary of what was seen."""

    class Kind(models.TextChoices):
        FILE = "file", "Video file"
        WEBCAM = "webcam", "Webcam"
        STREAM = "stream", "Stream URL"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"

    source = models.CharField(max_length=500, help_text="File name, webcam index or URL")
    kind = models.CharField(max_length=10, choices=Kind)
    status = models.CharField(max_length=10, choices=Status, default=Status.RUNNING)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Filled in once the source is open
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)

    # Filled in when the stream ends
    duration = models.FloatField(default=0, help_text="Seconds of video covered")
    frames_processed = models.PositiveIntegerField(default=0)
    events_count = models.PositiveIntegerField(default=0)
    peak_counts = models.JSONField(
        default=dict, blank=True, help_text="Most objects of each label seen at once"
    )

    commentary_enabled = models.BooleanField(default=True)
    yolo_model = models.CharField(max_length=200, blank=True)
    vlm_model = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]

    def __str__(self):
        return f"{self.source} ({self.started_at:%Y-%m-%d %H:%M})"


class CommentaryLine(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="lines")
    timestamp = models.FloatField(help_text="Video time in seconds")
    text = models.TextField()
    latency = models.FloatField(help_text="Seconds the VLM took")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "timestamp", "id"]

    def __str__(self):
        return f"[{self.timestamp:.1f}s] {self.text}"
