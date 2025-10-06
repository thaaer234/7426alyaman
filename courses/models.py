from django.db import models
from employ.models import Teacher
from django import forms

class Subject(models.Model):
    class SubjectType(models.TextChoices):
        SCIENTIFIC = 'scientific', 'علمي'
        LITERARY = 'literary', 'أدبي'
        NINTH = 'ninth', 'تاسع'
        COMMON = 'common', 'مشترك'
    
    name = models.CharField(max_length=100, verbose_name='اسم المادة')
    subject_type = models.CharField(
        max_length=10, 
        choices=SubjectType.choices,
        verbose_name='نوع المادة'
    )
    teachers = models.ManyToManyField(
        'employ.Teacher', 
        verbose_name='المدرسون',
        related_name='subjects_taught' 
    )
    
    class Meta:
        verbose_name = 'مادة'
        verbose_name_plural = 'المواد'
        ordering = ['name']  # الترتيب الأبجدي افتراضيًا
    
    def __str__(self):
        return self.name
    
    def get_compatible_branches(self):
        """إرجاع الفروع المتوافقة مع هذه المادة"""
        if self.subject_type == 'scientific':
            return ['علمي']
        elif self.subject_type == 'literary':
            return ['أدبي']
        elif self.subject_type == 'ninth':
            return ['تاسع']
        elif self.subject_type == 'common':
            return ['علمي', 'أدبي', 'تاسع']
        return []

