from django.db import models
from django.core.validators import MinLengthValidator
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


# =============================
# Employee & Permissions
# =============================

class Employee(models.Model):
    """الموظف: مرتبط بمستخدم النظام، ويُمنح صلاحيات ميزات مباشرةً عبر EmployeePermission."""

    # حقل الربط مع مستخدم Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')

    # حقول اختيارية للإدارة
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='رقم الهاتف')
    hire_date = models.DateField(blank=True, null=True, verbose_name='تاريخ التعيين')

    # الراتب الشهري الثابت (تستخدمه الفيوز الخاصة بملف الموظف ودفع الراتب)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='راتب شهري')

    # مسمى وظيفي (اختياري، لا يوزّع صلاحيات تلقائيًا)
    POSITION_CHOICES = [
        ('admin', 'مسؤول'),
        ('accountant', 'محاسب'),
        ('hr', 'موارد بشرية'),
        ('staff', 'موظف'),
    ]
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='staff', verbose_name='الوظيفة')

    def __str__(self):
        return self.full_name or (self.user.get_username() if self.user_id else 'Employee')

    # اسم العرض للموظف (يحل مشكلة AttributeError: full_name)
    @property
    def full_name(self):
        if self.user_id:
            return self.user.get_full_name() or self.user.get_username()
        return ''

    # فحص صلاحية معينة
    def has_permission(self, code: str) -> bool:
        return self.permissions.filter(permission=code, is_granted=True).exists()

    # جميع الصلاحيات (ممنوحة/غير ممنوحة) بشكل جاهز للعرض
    def get_all_permissions(self):
        granted = set(self.permissions.filter(is_granted=True).values_list('permission', flat=True))
        return [
            {'code': code, 'label': label, 'is_granted': code in granted}
            for code, label in EmployeePermission.PERMISSION_CHOICES
        ]

    # حالة راتب شهر معيّن (مطلوبة في الفيوز)
    def get_salary_status(self, year=None, month=None):
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        try:
            from accounts.models import ExpenseEntry
            qs = ExpenseEntry.objects.filter(employee=self, date__year=year, date__month=month)
            if qs.exists():
                return True

            # دعم البحث القديم بالاسم
            name_hint = (self.full_name or '').strip()
            if name_hint:
                legacy_qs = ExpenseEntry.objects.filter(
                    description__icontains=name_hint,
                    category__in=['SALARY', 'TEACHER_SALARY'],
                    date__year=year,
                    date__month=month
                )
                if legacy_qs.exists():
                    return True
            return False
        except Exception:
            return False

    # حساب مصروف رواتب الموظف (يُستخدم عند إنشاء قيود)
    def get_salary_account(self):
        from accounts.models import get_or_create_employee_salary_account
        return get_or_create_employee_salary_account(self)


