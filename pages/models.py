# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'إنشاء'),
        ('update', 'تعديل'),
        ('delete', 'حذف'),
        ('login', 'دخول'),
        ('logout', 'خروج'),
        ('view', 'عرض'),
        ('other', 'أخرى'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    content_type = models.CharField(max_length=100)  # نوع المودل
    object_id = models.PositiveIntegerField(null=True, blank=True)  # معرف العنصر
    object_repr = models.CharField(max_length=200)  # وصف العنصر
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True)  # تفاصيل إضافية

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'سجل النشاط'
        verbose_name_plural = 'سجلات النشاطات'

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.content_type}"