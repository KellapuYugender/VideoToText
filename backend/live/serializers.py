from rest_framework import serializers

from .models import CommentaryLine, Session


class CommentaryLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentaryLine
        fields = ["id", "timestamp", "text", "latency"]


class SessionSerializer(serializers.ModelSerializer):
    lines_count = serializers.IntegerField(read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id",
            "source",
            "kind",
            "status",
            "error",
            "started_at",
            "ended_at",
            "width",
            "height",
            "fps",
            "duration",
            "frames_processed",
            "events_count",
            "peak_counts",
            "commentary_enabled",
            "yolo_model",
            "vlm_model",
            "lines_count",
            "preview",
        ]

    def get_preview(self, session) -> str:
        """First commentary line, for list views."""
        lines = getattr(session, "first_lines", None)
        return lines[0].text if lines else ""


class SessionDetailSerializer(SessionSerializer):
    lines = CommentaryLineSerializer(many=True, read_only=True)

    class Meta(SessionSerializer.Meta):
        fields = [*SessionSerializer.Meta.fields, "lines"]
