from django.shortcuts import render
from django.views.generic import View , TemplateView ,ListView ,DetailView ,CreateView, UpdateView ,DeleteView
from django.urls import reverse_lazy
from .models import Subject
from employ.models import Teacher  # تأكد من استيراد نموذج المعلم

# إدارة المواد
class SubjectListView(ListView):
    model = Subject
    template_name = 'courses/subject_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # إضافة قائمة المدرسين للسياق لاستخدامها في التصفية
        context['teachers'] = Teacher.objects.all().order_by('full_name')
        return context

class SubjectCreateView(CreateView):
    model = Subject
    fields = ['name', 'subject_type', 'teachers']
    template_name = 'courses/subject_form.html'
    success_url = reverse_lazy('courses:subject_list')
    
class SubjectUpdateView(UpdateView):
    model = Subject
    fields = ['name', 'subject_type', 'teachers']
    template_name = 'courses/subject_form.html'
    success_url = reverse_lazy('courses:subject_list')

class SubjectDeleteView(DeleteView):
    model = Subject
    template_name = 'courses/subject_confirm_delete.html'
    success_url = reverse_lazy('courses:subject_list')    

class courses(TemplateView):
    template_name = 'courses/courses.html'