from django.contrib import admin
from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject_type']
    list_filter = ['subject_type']
    search_fields = ['name']
    filter_horizontal = ['teachers']