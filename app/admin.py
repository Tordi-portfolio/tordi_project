from django.contrib import admin
from .models import UploadedLAS, Well

@admin.register(UploadedLAS)
class UploadedLASAdmin(admin.ModelAdmin):
    list_display = ("id", "file", "uploaded_at")
    ordering = ("-uploaded_at",)
admin.site.register(Well)