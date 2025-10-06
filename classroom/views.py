from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, ListView, CreateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from .models import Classroom ,Classroomenrollment ,ClassroomSubject
from .form import ClassroomForm ,ClassroomSubjectForm
from students.models import Student
from courses.models import Subject
from django.db import IntegrityError
from django.core.exceptions import ValidationError
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import openpyxl
from openpyxl.styles import Font, Alignment




# Create your views here.
class ClassroomListView(ListView):
    template_name = 'classroom/classroom.html'
    model = Classroom
    context_object_name = 'classrooms'
    
    
class CreateClassroomView(CreateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'classroom/create_classroom.html'
    success_url = reverse_lazy('classroom:classroom')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'تم إضافة الشعبة بنجاح')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'حدث خطأ في إدخال البيانات')
        return super().form_invalid(form)    
    

class AssignStudentsView(View):
    template_name = 'classroom/assign_students.html'

    def get(self, request, classroom_id):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        
        # الحصول على الطلاب المسجلين في هذه الشعبة
        current_enrollments = Classroomenrollment.objects.filter(classroom=classroom)
        assigned_students = [e.student for e in current_enrollments]
        
        if classroom.class_type == 'study':
            # للشعبة الدراسية: نعرض فقط الطلاب غير مسجلين في أي شعبة دراسية ومن نفس الفرع
            enrolled_in_study = Classroomenrollment.objects.filter(
                classroom__class_type='study'
            ).values_list('student__id', flat=True)
            
            available_students = Student.objects.filter(
                branch=classroom.branches
            ).exclude(
                id__in=enrolled_in_study
            )
        else:
            # للدورة: نعرض جميع الطلاب غير مسجلين في هذه الدورة
            enrolled_in_course = current_enrollments.values_list('student__id', flat=True)
            available_students = Student.objects.exclude(id__in=enrolled_in_course)
        
        return render(request, self.template_name, {
            'classroom': classroom,
            'unassigned_students': available_students,
            'assigned_students': assigned_students
        })

    def post(self, request, classroom_id):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        student_ids = request.POST.getlist('student_ids')

        if student_ids:
            for student_id in student_ids:
                student = get_object_or_404(Student, id=student_id)
                
                try:
                    Classroomenrollment.objects.create(
                        student=student,
                        classroom=classroom,
                    )
                except ValidationError as e:
                    messages.error(request, str(e))
                    continue
                except IntegrityError:
                    messages.warning(request, f'الطالب {student.full_name} مسجل بالفعل في هذه الشعبة')
                    continue
            
            messages.success(request, 'تم تعيين الطلاب للشعبة بنجاح')
        
        return redirect('classroom:assign_students', classroom_id=classroom_id)

class UnassignStudentView(View):
    def post(self, request, classroom_id, student_id):
        enrollment = get_object_or_404(
            Classroomenrollment,
            classroom_id=classroom_id,
            student_id=student_id
        )
        enrollment.delete()
        messages.success(request, 'تم إزالة الطالب من الشعبة بنجاح')
        return redirect('classroom:assign_students', classroom_id=classroom_id)

