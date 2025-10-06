from django.shortcuts import render ,get_object_or_404 , redirect
from django.views.generic import View , TemplateView ,ListView ,DetailView
from .models import Attendance ,TeacherAttendance
from .form import AttendanceForm,TeacherAttendanceForm
from classroom.models import Classroom
from students.models import Student
from employ.models import Teacher
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
# Create your views here.

class attendance(ListView):
    model = Attendance
    template_name = 'attendance/attendance.html'
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        # الحصول على سجلات الحضور مع معلومات الشعبة
        return Attendance.objects.select_related('classroom').order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تجميع التواريخ لكل شعبة
        summary = {}
        for record in context['attendance_records']:
            key = (record.classroom.id, record.classroom.name, record.date)
            if key not in summary:
                summary[key] = {
                    'classroom_id': record.classroom.id,
                    'classroom_name': record.classroom.name,
                    'date': record.date,
                    'student_count': Attendance.objects.filter(
                        classroom=record.classroom, 
                        date=record.date
                    ).count()
                }
        context['summary'] = summary.values()
        return context

class TakeAttendanceView(View):
    template_name = 'attendance/take_attendance.html'
    
    def get(self, request):
        form = AttendanceForm()
        return render(request, self.template_name, {
            'form': form,
            'classrooms': Classroom.objects.all()
        })
    
    def post(self, request):
        date = request.POST.get('date')
        classroom_id = request.POST.get('classroom')
        
        if not date or not classroom_id:
            messages.error(request, 'يجب اختيار التاريخ والشعبة')
            return redirect('attendance:take_attendance')
        
        classroom = get_object_or_404(Classroom, id=classroom_id)
        students = Student.objects.filter(
            classroom_enrollments__classroom=classroom
        ).distinct()
        
        # التحقق من وجود سجلات قديمة لنفس التاريخ والشعبة
        existing_attendances = Attendance.objects.filter(
            classroom=classroom,
            date=date
        ).exists()
        
        if existing_attendances:
            messages.error(request, 'يوجد بالفعل سجل حضور لهذا التاريخ والشعبة. الرجاء استخدام تعديل الحضور بدلاً من ذلك.')
            return redirect('attendance:take_attendance')
        
        success_count = 0
        error_messages = []
        
        for student in students:
            # قراءة القيمة مباشرة من الـ radio button
            status = request.POST.get(f'status_{student.id}', 'present')  # الافتراضي حاضر
            notes = request.POST.get(f'notes_{student.id}', '')
            
            try:
                attendance = Attendance.objects.create(
                    student=student,
                    classroom=classroom,
                    date=date,
                    status=status,
                    notes=notes
                )
                success_count += 1
            except IntegrityError as e:
                error_messages.append(f'خطأ في تسجيل حضور الطالب {student.full_name}: {str(e)}')
        
        if success_count > 0:
            messages.success(request, f'تم تسجيل حضور {success_count} طالب بنجاح')
        if error_messages:
            messages.error(request, '<br>'.join(error_messages))
        
        return redirect('attendance:attendance')


def get_students(request):
    classroom_id = request.GET.get('classroom')
    
    if not classroom_id:
        return JsonResponse({'error': 'يجب تحديد معرف الشعبة'}, status=400)
    
    try:
        # جلب الطلاب عبر علاقة التسجيل في الشعبة
        students = Student.objects.filter(
            classroom_enrollments__classroom_id=classroom_id
        ).distinct().values('id', 'full_name')
        
        if not students.exists():
            return JsonResponse({'error': 'لا يوجد طلاب في هذه الشعبة'}, status=404)
            
        return JsonResponse(list(students), safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



class AttendanceDetailView(ListView):
    model = Attendance
    template_name = 'attendance/attendance_detail.html'
    context_object_name = 'attendances'
    
    def get_queryset(self):
        classroom_id = self.kwargs.get('classroom_id')
        date = self.kwargs.get('date')
        return Attendance.objects.filter(classroom_id=classroom_id, date=date)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classroom'] = get_object_or_404(Classroom, id=self.kwargs.get('classroom_id'))
        context['date'] = self.kwargs.get('date')
        return context
    
    
### لتعديل الحضور 
class UpdateAttendanceView(View):
    template_name = 'attendance/update_attendance.html'
    
    def get(self, request, classroom_id, date):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        attendances = Attendance.objects.filter(classroom=classroom, date=date)
        
        return render(request, self.template_name, {
            'classroom': classroom,
            'date': date,
            'attendances': attendances
        })
    
    def post(self, request, classroom_id, date):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        students = Student.objects.filter(classroom_enrollments__classroom=classroom)
        
        success_count = 0
        error_messages = []
        
        for student in students:
            # قراءة القيمة مباشرة من الـ radio button
            status = request.POST.get(f'status_{student.id}', 'present')  # الافتراضي حاضر
            notes = request.POST.get(f'notes_{student.id}', '')
            
            try:
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    date=date,
                    defaults={
                        'classroom': classroom,
                        'status': status,
                        'notes': notes
                    }
                )
                success_count += 1
            except IntegrityError as e:
                error_messages.append(f'خطأ في تحديث حضور الطالب {student.full_name}: {str(e)}')
        
        if success_count > 0:
            messages.success(request, f'تم تحديث حضور {success_count} طالب بنجاح')
        if error_messages:
            messages.error(request, '<br>'.join(error_messages))
        
        return redirect('attendance:attendance')
    
    
