from django.contrib import admin

from .models import CommentaryLine, Session


class CommentaryLineInline(admin.TabularInline):
    model = CommentaryLine
    extra = 0
    readonly_fields = ["timestamp", "text", "latency", "created_at"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["source", "kind", "status", "started_at", "duration", "frames_processed"]
    list_filter = ["status", "kind"]
    search_fields = ["source", "lines__text"]
    readonly_fields = ["started_at", "ended_at"]
    inlines = [CommentaryLineInline]
