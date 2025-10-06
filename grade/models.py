from django.db import models
from courses.models import Subject
from students.models import Student
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Grade(models.Model):
    class ExamType(models.TextChoices):
        MONTHLY = 'monthly', _('شهري')
        MIDTERM = 'midterm', _('نصفي')
        FINAL = 'final', _('نهائي')
        ACTIVITY = 'activity', _('نشاط')
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name=_('المادة'))
    grade = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name=_('العلامة'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,  # السماح بقيم فارغة
        blank=True  # السماح بحقول فارغة في النماذج
    )
    exam_type = models.CharField(
        max_length=50, 
        choices=ExamType.choices,
        verbose_name=_('نوع الامتحان')
    )
    date = models.DateField(auto_now_add=True, verbose_name=_('تاريخ التسجيل'))
    notes = models.TextField(blank=True, null=True, verbose_name=_('ملاحظات'))
    classroom = models.ForeignKey(
        'classroom.Classroom', 
        on_delete=models.CASCADE,
        verbose_name="الشعبة",
        null=True  # مؤقتاً للسماح بالقيم الفارغة
    )
    
    class Meta:
        unique_together = ('student', 'subject', 'exam_type')
        verbose_name = _('علامة')
        verbose_name_plural = _('العلامات')
        ordering = ['-date', 'student__full_name']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name}: {self.grade}"