class TeacherAttendanceView(ListView):
    model = TeacherAttendance
    template_name = 'attendance/teacher_attendance.html'
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        queryset = TeacherAttendance.objects.select_related('teacher').order_by('-date')
        
        # دعم التصفية حسب المدرس
        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تجميع البيانات لكل تاريخ
        summary = {}
        for record in context['attendance_records']:
            key = record.date
            if key not in summary:
                summary[key] = {
                    'date': record.date,
                    'present_count': 0,
                    'absent_count': 0,
                    'total_sessions': 0
                }
            
            if record.status == 'present':
                summary[key]['present_count'] += 1
                summary[key]['total_sessions'] += record.session_count
            elif record.status == 'absent':
                summary[key]['absent_count'] += 1
        
        context['summary'] = summary.values()
        context['teachers'] = Teacher.objects.all()
        return context    



class TakeTeacherAttendanceView(View):
    template_name = 'attendance/take_teacher_attendance.html'
    
    def get(self, request):
        form = TeacherAttendanceForm()
        teachers = Teacher.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'teachers': teachers
        })
    
    def post(self, request):
        date = request.POST.get('date')
        
        if not date:
            messages.error(request, 'يجب اختيار التاريخ')
            return redirect('employ:take_teacher_attendance')
        
        success_count = 0
        error_messages = []
        teachers_with_salary_accrual = []
        
        for teacher in Teacher.objects.all():
            status = request.POST.get(f'status_{teacher.id}', 'absent')
            session_count = request.POST.get(f'sessions_{teacher.id}', 1)
            notes = request.POST.get(f'notes_{teacher.id}', '')
            
            try:
                # التحقق من عدم وجود تسجيل مسبق لنفس اليوم والمدرس
                attendance, created = TeacherAttendance.objects.get_or_create(
                    teacher=teacher,
                    date=date,
                    defaults={
                        'status': status,
                        'session_count': session_count,
                        'notes': notes
                    }
                )
                
                if not created:
                    # إذا كان موجوداً مسبقاً، نقوم بالتحديث
                    attendance.status = status
                    attendance.session_count = session_count
                    attendance.notes = notes
                    attendance.save()
                
                # Create salary accrual entry if teacher was present
                if status == 'present' and int(session_count) > 0:
                    try:
                        # Get current month/year from the attendance date
                        attendance_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
                        accrual_year = attendance_date.year
                        accrual_month = attendance_date.month
                        
                        # Create or update salary accrual for this period
                        accrual_entry = teacher.create_salary_accrual_entry(
                            request.user, 
                            accrual_year, 
                            accrual_month
                        )
                        
                        if accrual_entry:
                            teachers_with_salary_accrual.append(teacher.full_name)
                    except Exception as e:
                        error_messages.append(f'تم تسجيل حضور {teacher.full_name} لكن فشل في إنشاء قيد الراتب: {str(e)}')
                
                success_count += 1
            except Exception as e:
                error_messages.append(f'خطأ في تسجيل حضور المدرس {teacher.full_name}: {str(e)}')
        
        if success_count > 0:
            messages.success(request, f'تم تسجيل حضور {success_count} مدرس بنجاح')
            
        if teachers_with_salary_accrual:
            messages.info(
                request, 
                f'تم إنشاء/تحديث قيود الرواتب للمدرسين: {", ".join(teachers_with_salary_accrual)}'
            )
            
        if error_messages:
            messages.error(request, '<br>'.join(error_messages))
        
        return redirect('attendance:teacher_attendance')

class TeacherAttendanceDetailView(ListView):
    model = TeacherAttendance
    template_name = 'attendance/teacher_attendance_detail.html'
    context_object_name = 'attendances'
    
    def get_queryset(self):
        date = self.kwargs.get('date')
        return TeacherAttendance.objects.filter(date=date).select_related('teacher')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date'] = self.kwargs.get('date')
        return context    
    
    
    
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone

def export_attendance_to_excel(request, classroom_id, date):
    # جلب بيانات الحضور
    attendances = Attendance.objects.filter(
        classroom_id=classroom_id, 
        date=date
    ).select_related('student')
    
    # إنشاء DataFrame من البيانات
    data = []
    for attendance in attendances:
        data.append({
            'اسم الطالب': attendance.student.full_name,
            'الحالة': attendance.get_status_display(),
            'ملاحظات': attendance.notes or ''
        })
    
    df = pd.DataFrame(data)
    
    # إنشاء اسم للملف
    classroom = get_object_or_404(Classroom, id=classroom_id)
    filename = f"حضور_{classroom.name}_{date}.xlsx"
    
    # إنشاء الرد بـ Excel file
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # تصدير DataFrame إلى Excel
    df.to_excel(response, index=False, sheet_name='الحضور')
    
    return response    