from django.contrib import admin
from .models import Grade


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'exam_type', 'grade', 'classroom', 'date']
    list_filter = ['exam_type', 'classroom', 'subject', 'date']
    search_fields = ['student__full_name', 'subject__name']
    ordering = ['-date', 'student__full_name']