class EmployeePermission(models.Model):
    """صلاحيات الميزات تُمنح مباشرةً للموظّف (ليست أدوار ولا Groups)."""

    PERMISSION_CHOICES = [
        # == Student Management ==
        ('students_view', 'عرض قائمة الطلاب'),
        ('students_create', 'إضافة طالب جديد'),
        ('students_edit', 'تعديل بيانات الطلاب'),
        ('students_delete', 'حذف الطلاب'),
        ('students_profile', 'عرض ملف الطالب'),
        ('students_receipt', 'قطع إيصالات الطلاب'),
        ('students_statement', 'كشف حساب الطالب'),
        ('students_register_course', 'تسجيل الطالب في دورة'),
        ('students_withdraw', 'سحب الطالب من دورة'),
        ('students_export', 'تصدير بيانات الطلاب'),
        # == Teacher Management ==
        ('teachers_view', 'عرض قائمة المدرسين'),
        ('teachers_create', 'إضافة مدرس جديد'),
        ('teachers_edit', 'تعديل بيانات المدرسين'),
        ('teachers_delete', 'حذف المدرسين'),
        ('teachers_profile', 'عرض ملف المدرس'),
        ('teachers_salary', 'إدارة رواتب المدرسين'),
        ('teachers_salary_pay', 'دفع رواتب المدرسين'),
        ('teachers_salary_accrual', 'إنشاء قيود استحقاق الرواتب'),
        ('teachers_advance', 'إدارة سلف المدرسين'),
        ('teachers_advance_create', 'إنشاء سلفة للمدرس'),
        # == Attendance ==
        ('attendance_view', 'عرض سجل الحضور'),
        ('attendance_take', 'تسجيل حضور الطلاب'),
        ('attendance_edit', 'تعديل سجل الحضور'),
        ('attendance_export', 'تصدير سجل الحضور'),
        ('attendance_teacher_view', 'عرض حضور المدرسين'),
        ('attendance_teacher_take', 'تسجيل حضور المدرسين'),
        ('attendance_teacher_export', 'تصدير حضور المدرسين'),
        # == Classroom ==
        ('classroom_view', 'عرض قائمة الشعب'),
        ('classroom_create', 'إنشاء شعبة جديدة'),
        ('classroom_edit', 'تعديل الشعب'),
        ('classroom_delete', 'حذف الشعب'),
        ('classroom_assign', 'تعيين الطلاب للشعب'),
        ('classroom_students', 'عرض طلاب الشعبة'),
        ('classroom_subjects', 'إدارة مواد الشعبة'),
        ('classroom_export', 'تصدير بيانات الشعب'),
        # == Grades ==
        ('grades_view', 'عرض العلامات'),
        ('grades_edit', 'تعديل العلامات'),
        ('grades_export', 'تصدير العلامات لإكسل'),
        ('grades_print', 'طباعة كشوف العلامات'),
        ('grades_custom_print', 'طباعة مخصصة للعلامات'),
        # == Courses/Subjects ==
        ('courses_view', 'عرض قائمة المواد'),
        ('courses_create', 'إضافة مادة جديدة'),
        ('courses_edit', 'تعديل المواد'),
        ('courses_delete', 'حذف المواد'),
        ('courses_assign_teachers', 'تعيين المدرسين للمواد'),
        # == Accounting ==
        ('accounting_dashboard', 'لوحة تحكم المحاسبة'),
        ('accounting_view', 'عرض النظام المحاسبي'),
        ('accounting_entries', 'إنشاء وتعديل قيود اليومية'),
        ('accounting_entries_post', 'ترحيل قيود اليومية'),
        ('accounting_accounts', 'إدارة دليل الحسابات'),
        ('accounting_accounts_create', 'إنشاء حسابات جديدة'),
        ('accounting_reports', 'عرض التقارير المالية'),
        ('accounting_trial_balance', 'ميزان المراجعة'),
        ('accounting_income_statement', 'قائمة الدخل'),
        ('accounting_balance_sheet', 'الميزانية العمومية'),
        ('accounting_ledger', 'دفاتر الأستاذ'),
        ('accounting_receipts', 'إيصالات الطلاب'),
        ('accounting_receipts_create', 'إنشاء إيصالات جديدة'),
        ('accounting_expenses', 'إدارة المصروفات'),
        ('accounting_expenses_create', 'تسجيل مصروفات جديدة'),
        ('accounting_budgets', 'إدارة الميزانيات'),
        ('accounting_periods', 'الفترات المحاسبية'),
        ('accounting_cost_centers', 'مراكز التكلفة'),
        ('accounting_outstanding', 'تقارير المتبقي على الطلاب'),
        ('accounting_export', 'تصدير التقارير المالية'),
        # == HR ==
        ('hr_dashboard', 'لوحة تحكم الموارد البشرية'),
        ('hr_view', 'عرض قائمة الموظفين'),
        ('hr_create', 'تسجيل موظف جديد'),
        ('hr_edit', 'تعديل بيانات الموظفين'),
        ('hr_delete', 'حذف الموظفين'),
        ('hr_profile', 'عرض ملف الموظف'),
        ('hr_permissions', 'إدارة صلاحيات الموظفين'),
        ('hr_salary', 'إدارة رواتب الموظفين'),
        ('hr_salary_pay', 'دفع رواتب الموظفين'),
        ('hr_advances', 'إدارة سلف الموظفين'),
        ('hr_advances_create', 'إنشاء سلفة للموظف'),
        ('hr_vacations', 'إدارة إجازات الموظفين'),
        ('hr_vacations_approve', 'الموافقة على الإجازات'),
        # == System ==
        ('admin_dashboard', 'الوصول للوحة التحكم الرئيسية'),
        ('admin_settings', 'إعدادات النظام العامة'),
        ('admin_users', 'إدارة المستخدمين والحسابات'),
        ('admin_backup', 'النسخ الاحتياطي واستعادة البيانات'),
        ('admin_logs', 'عرض سجلات النظام'),
        ('admin_database', 'إدارة قاعدة البيانات'),
        ('admin_maintenance', 'صيانة النظام'),
        # == Reports ==
        ('reports_dashboard', 'لوحة تحكم التقارير'),
        ('reports_students', 'تقارير الطلاب وإحصائياتهم'),
        ('reports_students_export', 'تصدير تقارير الطلاب'),
        ('reports_teachers', 'تقارير المدرسين وأدائهم'),
        ('reports_teachers_export', 'تصدير تقارير المدرسين'),
        ('reports_financial', 'التقارير المالية والمحاسبية'),
        ('reports_financial_export', 'تصدير التقارير المالية'),
        ('reports_attendance', 'تقارير الحضور والغياب'),
        ('reports_attendance_export', 'تصدير تقارير الحضور'),
        ('reports_grades', 'تقارير العلامات والدرجات'),
        ('reports_grades_export', 'تصدير تقارير العلامات'),
        ('reports_custom', 'تقارير مخصصة'),
        # == Accounting Courses ==
        ('course_accounting_view', 'عرض دورات النظام المحاسبي'),
        ('course_accounting_create', 'إنشاء دورة جديدة'),
        ('course_accounting_edit', 'تعديل الدورات'),
        ('course_accounting_pricing', 'إدارة أسعار الدورات'),
        # == Inventory & Assets ==
        ('inventory_view', 'عرض المخزون'),
        ('inventory_manage', 'إدارة المخزون'),
        ('assets_view', 'عرض الأصول'),
        ('assets_manage', 'إدارة الأصول'),
        # == Marketing ==
        ('marketing_campaigns', 'إدارة الحملات التسويقية'),
        ('marketing_leads', 'إدارة العملاء المحتملين'),
        ('marketing_analytics', 'تحليلات التسويق'),
        # == Quality ==
        ('quality_surveys', 'استطلاعات رضا الطلاب'),
        ('quality_feedback', 'إدارة التغذية الراجعة'),
        ('quality_evaluation', 'تقييم المدرسين'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='permissions')
    permission = models.CharField(max_length=50, choices=PERMISSION_CHOICES)
    is_granted = models.BooleanField(default=False, verbose_name='ممنوح')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='مُنح بواسطة')
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ المنح')

    class Meta:
        unique_together = ('employee', 'permission')
        verbose_name = 'صلاحية موظف'
        verbose_name_plural = 'صلاحيات الموظفين'

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_permission_display()}"


