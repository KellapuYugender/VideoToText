from django.db import models


def video_upload_path(instance, filename):
    return f"videos/{instance.uploaded_at:%Y/%m/%d}/{filename}"


class Video(models.Model):
    """An uploaded video and the description generated for it."""

    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=video_upload_path)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Filled in by the probe step
    duration_seconds = models.FloatField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Filled in by the compose step
    summary = models.TextField(blank=True)
    narrative = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title or self.original_filename


class Job(models.Model):
    """One run of the description pipeline over a video."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Stage(models.TextChoices):
        PENDING = "pending", "Pending"
        PROBE = "probe", "Reading video info"
        SEGMENT = "segment", "Detecting scenes"
        FRAMES = "frames", "Extracting frames"
        CAPTION = "caption", "Describing actions"
        COMPOSE = "compose", "Writing summary"
        DONE = "done", "Done"

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=16, choices=Status, default=Status.QUEUED)
    stage = models.CharField(max_length=16, choices=Stage, default=Stage.PENDING)
    progress = models.PositiveSmallIntegerField(default=0, help_text="0–100")
    message = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)

    # Settings used for this run, so results can be compared across models
    vision_model = models.CharField(max_length=100, blank=True)
    text_model = models.CharField(max_length=100, blank=True)

    task_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.pk} ({self.status}) for {self.video}"


class Segment(models.Model):
    """A time window of a video and the actions described in it."""

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="segments")
    index = models.PositiveIntegerField()
    start_seconds = models.FloatField()
    end_seconds = models.FloatField()
    caption = models.TextField(blank=True)

    class Meta:
        ordering = ["video", "index"]
        constraints = [
            models.UniqueConstraint(fields=["video", "index"], name="unique_segment_index"),
            models.CheckConstraint(
                condition=models.Q(end_seconds__gt=models.F("start_seconds")),
                name="segment_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.video} [{self.start_seconds:.1f}s–{self.end_seconds:.1f}s]"
