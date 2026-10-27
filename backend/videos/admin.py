from django.contrib import admin

from .models import Job, Segment, Video


class SegmentInline(admin.TabularInline):
    model = Segment
    extra = 0
    fields = ["index", "start_seconds", "end_seconds", "caption"]
    readonly_fields = fields


class JobInline(admin.TabularInline):
    model = Job
    extra = 0
    fields = ["status", "stage", "progress", "vision_model", "created_at", "finished_at"]
    readonly_fields = fields
    show_change_link = True


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "duration_seconds", "uploaded_at"]
    search_fields = ["title", "original_filename", "summary"]
    readonly_fields = ["uploaded_at", "duration_seconds", "fps", "width", "height"]
    inlines = [JobInline, SegmentInline]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["id", "video", "status", "stage", "progress", "created_at"]
    list_filter = ["status", "stage"]
    readonly_fields = ["created_at", "started_at", "finished_at", "task_id"]


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ["video", "index", "start_seconds", "end_seconds"]
    list_filter = ["video"]