# =============================
# Teacher
# =============================

class Teacher(models.Model):
    class BranchChoices(models.TextChoices):
        LITERARY = 'أدبي', 'أدبي'
        SCIENTIFIC = 'علمي', 'علمي'
        NINTH_GRADE = 'تاسع', 'الصف التاسع'

    full_name = models.CharField(
        max_length=100,
        verbose_name='الاسم الكامل',
        validators=[MinLengthValidator(3)]
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='رقم الهاتف',
        validators=[MinLengthValidator(8)]
    )
    branches = models.CharField(
        max_length=100,
        verbose_name='الفروع',
        help_text='الفروع التي يدرّسها المدرّس مفصولة بفاصلة'
    )
    hire_date = models.DateField(default=date.today, verbose_name='تاريخ التعيين')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')

    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        verbose_name='أجر الساعة',
        help_text='الأجر عن كل حصة دراسية'
    )
    monthly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        verbose_name='راتب شهري ثابت',
        help_text='يستخدم مع نوع الراتب الشهري أو المختلط'
    )
    salary_type = models.CharField(
        max_length=20,
        choices=[
            ('hourly', 'ساعي'),
            ('monthly', 'شهري ثابت'),
            ('mixed', 'مختلط (شهري + ساعي)')
        ],
        default='hourly',
        verbose_name='نوع الراتب'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    def get_branches_list(self):
        if self.branches:
            return [branch.strip() for branch in self.branches.split(',') if branch.strip()]
        return []

    class Meta:
        verbose_name = 'مدرّس'
        verbose_name_plural = 'مدرّسون'
        ordering = ['-created_at']

    def get_daily_sessions(self, date=None):
        if date is None:
            date = timezone.now().date()
        from attendance.models import TeacherAttendance
        attendance = TeacherAttendance.objects.filter(
            teacher=self,
            date=date,
            status='present'
        ).first()
        return attendance.session_count if attendance else 0

    def get_monthly_sessions(self, year=None, month=None):
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        from attendance.models import TeacherAttendance
        return TeacherAttendance.objects.filter(
            teacher=self,
            date__year=year,
            date__month=month,
            status='present'
        ).aggregate(total=Sum('session_count'))['total'] or 0

    def get_yearly_sessions(self, year=None):
        if year is None:
            year = timezone.now().year
        from attendance.models import TeacherAttendance
        return TeacherAttendance.objects.filter(
            teacher=self,
            date__year=year,
            status='present'
        ).aggregate(total=Sum('session_count'))['total'] or 0

    def calculate_monthly_salary(self, year=None, month=None):
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        monthly_sessions = self.get_monthly_sessions(year, month)
        if self.salary_type == 'hourly':
            return Decimal(monthly_sessions) * (self.hourly_rate or Decimal('0'))
        if self.salary_type == 'monthly':
            return self.monthly_salary or Decimal('0')
        if self.salary_type == 'mixed':
            monthly_base = self.monthly_salary or Decimal('0')
            hourly_total = Decimal(monthly_sessions) * (self.hourly_rate or Decimal('0'))
            return monthly_base + hourly_total
        return Decimal('0.00')

    def get_salary_account(self):
        from accounts.models import get_or_create_teacher_salary_account
        return get_or_create_teacher_salary_account(self)

    @property
    def salary_account(self):
        return self.get_salary_account()

    def get_salary_status(self, year=None, month=None):
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        try:
            from accounts.models import ExpenseEntry
            salary_qs = ExpenseEntry.objects.filter(
                teacher=self,
                date__year=year,
                date__month=month
            )
            if salary_qs.exists():
                return True

            name_hint = (self.full_name or '').strip()
            if name_hint:
                legacy_qs = ExpenseEntry.objects.filter(
                    teacher__isnull=True,
                    category__in=['SALARY', 'TEACHER_SALARY'],
                    date__year=year,
                    date__month=month
                ).filter(description__icontains=name_hint)
                if legacy_qs.exists():
                    return True
            return False
        except Exception:
            return False

    def get_total_advances(self, year=None, month=None):
        """Get total outstanding advances for teacher in a specific period"""
        try:
            from accounts.models import TeacherAdvance
            advances_qs = TeacherAdvance.objects.filter(teacher=self, is_repaid=False)
            if year is not None and month is not None:
                advances_qs = advances_qs.filter(date__year=year, date__month=month)
            return sum(advance.outstanding_amount for advance in advances_qs)
        except Exception:
            return Decimal('0.00')

    def calculate_net_salary(self, year=None, month=None):
        """Calculate net salary after advance deductions"""
        gross_salary = self.calculate_monthly_salary(year, month)
        total_advances = self.get_total_advances(year, month)
        return max(Decimal('0.00'), gross_salary - total_advances)

    def get_teacher_dues_account(self):
        """Get teacher dues account"""
        from accounts.models import get_or_create_teacher_dues_account
        return get_or_create_teacher_dues_account(self)

    def get_teacher_advance_account(self):
        """Get teacher advance account"""
        from accounts.models import get_or_create_teacher_advance_account
        return get_or_create_teacher_advance_account(self)

    def create_salary_accrual_entry(self, user, year=None, month=None):
        """Create salary accrual entry (DR: Salary Expense, CR: Teacher Dues)"""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month

        gross_salary = self.calculate_monthly_salary(year, month)
        if gross_salary <= 0:
            raise ValueError("No salary calculated for this period")

        # Check if accrual already exists
        from accounts.models import JournalEntry
        period_description = f"Teacher salary accrual - {self.full_name} ({month:02d}/{year})"
        existing_accrual = JournalEntry.objects.filter(
            description=period_description,
            entry_type='SALARY'
        ).first()

        if existing_accrual:
            return existing_accrual

        # Get accounts
        from accounts.models import Transaction
        teacher_salary_account = self.get_salary_account()
        teacher_dues_account = self.get_teacher_dues_account()

        # Create accrual entry
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=period_description,
            entry_type='SALARY',
            total_amount=gross_salary,
            created_by=user
        )

        # DR: Salary Expense
        Transaction.objects.create(
            journal_entry=entry,
            account=teacher_salary_account,
            amount=gross_salary,
            is_debit=True,
            description=f"Salary expense - {self.full_name}"
        )

        # CR: Teacher Dues
        Transaction.objects.create(
            journal_entry=entry,
            account=teacher_dues_account,
            amount=gross_salary,
            is_debit=False,
            description=f"Salary due - {self.full_name}"
        )

        entry.post_entry(user)
        return entry

    def create_salary_payment_entry(self, user, year=None, month=None):
        """Create salary payment entry with advance deduction"""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month

        gross_salary = self.calculate_monthly_salary(year, month)
        total_advances = self.get_total_advances(year, month)
        net_salary = max(Decimal('0.00'), gross_salary - total_advances)

        if gross_salary <= 0:
            raise ValueError("No salary calculated for this period")

        # Get accounts
        from accounts.models import Account, JournalEntry, Transaction
        teacher_dues_account = self.get_teacher_dues_account()
        cash_account, _ = Account.objects.get_or_create(
            code='121',
            defaults={
                'name': 'Cash',
                'name_ar': 'النقدية',
                'account_type': 'ASSET',
                'is_active': True,
            }
        )

        if total_advances > 0:
            teacher_advance_account = self.get_teacher_advance_account()

        # Create payment entry
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f"Teacher salary payment - {self.full_name} ({month:02d}/{year})",
            entry_type='SALARY',
            total_amount=gross_salary,
            created_by=user
        )

        # Debit: Teacher Dues (full salary)
        Transaction.objects.create(
            journal_entry=entry,
            account=teacher_dues_account,
            amount=gross_salary,
            is_debit=True,
            description=f"Salary payment - {self.full_name}"
        )

        # Credit: Cash (net amount)
        if net_salary > 0:
            Transaction.objects.create(
                journal_entry=entry,
                account=cash_account,
                amount=net_salary,
                is_debit=False,
                description=f"Cash payment - {self.full_name}"
            )

        # Credit: Teacher Advance (advance amount)
        if total_advances > 0:
            Transaction.objects.create(
                journal_entry=entry,
                account=teacher_advance_account,
                amount=total_advances,
                is_debit=False,
                description=f"Advance deduction - {self.full_name}"
            )

            # Mark advances as repaid
            from accounts.models import TeacherAdvance
            advances = TeacherAdvance.objects.filter(
                teacher=self,
                date__year=year,
                date__month=month,
                is_repaid=False
            )
            for advance in advances:
                advance.is_repaid = True
                advance.repaid_amount = advance.amount
                advance.save(update_fields=['is_repaid', 'repaid_amount'])

        # Post the entry
        entry.post_entry(user)

        # Create ExpenseEntry for tracking
        from accounts.models import ExpenseEntry
        ExpenseEntry.objects.create(
            date=timezone.now().date(),
            description=f"Teacher salary - {self.full_name} ({month:02d}/{year})",
            category='TEACHER_SALARY',
            amount=gross_salary,
            payment_method='CASH',
            vendor=self.full_name,
            notes=f'Gross: {gross_salary}, Advances: {total_advances}, Net: {net_salary}',
            created_by=user,
            teacher=self,
            journal_entry=entry
        )

        return entry


