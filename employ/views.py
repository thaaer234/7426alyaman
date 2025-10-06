from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count
from django.core.exceptions import FieldDoesNotExist

from accounts.models import ExpenseEntry, EmployeeAdvance, Account
from accounts.forms import EmployeeAdvanceForm
from attendance.models import TeacherAttendance

from .models import Teacher, Employee, Vacation, EmployeePermission
from .forms import TeacherForm, EmployeeRegistrationForm, AdminVacationForm


# -----------------------------
# أدوات مساعدة
# -----------------------------
def _employee_full_name(employee):
    """إرجاع اسم الموظف للعرض بأولوية: Employee.full_name -> User.get_full_name -> username"""
    if not employee:
        return ''
    name_attr = getattr(employee, 'full_name', None)
    if name_attr:
        return name_attr
    user = getattr(employee, 'user', None)
    if user:
        full_name = user.get_full_name()
        return full_name if full_name else user.get_username()
    return str(employee)


# خريطة المجموعات بحسب بادئة كود الصلاحية
GROUP_PREFIXES = {
    'students_': 'students',
    'teachers_': 'teachers',
    'attendance_': 'attendance',
    'classroom_': 'classroom',
    'grades_': 'grades',
    'courses_': 'courses',
    'accounting_': 'accounting',
    'hr_': 'hr',
    'admin_': 'admin',
    'reports_': 'reports',
    'course_accounting_': 'course_accounting',
    'inventory_': 'inventory',   # سنجمع الأصول مع المخزون في نفس المجموعة
    'assets_': 'inventory',
    'marketing_': 'marketing',
    'quality_': 'quality',
}


def _empty_permission_groups():
    """نضمن وجود جميع المفاتيح دائماً (حتى لو كانت القوائم فارغة)."""
    return {
        'students': [],
        'teachers': [],
        'attendance': [],
        'classroom': [],
        'grades': [],
        'courses': [],
        'accounting': [],
        'hr': [],
        'admin': [],
        'reports': [],
        'course_accounting': [],
        'inventory': [],
        'marketing': [],
        'quality': [],
    }


def _group_for_code(code: str):
    """استخرج اسم المجموعة من بادئة كود الصلاحية."""
    for prefix, group in GROUP_PREFIXES.items():
        if code.startswith(prefix):
            return group
    return None


# -----------------------------
# إدارة صلاحيات الموظف
# -----------------------------
class EmployeePermissionsView(LoginRequiredMixin, View):
    template_name = 'employ/employee_permissions.html'

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)

        # الصلاحيات الممنوحة حاليًا
        granted = set(
            employee.permissions.filter(is_granted=True).values_list('permission', flat=True)
        )

        # بناء القوائم
        permission_groups = _empty_permission_groups()

        for code, label in EmployeePermission.PERMISSION_CHOICES:
            group = _group_for_code(code)
            if not group:
                continue
            permission_groups[group].append({
                'code': code,
                'label': label,
                'is_granted': code in granted
            })

        return render(request, self.template_name, {
            'employee': employee,
            'permission_groups': permission_groups
        })

    @transaction.atomic
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)

        # الصلاحيات المختارة
        selected_codes = set(request.POST.getlist('permissions'))

        # ببساطة: فعّل ما تم تحديده، وعطّل الباقي
        existing = {ep.permission: ep for ep in employee.permissions.all()}

        for code, _label in EmployeePermission.PERMISSION_CHOICES:
            should_grant = code in selected_codes
            if code in existing:
                ep = existing[code]
                if ep.is_granted != should_grant:
                    ep.is_granted = should_grant
                    ep.granted_by = request.user if should_grant else ep.granted_by
                    ep.save(update_fields=['is_granted', 'granted_by'])
            else:
                if should_grant:
                    EmployeePermission.objects.create(
                        employee=employee,
                        permission=code,
                        is_granted=True,
                        granted_by=request.user
                    )

        messages.success(request, f'تم تحديث صلاحيات الموظف { _employee_full_name(employee) } بنجاح.')
        return redirect('employ:employee_permissions', pk=pk)


# -----------------------------
# سلف الموظفين
# -----------------------------
class EmployeeAdvanceListView(LoginRequiredMixin, ListView):
    model = EmployeeAdvance
    template_name = 'employ/employee_advance_list.html'
    context_object_name = 'advances'

    def get_queryset(self):
        return EmployeeAdvance.objects.select_related('employee__user', 'created_by').order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        advances = self.get_queryset()
        context['total_advances'] = advances.count()
        context['outstanding_advances'] = advances.filter(is_repaid=False).count()
        context['total_outstanding_amount'] = sum(adv.outstanding_amount for adv in advances.filter(is_repaid=False))
        context['total_advance_amount'] = sum(adv.amount for adv in advances)
        return context


class EmployeeAdvanceCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeAdvance
    form_class = EmployeeAdvanceForm
    template_name = 'employ/employee_advance_form.html'
    success_url = reverse_lazy('employ:employee_advance_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        # قيد محاسبي
        try:
            self.object.create_advance_journal_entry(self.request.user)
            messages.success(
                self.request,
                f'تم إنشاء سلفة للموظف {self.object.employee.user.get_full_name()} بمبلغ {self.object.amount} ل.س'
            )
        except Exception as e:
            messages.error(self.request, f'خطأ في إنشاء القيد المحاسبي: {e}')
        return response


class EmployeeAdvanceDetailView(LoginRequiredMixin, DetailView):
    model = EmployeeAdvance
    template_name = 'employ/employee_advance_detail.html'
    context_object_name = 'advance'


class EmployeeAdvanceRepayView(LoginRequiredMixin, View):
    def post(self, request, pk):
        advance = get_object_or_404(EmployeeAdvance, pk=pk)
        display_name = advance.employee.user.get_full_name() or advance.employee.user.get_username()

        try:
            repayment_amount = Decimal(str(request.POST.get('repayment_amount', '0')))
        except (ValueError, InvalidOperation):
            repayment_amount = Decimal('0')

        if repayment_amount <= 0:
            messages.error(request, 'يجب إدخال مبلغ سداد صحيح.')
            return redirect('employ:employee_advance_detail', pk=pk)

        if repayment_amount > advance.outstanding_amount:
            messages.error(request, 'مبلغ السداد أكبر من المبلغ المتبقي.')
            return redirect('employ:employee_advance_detail', pk=pk)

        try:
            advance.create_repayment_entry(repayment_amount, request.user)
            messages.success(request, f'تم تسجيل سداد سلفة {display_name} بنجاح.')
        except Exception as e:
            messages.error(request, f'تعذر تسجيل السداد: {e}')

        return redirect('employ:employee_advance_detail', pk=pk)


# -----------------------------
# المدرّسون
# -----------------------------
class teachers(LoginRequiredMixin, ListView):
    model = Teacher
    template_name = 'employ/teachers.html'
    context_object_name = 'teachers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teachers = context.get('teachers') or context.get('object_list') or Teacher.objects.all()

        today = timezone.now().date()
        current_year = today.year
        current_month = today.month

        # فترة الراتب الافتراضية
        if today.day >= 25:
            period_date = today
        else:
            period_date = today.replace(day=1) - timedelta(days=1)

        salary_year = period_date.year
        salary_month = period_date.month

        teachers_data = []
        paid_count = 0
        unpaid_count = 0

        for teacher in teachers:
            monthly_sessions = teacher.get_monthly_sessions(salary_year, salary_month)
            salary_amount = teacher.calculate_monthly_salary(salary_year, salary_month)
            salary_status = teacher.get_salary_status(salary_year, salary_month)

            paid_count += 1 if salary_status else 0
            unpaid_count += 0 if salary_status else 1

            teachers_data.append({
                'teacher': teacher,
                'monthly_sessions': monthly_sessions,
                'calculated_salary': salary_amount,
                'salary_status': salary_status,
            })

        today_sessions = (TeacherAttendance.objects
                          .filter(date=today, status='present')
                          .aggregate(total=Sum('session_count'))['total'] or 0)

        context.update({
            'today': today,
            'salary_year': salary_year,
            'salary_month': salary_month,
            'salary_period_label': f"{salary_year}/{salary_month:02d}",
            'salary_period_is_current': (salary_year == current_year and salary_month == current_month),
            'teachers_data': teachers_data,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'today_sessions': today_sessions,
        })
        return context


class CreateTeacherView(LoginRequiredMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'employ/teacher_form.html'
    success_url = reverse_lazy('employ:teachers')

    def form_valid(self, form):
        messages.success(self.request, 'تم إنشاء بيانات المعلم بنجاح.')
        return super().form_valid(form)


# -----------------------------
# الموارد البشرية (قائمة الموظفين)
# -----------------------------
class hr(ListView):
    template_name = 'employ/hr.html'
    model = Employee
    context_object_name = 'employees'

    def get_queryset(self):
        queryset = Employee.objects.select_related('user').all()
        position = self.request.GET.get('position')
        search = self.request.GET.get('search')

        if position:
            queryset = queryset.filter(position=position)

        if search:
            queryset = queryset.filter(user__first_name__icontains=search) | queryset.filter(
                user__last_name__icontains=search
            )

        return queryset


class EmployeeCreateView(CreateView):
    form_class = EmployeeRegistrationForm
    template_name = 'employ/employee_form.html'
    success_url = reverse_lazy('employ:hr')

    def form_valid(self, form):
        response = super().form_valid(form)  # self.object = created User
        messages.success(self.request, f'تم تسجيل الموظف {self.object.get_full_name() or self.object.username} بنجاح.')
        return response


class EmployeeUpdateView(UpdateView):
    model = Employee
    fields = ['position', 'phone_number', 'salary']
    template_name = 'employ/employee_update.html'
    success_url = reverse_lazy('employ:hr')

    def get_context_data(self, **kwargs):
        from django.contrib.auth.forms import SetPasswordForm
        context = super().get_context_data(**kwargs)
        context['password_form'] = SetPasswordForm(self.object.user)
        return context

    def form_valid(self, form):
        # تغيير كلمة المرور إن طُلب
        if 'change_password' in self.request.POST:
            from django.contrib.auth.forms import SetPasswordForm
            password_form = SetPasswordForm(self.object.user, self.request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(self.request, 'تم تغيير كلمة المرور بنجاح.')
            else:
                messages.error(self.request, 'خطأ في تغيير كلمة المرور.')
            return redirect(self.success_url)

        # تحديث بيانات المستخدم
        user = self.object.user
        user.username = self.request.POST.get('username', user.username)
        user.first_name = self.request.POST.get('first_name', user.first_name)
        user.last_name = self.request.POST.get('last_name', user.last_name)
        user.email = self.request.POST.get('email', user.email)
        user.save()

        response = super().form_valid(form)
        messages.success(self.request, 'تم تحديث بيانات الموظف بنجاح.')
        return response


class EmployeeDeleteView(DeleteView):
    model = Employee
    success_url = reverse_lazy('employ:hr')

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        employee_name = employee.user.get_full_name() or employee.user.get_username()

        # حذف المستخدم سيحذف الموظف (on_delete=CASCADE)
        employee.user.delete()

        messages.success(request, f'تم حذف الموظف {employee_name} بنجاح.')
        return HttpResponseRedirect(self.success_url)


def select_employee(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        return redirect('employ:employee_update', pk=employee_id)

    employees = Employee.objects.select_related('user').all()
    return render(request, 'employ/select_employee.html', {'employees': employees})


class EmployeeProfileView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employ/employee_profile.html'
    context_object_name = 'employee'

    def _get_period_from_request(self):
        today = timezone.now().date()
        year_param = self.request.GET.get('year')
        month_param = self.request.GET.get('month')

        def sanitize(value, default, low=1, high=12):
            try:
                ivalue = int(value)
                if low <= ivalue <= high:
                    return ivalue
            except (TypeError, ValueError):
                pass
            return default

        if year_param is not None or month_param is not None:
            year = sanitize(year_param, today.year, low=1900, high=2100)
            month = sanitize(month_param, today.month)
            period_date = today.replace(year=year, month=month, day=1)
        else:
            period_date = today
            year = today.year
            month = today.month
        return today, period_date, year, month

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = context['employee']
        today, period_date, salary_year, salary_month = self._get_period_from_request()

        # التحقق من وجود حقل employee في ExpenseEntry قبل استخدامه
        try:
            # التحقق من وجود الحقل أولاً
            ExpenseEntry._meta.get_field('employee')
            salary_qs = ExpenseEntry.objects.filter(employee=employee).select_related(
                'journal_entry'
            ).prefetch_related('journal_entry__transactions__account').order_by('-date', '-created_at')
            period_salary_qs = salary_qs.filter(date__year=salary_year, date__month=salary_month)
        except FieldDoesNotExist:
            # إذا لم يكن الحقل موجوداً، نستخدم فلتر بديل أو نعيد queryset فارغ
            salary_qs = ExpenseEntry.objects.none()
            period_salary_qs = ExpenseEntry.objects.none()

        salary_amount = employee.salary or Decimal('0')
        period_paid_total = period_salary_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        period_advances = list(EmployeeAdvance.objects.filter(
            employee=employee,
            is_repaid=False,
            date__year=salary_year,
            date__month=salary_month
        ))
        period_advance_outstanding = sum((adv.outstanding_amount for adv in period_advances), Decimal('0'))
        period_paid_total += period_advance_outstanding

        salary_status = period_salary_qs.exists() or (salary_amount > 0 and period_advance_outstanding >= salary_amount)
        salary_total_paid = salary_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        last_salary_payment = salary_qs.first()

        period_remaining_amount = salary_amount - period_paid_total
        if period_remaining_amount < Decimal('0'):
            period_remaining_amount = Decimal('0')

        salary_entries = []
        for payment in salary_qs[:10]:
            debit_account = None
            if payment.journal_entry:
                try:
                    debit_tx = payment.journal_entry.transactions.filter(is_debit=True).select_related('account').first()
                    if debit_tx and hasattr(debit_tx, 'account'):
                        debit_account = debit_tx.account
                except Exception:
                    debit_account = None
            salary_entries.append({
                'entry': payment,
                'debit_account': debit_account,
            })

        salary_account_code = f"501-{employee.pk:04d}"
        salary_account = Account.objects.filter(code=salary_account_code).first()

        vacations_qs = Vacation.objects.filter(employee=employee).order_by('-start_date')
        status_totals = dict(vacations_qs.values('status').annotate(total=Count('id')).values_list('status', 'total'))
        vacations_list = list(vacations_qs)
        vacation_status_breakdown = [
            {'code': code, 'label': label, 'count': status_totals.get(code, 0)}
            for code, label in Vacation.STATUS_CHOICES
        ]
        vacations_total = len(vacations_list)
        vacations_current_year = sum(1 for vac in vacations_list if vac.start_date.year == today.year)
        upcoming_vacations = [vac for vac in vacations_list if vac.start_date >= today][:5]
        pending_status = Vacation.STATUS_CHOICES[0][0] if Vacation.STATUS_CHOICES else None
        pending_vacations_count = status_totals.get(pending_status, 0) if pending_status else 0

        advances_qs = EmployeeAdvance.objects.filter(employee=employee).order_by('-date')
        advances_list = list(advances_qs)
        advance_outstanding_total = sum((adv.outstanding_amount for adv in advances_list), Decimal('0'))
        outstanding_advances = [adv for adv in advances_list if not adv.is_repaid]

        months = [
            (1, 'كانون الثاني'), (2, 'شباط'), (3, 'آذار'), (4, 'نيسان'),
            (5, 'أيار'), (6, 'حزيران'), (7, 'تموز'), (8, 'آب'),
            (9, 'أيلول'), (10, 'تشرين الأول'), (11, 'تشرين الثاني'), (12, 'كانون الأول')
        ]

        context.update({
            'salary_year': salary_year,
            'salary_month': salary_month,
            'salary_period_label': f"{salary_year}/{salary_month:02d}",
            'salary_period_is_current': (salary_year == today.year and salary_month == today.month),
            'salary_amount': salary_amount,
            'salary_status': salary_status,
            'salary_total_paid': salary_total_paid,
            'salary_period_paid_total': period_paid_total,
            'salary_period_remaining': period_remaining_amount,
            'salary_period_advance_outstanding': period_advance_outstanding,
            'salary_entries': salary_entries,
            'last_salary_payment': last_salary_payment,
            'salary_account': salary_account,
            'salary_account_code': salary_account_code,
            'vacations': vacations_list,
            'salary_period_advances': period_advances,
            'display_name': _employee_full_name(employee),
            'vacations_total': vacations_total,
            'vacations_current_year': vacations_current_year,
            'vacation_status_breakdown': vacation_status_breakdown,
            'vacation_pending_count': pending_vacations_count,
            'upcoming_vacations': upcoming_vacations,
            'advances': advances_list,
            'advances_total': len(advances_list),
            'advance_outstanding_total': advance_outstanding_total,
            'outstanding_advances_count': len(outstanding_advances),
            'months': months,
            'today': today,
        })
        return context


# -----------------------------
# الإجازات
# -----------------------------
class VacationListView(ListView):
    model = Vacation
    template_name = 'employ/vacation_list.html'
    context_object_name = 'vacations'

    def get_queryset(self):
        queryset = Vacation.objects.select_related('employee__user').all()

        # فلاتر
        employee_name = self.request.GET.get('employee_name')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if employee_name:
            queryset = queryset.filter(employee__user__first_name__icontains=employee_name) | queryset.filter(
                employee__user__last_name__icontains=employee_name
            )

        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset.order_by('-start_date')


class VacationCreateView(CreateView):
    model = Vacation
    form_class = AdminVacationForm
    template_name = 'employ/vacation_form.html'
    success_url = reverse_lazy('employ:vacation_list')

    def get_initial(self):
        initial = super().get_initial()
        employee_id = self.request.GET.get('employee')
        if employee_id:
            try:
                initial['employee'] = Employee.objects.get(pk=employee_id)
            except Employee.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'تم تسجيل الإجازة بنجاح.')
        return response


class VacationUpdateView(UpdateView):
    model = Vacation
    form_class = AdminVacationForm
    template_name = 'employ/vacation_form.html'
    success_url = reverse_lazy('employ:vacation_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'تم تحديث الإجازة بنجاح.')
        return response


# -----------------------------
# إدارة رواتب المدرسين (عرض)
# -----------------------------
class SalaryManagementView(TemplateView):
    template_name = 'employ/salary_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_year = int(self.request.GET.get('year', timezone.now().year))
        selected_month = int(self.request.GET.get('month', timezone.now().month))

        months = [
            (1, 'كانون الثاني'), (2, 'شباط'), (3, 'آذار'), (4, 'نيسان'),
            (5, 'أيار'), (6, 'حزيران'), (7, 'تموز'), (8, 'آب'),
            (9, 'أيلول'), (10, 'تشرين الأول'), (11, 'تشرين الثاني'), (12, 'كانون الأول')
        ]

        teachers = Teacher.objects.all()
        teachers_salary_data = []
        total_calculated_amount = Decimal('0.00')
        paid_count = 0
        unpaid_count = 0

        for teacher in teachers:
            monthly_sessions = teacher.get_monthly_sessions(selected_year, selected_month)
            calculated_salary = teacher.calculate_monthly_salary(selected_year, selected_month)
            salary_status = teacher.get_salary_status(selected_year, selected_month)

            teachers_salary_data.append({
                'teacher': teacher,
                'monthly_sessions': monthly_sessions,
                'calculated_salary': calculated_salary,
                'salary_status': salary_status
            })

            total_calculated_amount += calculated_salary
            if salary_status:
                paid_count += 1
            else:
                unpaid_count += 1

        context.update({
            'teachers_salary_data': teachers_salary_data,
            'selected_year': selected_year,
            'selected_month': selected_month,
            'months': months,
            'total_calculated_amount': total_calculated_amount,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'today': timezone.now().date()
        })

        return context


# -----------------------------
# قيد استحقاق راتب المدرس / دفعه
# -----------------------------
class CreateTeacherAccrualView(View):
    def post(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)

        def _sanitize_int(value, default, allowed=None):
            if value is None:
                return default
            cleaned = ''.join(ch for ch in str(value) if ch.isdigit())
            if cleaned:
                try:
                    numeric = int(cleaned)
                    if allowed and numeric not in allowed:
                        return default
                    return numeric
                except ValueError:
                    pass
            return default

        year = _sanitize_int(request.POST.get('year'), timezone.now().year)
        month = _sanitize_int(request.POST.get('month'), timezone.now().month, allowed=set(range(1, 13)))
        return_to_profile = request.POST.get('return_to_profile')

        try:
            accrual_entry = teacher.create_salary_accrual_entry(request.user, year, month)
            messages.success(
                request,
                f'تم إنشاء قيد استحقاق راتب {teacher.full_name} ({month:02d}/{year}) بنجاح. المرجع: {getattr(accrual_entry, "reference", accrual_entry.pk)}'
            )
        except Exception as e:
            messages.error(request, f'تعذر إنشاء قيد الاستحقاق: {e}')

        if return_to_profile:
            return redirect('employ:teacher_profile', pk=teacher.pk)
        return redirect('employ:salary_management')


class PayTeacherSalaryView(View):
    def post(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)

        def _sanitize_int(value, default, allowed=None):
            if value is None:
                return default
            cleaned = ''.join(ch for ch in str(value) if ch.isdigit())
            if cleaned:
                try:
                    numeric = int(cleaned)
                    if allowed and numeric not in allowed:
                        return default
                    return numeric
                except ValueError:
                    pass
            return default

        year = _sanitize_int(request.POST.get('year'), timezone.now().year)
        month = _sanitize_int(request.POST.get('month'), timezone.now().month, allowed=set(range(1, 13)))
        return_to_profile = request.POST.get('return_to_profile')

        gross_salary = teacher.calculate_monthly_salary(year, month)
        total_advances = teacher.get_total_advances(year, month)
        net_salary = teacher.calculate_net_salary(year, month)

        if gross_salary <= 0:
            messages.error(request, 'لا يمكن حساب راتب هذا المعلم.')
            if return_to_profile:
                return redirect('employ:teacher_profile', pk=teacher.pk)
            return redirect('employ:salary_management')

        if teacher.get_salary_status(year, month):
            messages.warning(request, f'راتب {teacher.full_name} مسجل بالفعل لشهر {month:02d}/{year}.')
            if return_to_profile:
                return redirect('employ:teacher_profile', pk=teacher.pk)
            return redirect('employ:salary_management')

        from accounts.models import JournalEntry
        accrual_exists = JournalEntry.objects.filter(
            description__icontains=f"Teacher salary accrual - {teacher.full_name}",
            entry_type='SALARY',
            is_posted=True
        ).exists()

        if not accrual_exists:
            messages.error(request, f'يجب إنشاء قيد الاستحقاق أولاً لراتب {teacher.full_name} عن شهر {month:02d}/{year}.')
            if return_to_profile:
                return redirect('employ:teacher_profile', pk=teacher.pk)
            return redirect('employ:salary_management')

        try:
            payment_entry = teacher.create_salary_payment_entry(request.user, year, month)
            messages.success(
                request,
                f'تم دفع راتب {teacher.full_name} ({month:02d}/{year}) بنجاح. '
                f'الإجمالي: {gross_salary}, السلف: {total_advances}, الصافي: {net_salary}'
            )
        except Exception as e:
            messages.error(request, f'تعذر تسجيل راتب {teacher.full_name}: {e}')
            if return_to_profile:
                return redirect('employ:teacher_profile', pk=teacher.pk)
            return redirect('employ:salary_management')

        if return_to_profile:
            return redirect('employ:teacher_profile', pk=teacher.pk)
        return redirect('employ:salary_management')


class TeacherProfileView(DetailView):
    model = Teacher
    template_name = 'employ/teacher_profile.html'
    context_object_name = 'teacher'

    def _get_period_from_request(self):
        today = timezone.now().date()
        year_param = self.request.GET.get('year')
        month_param = self.request.GET.get('month')

        def sanitize(value, default, low=1, high=12):
            try:
                ivalue = int(value)
                if low <= ivalue <= high:
                    return ivalue
            except (TypeError, ValueError):
                pass
            return default

        if year_param is not None or month_param is not None:
            year = sanitize(year_param, today.year, low=1900, high=2100)
            month = sanitize(month_param, today.month)
            period_date = today.replace(year=year, month=month, day=1)
        else:
            if today.day >= 28:
                period_date = today
            else:
                period_date = today.replace(day=1) - timedelta(days=1)
            year = period_date.year
            month = period_date.month

        return today, period_date, year, month

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.get_object()
        today, period_date, salary_year, salary_month = self._get_period_from_request()

        # التأكد من وجود قيد الاستحقاق
        from accounts.models import JournalEntry
        has_accrual_entry = JournalEntry.objects.filter(
            description__icontains=f"Teacher salary accrual - {teacher.full_name} ({salary_month:02d}/{salary_year})",
            entry_type='SALARY',
            is_posted=True
        ).exists()

        context['daily_sessions'] = teacher.get_daily_sessions(today)
        context['monthly_sessions'] = teacher.get_monthly_sessions(today.year, today.month)
        context['yearly_sessions'] = teacher.get_yearly_sessions(today.year)

        context['salary_year'] = salary_year
        context['salary_month'] = salary_month
        context['salary_period_date'] = period_date
        context['salary_period_label'] = f"{salary_year}/{salary_month:02d}"
        context['salary_period_is_current'] = (salary_year == today.year and salary_month == today.month)
        context['salary_amount'] = teacher.calculate_monthly_salary(salary_year, salary_month)
        context['monthly_salary'] = context['salary_amount']
        context['salary_status'] = teacher.get_salary_status(salary_year, salary_month)
        context['has_accrual_entry'] = has_accrual_entry

        context['daily_attendance'] = TeacherAttendance.objects.filter(teacher=teacher, date=today).first()

        monthly_attendance = TeacherAttendance.objects.filter(
            teacher=teacher,
            date__year=today.year,
            date__month=today.month
        )

        context['monthly_stats'] = {
            'present_days': monthly_attendance.filter(status='present').count(),
            'absent_days': monthly_attendance.filter(status='absent').count(),
            'total_days': monthly_attendance.count(),
        }

        yearly_attendance = TeacherAttendance.objects.filter(teacher=teacher, date__year=today.year)

        context['yearly_stats'] = {
            'present_days': yearly_attendance.filter(status='present').count(),
            'absent_days': yearly_attendance.filter(status='absent').count(),
            'total_days': yearly_attendance.count(),
            'total_sessions': yearly_attendance.filter(status='present').aggregate(total=Sum('session_count'))['total'] or 0,
        }

        context['today'] = today
        return context


class TeacherDeleteView(LoginRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'employ/teacher_confirm_delete.html'
    success_url = reverse_lazy('employ:teachers')

    def delete(self, request, *args, **kwargs):
        teacher = self.get_object()
        messages.success(request, f'تم حذف بيانات المعلم {teacher.full_name}.')
        return super().delete(request, *args, **kwargs)


# -----------------------------
# دفع راتب الموظف
# -----------------------------
class PayEmployeeSalaryView(View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)

        def _sanitize_int(value, default, allowed=None):
            if value is None:
                return default
            cleaned = ''.join(ch for ch in str(value) if ch.isdigit())
            if cleaned:
                try:
                    numeric = int(cleaned)
                    if allowed and numeric not in allowed:
                        return default
                    return numeric
                except ValueError:
                    pass
            return default

        year = _sanitize_int(request.POST.get('year'), timezone.now().year)
        month = _sanitize_int(request.POST.get('month'), timezone.now().month, allowed=set(range(1, 13)))
        return_to_profile = request.POST.get('return_to_profile')
        manual_advance_amount = request.POST.get('manual_advance_amount', '0')

        try:
            manual_advance_amount = Decimal(str(manual_advance_amount))
        except (ValueError, InvalidOperation):
            manual_advance_amount = Decimal('0')

        gross_salary = employee.salary or Decimal('0')
        if gross_salary <= 0:
            messages.error(request, 'لا يمكن حساب راتب هذا الموظف.')
            if return_to_profile:
                return redirect('employ:employee_profile', pk=employee.pk)
            return redirect('accounts:employee_financial_profile', entity_type='employee', pk=employee.pk)

        if employee.get_salary_status(year, month):
            messages.warning(request, f'راتب { _employee_full_name(employee) } مسجل بالفعل لشهر {month:02d}/{year}.')
            if return_to_profile:
                return redirect('employ:employee_profile', pk=employee.pk)
            return redirect('accounts:employee_financial_profile', entity_type='employee', pk=employee.pk)

        display_name = _employee_full_name(employee)
        net_salary = max(Decimal('0'), gross_salary - manual_advance_amount)

        try:
            from accounts.models import Account, JournalEntry, Transaction

            salary_account = employee.get_salary_account()
            cash_account, _ = Account.objects.get_or_create(
                code='1210',
                defaults={
                    'name': 'Cash',
                    'name_ar': 'النقدية',
                    'account_type': 'ASSET',
                    'is_active': True,
                }
            )

            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=f'Employee salary - {display_name} ({month:02d}/{year})',
                entry_type='SALARY',
                total_amount=gross_salary,
                created_by=request.user
            )

            # مدين: مصروف رواتب
            Transaction.objects.create(
                journal_entry=entry,
                account=salary_account,
                amount=gross_salary,
                is_debit=True,
                description=f'Salary expense - {display_name}'
            )

            # دائن: نقدية
            if net_salary > 0:
                Transaction.objects.create(
                    journal_entry=entry,
                    account=cash_account,
                    amount=net_salary,
                    is_debit=False,
                    description=f'Cash payment - {display_name}'
                )

            # دائن: سلف الموظف (خصم)
            if manual_advance_amount > 0:
                from accounts.models import get_or_create_employee_advance_account
                advance_account = get_or_create_employee_advance_account(employee)
                Transaction.objects.create(
                    journal_entry=entry,
                    account=advance_account,
                    amount=manual_advance_amount,
                    is_debit=False,
                    description=f'Advance deduction - {display_name}'
                )

            entry.post_entry(request.user)

            # التحقق من وجود حقل employee قبل إنشاء ExpenseEntry
            try:
                ExpenseEntry._meta.get_field('employee')
                ExpenseEntry.objects.create(
                    date=timezone.now().date(),
                    description=f'Salary - {display_name} ({month:02d}/{year})',
                    category='SALARY',
                    amount=gross_salary,
                    payment_method='CASH',
                    vendor=display_name or employee.user.get_username(),
                    notes=f'Gross: {gross_salary}, Manual Advances: {manual_advance_amount}, Net: {net_salary}',
                    created_by=request.user,
                    employee=employee,
                    journal_entry=entry
                )
            except FieldDoesNotExist:
                # إذا لم يكن الحقل موجوداً، ننشئ ExpenseEntry بدون حقل employee
                ExpenseEntry.objects.create(
                    date=timezone.now().date(),
                    description=f'Salary - {display_name} ({month:02d}/{year})',
                    category='SALARY',
                    amount=gross_salary,
                    payment_method='CASH',
                    vendor=display_name or employee.user.get_username(),
                    notes=f'Gross: {gross_salary}, Manual Advances: {manual_advance_amount}, Net: {net_salary}',
                    created_by=request.user,
                    journal_entry=entry
                )

            messages.success(
                request,
                f'تم تسجيل راتب {display_name} ({month:02d}/{year}) بنجاح. '
                f'الإجمالي: {gross_salary}, السلف: {manual_advance_amount}, الصافي: {net_salary}'
            )
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تسجيل الراتب: {e}')
            if return_to_profile:
                return redirect('employ:employee_profile', pk=employee.pk)
            return redirect('accounts:employee_financial_profile', entity_type='employee', pk=employee.pk)

        if return_to_profile:
            return redirect('employ:employee_profile', pk=employee.pk)
        return redirect('accounts:employee_financial_profile', entity_type='employee', pk=employee.pk)


# -----------------------------
# سلف المدرس
# -----------------------------
class TeacherAdvanceCreateView(LoginRequiredMixin, CreateView):
    template_name = 'employ/teacher_advance_form.html'
    fields = ['date', 'amount', 'purpose']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teacher'] = get_object_or_404(Teacher, pk=self.kwargs['teacher_id'])
        return context

    def form_valid(self, form):
        teacher = get_object_or_404(Teacher, pk=self.kwargs['teacher_id'])

        from accounts.models import TeacherAdvance
        advance = TeacherAdvance.objects.create(
            teacher=teacher,
            date=form.cleaned_data['date'],
            amount=form.cleaned_data['amount'],
            purpose=form.cleaned_data['purpose'],
            created_by=self.request.user
        )

        try:
            advance.create_advance_journal_entry(self.request.user)
            messages.success(self.request, f'تم إنشاء سلفة للمدرس {teacher.full_name} بمبلغ {advance.amount} ل.س')
        except Exception as e:
            messages.error(self.request, f'خطأ في إنشاء القيد المحاسبي: {e}')

        return redirect('employ:teacher_profile', pk=teacher.pk)

    def get_success_url(self):
        return reverse('employ:teacher_profile', kwargs={'pk': self.kwargs['teacher_id']})


class TeacherAdvanceListView(LoginRequiredMixin, ListView):
    """قائمة سلف مدرس معيّن بحسب teacher_id في الـ URL"""
    template_name = 'employ/teacher_advance_list.html'
    context_object_name = 'advances'

    def get_queryset(self):
        from accounts.models import TeacherAdvance
        teacher = get_object_or_404(Teacher, pk=self.kwargs['teacher_id'])
        return (TeacherAdvance.objects
                .filter(teacher=teacher)
                .select_related('teacher')
                .order_by('-date', '-created_at'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = get_object_or_404(Teacher, pk=self.kwargs['teacher_id'])
        advances = context['advances']
        context.update({
            'teacher': teacher,
            'total_advances': advances.count(),
            'outstanding_count': advances.filter(is_repaid=False).count(),
            'total_amount': sum(a.amount for a in advances),
            'total_outstanding_amount': sum(a.outstanding_amount for a in advances if not a.is_repaid),
        })
        return context


# -----------------------------
# نظرة عامة على الشؤون المالية للموظفين
# -----------------------------
class EmployeeFinancialOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/employee_financial_overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from employ.models import Employee, Teacher
        
        # Get employee data
        employees = Employee.objects.select_related('user').all()
        employee_rows = []
        
        for employee in employees:
            # Get salary payments (guard field existence)
            try:
                ExpenseEntry._meta.get_field('employee')
                salary_payments = ExpenseEntry.objects.filter(employee=employee).order_by('-date')
            except FieldDoesNotExist:
                salary_payments = ExpenseEntry.objects.none()
            last_payment = salary_payments.first()
            total_paid = salary_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Get outstanding advances
            outstanding_advances = EmployeeAdvance.objects.filter(
                employee=employee, is_repaid=False
            ).aggregate(total=Sum('outstanding_amount'))['total'] or Decimal('0')
            
            employee_rows.append({
                'employee': employee,
                'display_name': _employee_full_name(employee),
                'position': employee.get_position_display(),
                'monthly_salary': employee.salary,
                'total_paid': total_paid,
                'outstanding_advances': outstanding_advances,
                'last_payment': last_payment,
                'detail_url': reverse('accounts:employee_financial_profile', kwargs={'entity_type': 'employee', 'pk': employee.pk})
            })
        
        # Get teacher data
        teachers = Teacher.objects.all()
        teacher_rows = []
        
        for teacher in teachers:
            # Get salary payments (guard field existence)
            try:
                ExpenseEntry._meta.get_field('teacher')
                salary_payments = ExpenseEntry.objects.filter(teacher=teacher).order_by('-date')
            except FieldDoesNotExist:
                salary_payments = ExpenseEntry.objects.none()
            last_payment = salary_payments.first()
            total_paid = salary_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            teacher_rows.append({
                'teacher': teacher,
                'display_name': teacher.full_name,
                'monthly_salary': teacher.calculate_monthly_salary(),
                'total_paid': total_paid,
                'last_payment': last_payment,
                'detail_url': reverse('accounts:employee_financial_profile', kwargs={'entity_type': 'teacher', 'pk': teacher.pk})
            })

        context.update({
            'employee_rows': employee_rows,
            'teacher_rows': teacher_rows,
            'total_employees': len(employee_rows),
            'total_teachers': len(teacher_rows),
        })
        
        return context


def no_permission(request):
    # يستخدم للروابط المعروضة بدون إذن: يفتح 503 مباشرة
    return render(request, "503.html", status=503)