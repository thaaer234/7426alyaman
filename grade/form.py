from django import forms
from django.forms import modelformset_factory 
from .models import Grade

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'exam_type', 'grade', 'notes', 'classroom']
        widgets = {
            'student': forms.HiddenInput(),
            'subject': forms.HiddenInput(),
            'exam_type': forms.HiddenInput(),
            'classroom': forms.HiddenInput(),
            'grade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1,
                'placeholder': 'أدخل العلامة'  # إضافة placeholder
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل الملاحظات هنا'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل الحقل غير مطلوب للسماح بقيم فارغة
        self.fields['grade'].required = False

GradeFormSet = modelformset_factory(  
    Grade,
    form=GradeForm,
    extra=0
)


class CustomPrintForm(forms.Form):
    PRINT_CHOICES = [
        ('summary', 'الجدول الإجمالي للمجموع'),
        ('1', 'جدول 1'),
        ('2', 'جدول 2'),
        ('3', 'جدول 3'),
        ('midterm', 'جدول النصفي'),
        ('all', 'جميع الجداول معاً')
    ]
    
    tables = forms.MultipleChoiceField(
        choices=PRINT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        initial=['summary'],
        label="اختر الجداول المطلوبة"
    )
    
    include_notes = forms.BooleanField(
        initial=True,
        required=False,
        label="تضمين الملاحظات"
    )
    
    include_signature = forms.BooleanField(
        initial=True,
        required=False,
        label="تضمين مكان التوقيع"
    )