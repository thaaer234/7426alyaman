from django import forms
from courses.models import Subject
from .models import Classroom ,ClassroomSubject

class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = '__all__'
        widgets = {
            'branches': forms.Select(attrs={'class': 'form-control'}),
            'class_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.class_type == 'course':
            self.fields['branches'].widget = forms.HiddenInput()
        
        
class ClassroomSubjectForm(forms.ModelForm):
    class Meta:
        model = ClassroomSubject
        fields = ['classroom', 'subject']
        widgets = {
            'classroom': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        classroom = kwargs.pop('classroom', None)
        super().__init__(*args, **kwargs)
        
        if classroom:
            # تصفية المواد بناءً على نوع الشعبة وفرعها
            if classroom.class_type == 'study':
                if classroom.branches == 'علمي':
                    # للمواد العلمية والمشتركة
                    self.fields['subject'].queryset = Subject.objects.filter(
                        subject_type__in=['scientific', 'common']
                    )
                elif classroom.branches == 'أدبي':
                    # للمواد الأدبية والمشتركة
                    self.fields['subject'].queryset = Subject.objects.filter(
                        subject_type__in=['literary', 'common']
                    )
                elif classroom.branches == 'تاسع':
                    # للمواد الخاصة بالتاسع والمشتركة
                    self.fields['subject'].queryset = Subject.objects.filter(
                        subject_type__in=['ninth', 'common']
                    )
            else:
                # للدورات: عرض جميع المواد
                self.fields['subject'].queryset = Subject.objects.all()          