class ClassroomStudentsView(ListView):
    template_name = 'classroom/classroom_students.html'
    context_object_name = 'students'

    def get_queryset(self):
        classroom = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        if classroom.class_type == 'study':
            # للشعبة الدراسية: نراعي الفرع
            return Student.objects.filter(
                classroom_enrollments__classroom=classroom,
                branch=classroom.branches
            )
        else:
            # للدورة: نعرض جميع الطلاب المسجلين بغض النظر عن الفرع
            return Student.objects.filter(
                classroom_enrollments__classroom=classroom
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classroom = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        context['classroom'] = classroom
        return context

class DeleteClassroomView(DeleteView):
    model = Classroom
    pk_url_kwarg = 'classroom_id'
    success_url = reverse_lazy('classroom:classroom')
    template_name = 'classroom/classroom_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'تم حذف الشعبة بنجاح')
        return super().delete(request, *args, **kwargs)


class ClassroomSubjectListView(ListView):
    model = ClassroomSubject
    template_name = 'classroom/classroom_subject_list.html'

    def get_queryset(self):
        return ClassroomSubject.objects.filter(
            classroom_id=self.kwargs['classroom_id']
        ).select_related('subject').prefetch_related('subject__teachers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classroom'] = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        return context

class ClassroomSubjectCreateView(CreateView):
    model = ClassroomSubject
    form_class = ClassroomSubjectForm
    template_name = 'classroom/classroom_subject_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        classroom = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        kwargs['classroom'] = classroom
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['classroom'] = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        return initial

    # في ClassroomSubjectCreateView، قم بتعديل طريقة get_context_data
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classroom = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        context['classroom'] = classroom
        
        # تحميل المواد مع معلميها مسبقاً لتحسين الأداء
        if classroom.class_type == 'study':
            if classroom.branches == 'علمي':
                subjects = Subject.objects.filter(
                    subject_type__in=['scientific', 'common']
                ).prefetch_related('teachers')
            elif classroom.branches == 'أدبي':
                subjects = Subject.objects.filter(
                    subject_type__in=['literary', 'common']
                ).prefetch_related('teachers')
            elif classroom.branches == 'تاسع':
                subjects = Subject.objects.filter(
                    subject_type__in=['ninth', 'common']
                ).prefetch_related('teachers')
            else:
                subjects = Subject.objects.none()
        else:
            subjects = Subject.objects.all().prefetch_related('teachers')
        
        # إنشاء قائمة بالمواد مع أسماء المعلمين
        subject_choices = []
        for subject in subjects:
            teacher_names = ", ".join([teacher.full_name for teacher in subject.teachers.all()])
            if teacher_names:
                display_name = f"{subject.name} ({teacher_names})"
            else:
                display_name = subject.name
            subject_choices.append((subject.id, display_name))
        
        context['subject_choices'] = subject_choices
        return context

    def form_valid(self, form):
        form.instance.classroom = get_object_or_404(Classroom, id=self.kwargs['classroom_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('classroom:classroom_subject_list', kwargs={'classroom_id': self.kwargs['classroom_id']})


class AssignToCourseView(View):
    template_name = 'classroom/assign_to_course.html'

    def get(self, request, course_id):
        course = get_object_or_404(Classroom, id=course_id, class_type='course')
        enrollments = Classroomenrollment.objects.filter(classroom=course)
        
        enrolled_student_ids = enrollments.values_list('student__id', flat=True)
        available_students = Student.objects.exclude(id__in=enrolled_student_ids)
        
        return render(request, self.template_name, {
            'course': course,
            'available_students': available_students,
            'enrolled_students': [e.student for e in enrollments]
        })

    def post(self, request, course_id):
        course = get_object_or_404(Classroom, id=course_id, class_type='course')
        student_ids = request.POST.getlist('student_ids')

        if student_ids:
            for student_id in student_ids:
                Classroomenrollment.objects.get_or_create(
                    student_id=student_id,
                    classroom=course,
                    
                )
            messages.success(request, 'تم تسجيل الطلاب في الدورة بنجاح')
        
        return redirect('classroom:assign_to_course', course_id=course_id)
    
    
    
    


def export_classroom_students_to_excel(request, classroom_id):
    # جلب بيانات الشعبة
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    # جلب طلاب الشعبة فقط
    students = Student.objects.filter(
        classroom_enrollments__classroom=classroom
    ).values('full_name')
    
    # تحويل البيانات إلى DataFrame
    df = pd.DataFrame(list(students))
    
    # إضافة عمود الأرقام التسلسلية
    df.insert(0, '#', range(1, len(df) + 1))
    
    # إعادة تسمية الأعمدة بالعربية
    df.rename(columns={'full_name': 'اسم الطالب'}, inplace=True)
    
    # إعداد اسم الملف والاستجابة
    filename = f"طلاب_{classroom.name}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # إنشاء Excel باستخدام pandas
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(
            writer, 
            sheet_name='الطلاب', 
            index=False,
            startrow=0
        )
        
        # الحصول على ورقة العمل وتنسيقها
        worksheet = writer.sheets['الطلاب']
        
        # تنسيق الأعمدة (ضبط العرض)
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # تنسيق الرأس (جعل الخط عريض ومركز)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')
    
    return response