# =============================
# Vacation
# =============================

class Vacation(models.Model):
    VACATION_TYPES = [
        ('يومية', 'يومية'),
        ('طارئة', 'طارئة'),
        ('مرضية', 'مرضية'),
    ]

    STATUS_CHOICES = [
        ('معلقة', 'معلقة'),
        ('موافق', 'موافق'),
        ('غير موافق', 'غير موافق'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vacations')
    vacation_type = models.CharField(max_length=20, choices=VACATION_TYPES, verbose_name='نوع الإجازة')
    reason = models.TextField(verbose_name='سبب الإجازة')
    start_date = models.DateField(verbose_name='تاريخ بدء الإجازة')
    end_date = models.DateField(verbose_name='تاريخ انتهاء الإجازة')
    submission_date = models.DateField(auto_now_add=True, verbose_name='تاريخ تقديم الطلب')
    is_replacement_secured = models.BooleanField(default=False, verbose_name='تم تأمين البديل')
    manager_opinion = models.TextField(blank=True, null=True, verbose_name='رأي المدير')
    general_manager_opinion = models.TextField(blank=True, null=True, verbose_name='رأي المدير العام')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='معلقة')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"إجازة {self.employee.full_name} - {self.get_vacation_type_display()}"

    class Meta:
        verbose_name = 'إجازة'
        verbose_name_plural = 'الإجازات'
        ordering = ['-created_at']


# =============================
# Signals
# =============================

@receiver(post_save, sender=Employee)
def ensure_employee_salary_account(sender, instance, **kwargs):
    from accounts.models import get_or_create_employee_salary_account
    get_or_create_employee_salary_account(instance)


@receiver(post_save, sender=Teacher)
def ensure_teacher_salary_account(sender, instance, **kwargs):
    from accounts.models import get_or_create_teacher_salary_account
    get_or_create_teacher_salary_account(instance)
