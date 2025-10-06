from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
import uuid


class NumberSequence(models.Model):
    """Track sequential numbers for various document types"""
    key = models.CharField(max_length=64, unique=True)
    last_value = models.BigIntegerField(default=0)

    @classmethod
    def next_value(cls, key):
        seq, created = cls.objects.get_or_create(key=key, defaults={'last_value': 0})
        seq.last_value += 1
        seq.save(update_fields=['last_value'])
        return seq.last_value


class Account(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'الأصول / Assets'),
        ('LIABILITY', 'الخصوم / Liabilities'),
        ('EQUITY', 'حقوق الملكية / Equity'),
        ('REVENUE', 'الإيرادات / Revenue'),
        ('EXPENSE', 'المصروفات / Expenses'),
    ]

    code = models.CharField(max_length=20, unique=True, verbose_name='رمز الحساب / Account Code')
    name = models.CharField(max_length=200, verbose_name='اسم الحساب / Account Name')
    name_ar = models.CharField(max_length=200, blank=True, verbose_name='الاسم بالعربية / Arabic Name')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, verbose_name='نوع الحساب / Account Type')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='الحساب الأب / Parent Account')
    description = models.TextField(blank=True, verbose_name='الوصف / Description')
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد / Balance')
    
    # Special account flags
    is_course_account = models.BooleanField(default=False, verbose_name='حساب الدورة / Course Account')
    course_name = models.CharField(max_length=200, blank=True, verbose_name='اسم الدورة / Course Name')
    is_student_account = models.BooleanField(default=False, verbose_name='حساب الطالب / Student Account')
    student_name = models.CharField(max_length=200, blank=True, verbose_name='اسم الطالب / Student Name')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'الحساب / Account'
        verbose_name_plural = 'الحسابات / Accounts'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.display_name}"

    @property
    def display_name(self):
        return self.name_ar if self.name_ar else self.name

    def get_absolute_url(self):
        return reverse('accounts:account_detail', kwargs={'pk': self.pk})

    def get_debit_balance(self):
        """Get total debit amount for this account"""
        return self.transactions.filter(is_debit=True).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')

    def get_credit_balance(self):
        """Get total credit amount for this account"""
        return self.transactions.filter(is_debit=False).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')

    def get_net_balance(self):
        """Calculate net balance based on account type"""
        debit_total = self.get_debit_balance()
        credit_total = self.get_credit_balance()
        
        if self.account_type in ['ASSET', 'EXPENSE']:
            return debit_total - credit_total
        else:  # LIABILITY, EQUITY, REVENUE
            return credit_total - debit_total

    @property
    def rollup_balance(self):
        """Get balance including children accounts (with recursion protection)"""
        return self._calculate_rollup_balance(set())
    
    def _calculate_rollup_balance(self, visited_ids):
        """Calculate rollup balance with recursion protection"""
        if self.id in visited_ids:
            return Decimal('0.00')  # Prevent infinite recursion
        
        visited_ids.add(self.id)
        own_balance = self.get_net_balance()
        children_balance = Decimal('0.00')
        
        for child in self.children.all():
            children_balance += child._calculate_rollup_balance(visited_ids.copy())
        
        return own_balance + children_balance

    def transactions_with_descendants(self):
        """Get all transactions for this account and its descendants"""
        account_ids = [self.id]
        
        def collect_children(account):
            for child in account.children.all():
                account_ids.append(child.id)
                collect_children(child)
        
        collect_children(self)
        return Transaction.objects.filter(account_id__in=account_ids)

    def recalculate_tree_balances(self):
        """Recalculate balances for this account and all its children"""
        # Recalculate children first (bottom-up)
        for child in self.children.all():
            child.recalculate_tree_balances()
        
        # Then recalculate this account
        self.balance = self.get_net_balance()
        self.save(update_fields=['balance'])

    @classmethod
    def rebuild_all_balances(cls):
        """Rebuild all account balances from transactions"""
        for account in cls.objects.all():
            account.balance = account.get_net_balance()
            account.save(update_fields=['balance'])

    @classmethod
    def get_or_create_student_ar_account(cls, student):
        """Get or create AR account for student"""
        # Ensure AR parent exists
        ar_parent, _ = cls.objects.get_or_create(
            code='1251',
            defaults={
                'name': 'Accounts Receivable - Students',
                'name_ar': 'ذمم الطلاب المدينة',
                'account_type': 'ASSET',
                'is_active': True,
            }
        )
        
        # Create student-specific AR account
        student_code = f"1251-{student.id:03d}"
        account, created = cls.objects.get_or_create(
            code=student_code,
            defaults={
                'name': f"AR - {student.full_name}",
                'name_ar': f"ذمة {student.full_name}",
                'account_type': 'ASSET',
                'parent': ar_parent,
                'is_student_account': True,
                'student_name': student.full_name,
                'is_active': True,
            }
        )
        return account

    @classmethod
    def get_or_create_course_deferred_account(cls, course):
        """Get or create deferred revenue account for course"""
        # Ensure deferred revenue parent exists
        deferred_parent, _ = cls.objects.get_or_create(
            code='21',
            defaults={
                'name': 'Deferred Revenue - Courses',
                'name_ar': 'إيرادات مؤجلة - الدورات',
                'account_type': 'LIABILITY',
                'is_active': True,
            }
        )


        # =========================

        
        # Create course-specific deferred revenue account
        course_code = f"21001-{course.id:03d}"
        account, created = cls.objects.get_or_create(
            code=course_code,
            defaults={
                'name': f"Deferred Revenue - {course.name}",
                'name_ar': f"إيرادات مؤجلة - {course.name}",
                'account_type': 'LIABILITY',
                'parent': deferred_parent,
                'is_course_account': True,
                'course_name': course.name,
                'is_active': True,
            }
        )


        # ===================
               # Create course-specific deferred revenue account
        course_code = f"4101-{course.id:03d}"
        account, created = cls.objects.get_or_create(
            code=course_code,
            defaults={
                'name': f"Deferred Revenue - {course.name}",
                'name_ar': f"  إيرادات  دورة - {course.name}",
                'account_type': 'REVENUE',
                'parent': deferred_parent,
                'is_course_account': True,
                'course_name': course.name,
                'is_active': True,
            }
        )
        return account


class CostCenter(models.Model):
    COST_CENTER_TYPE_CHOICES = [
        ('ACADEMIC', 'أكاديمي / Academic'),
        ('ADMINISTRATIVE', 'إداري / Administrative'),
        ('OPERATIONAL', 'تشغيلي / Operational'),
        ('SUPPORT', 'دعم / Support'),
    ]
    
    code = models.CharField(max_length=20, unique=True, verbose_name='الرمز / Code')
    name = models.CharField(max_length=100, verbose_name='الاسم / Name')
    name_ar = models.CharField(max_length=100, blank=True, verbose_name='الاسم بالعربية / Arabic Name')
    description = models.TextField(blank=True, verbose_name='الوصف / Description')
    cost_center_type = models.CharField(max_length=20, choices=COST_CENTER_TYPE_CHOICES, default='ACADEMIC', verbose_name='نوع مركز التكلفة / Cost Center Type')
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    
    # Manager information
    manager_name = models.CharField(max_length=200, blank=True, verbose_name='اسم المدير / Manager Name')
    manager_phone = models.CharField(max_length=20, blank=True, verbose_name='هاتف المدير / Manager Phone')
    
    # Budget information
    annual_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الميزانية السنوية / Annual Budget')
    monthly_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الميزانية الشهرية / Monthly Budget')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مركز التكلفة / Cost Center'
        verbose_name_plural = 'مراكز التكلفة / Cost Centers'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name_ar if self.name_ar else self.name}"
    
    def get_total_expenses(self, start_date=None, end_date=None):
        """Get total expenses for this cost center in a period"""
        from django.db.models import Sum
        transactions = self.transaction_set.all()
        
        if start_date:
            transactions = transactions.filter(journal_entry__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(journal_entry__date__lte=end_date)
        
        # Sum debit transactions (expenses)
        return transactions.filter(is_debit=True).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
    
    def get_teacher_salaries(self, start_date=None, end_date=None):
        """Get teacher salaries allocated to this cost center based on course assignments"""
        from django.db.models import Sum
        total_salary = Decimal('0.00')
        
        # Get all courses assigned to this cost center
        courses = self.courses.filter(is_active=True)
        
        for course in courses:
            # Get teacher assignments for this course
            assignments = course.courseteacherassignment_set.filter(is_active=True)
            
            if start_date:
                assignments = assignments.filter(start_date__gte=start_date)
            if end_date:
                assignments = assignments.filter(start_date__lte=end_date)
            
            # Calculate total salary for each assignment
            for assignment in assignments:
                total_salary += assignment.calculate_total_salary()
        
        return total_salary
    
    def get_course_count(self):
        """Get number of courses associated with this cost center"""
        return self.courses.filter(is_active=True).count()
    
    def get_total_revenue(self, start_date=None, end_date=None):
        """Get total revenue for this cost center from course enrollments"""
        from django.db.models import Sum
        total_revenue = Decimal('0.00')
        
        # Get all courses assigned to this cost center
        courses = self.courses.filter(is_active=True)
        
        for course in courses:
            total_revenue += course.get_total_revenue(start_date, end_date)
        
        return total_revenue
    
    def get_other_expenses(self, start_date=None, end_date=None):
        """Get other expenses (non-salary) for this cost center"""
        total_expenses = self.get_total_expenses(start_date, end_date)
        teacher_salaries = self.get_teacher_salaries(start_date, end_date)
        return total_expenses - teacher_salaries
    
    def get_cash_inflow(self, start_date=None, end_date=None):
        """Get cash inflow for this cost center"""
        from django.db.models import Sum
        transactions = self.transaction_set.filter(
            account__code__in=['121', '1120'],  # Cash and Bank accounts
            is_debit=True  # Cash inflow is debit to cash accounts
        )
        
        if start_date:
            transactions = transactions.filter(journal_entry__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(journal_entry__date__lte=end_date)
        
        return transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    def get_cash_outflow(self, start_date=None, end_date=None):
        """Get cash outflow for this cost center"""
        from django.db.models import Sum
        transactions = self.transaction_set.filter(
            account__code__in=['121', '1120'],  # Cash and Bank accounts
            is_debit=False  # Cash outflow is credit to cash accounts
        )
        
        if start_date:
            transactions = transactions.filter(journal_entry__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(journal_entry__date__lte=end_date)
        
        return transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    def get_opening_balance(self, start_date=None):
        """Get opening balance for this cost center"""
        if not start_date:
            return Decimal('0.00')
        
        from django.db.models import Sum
        transactions = self.transaction_set.filter(
            journal_entry__date__lt=start_date
        )
        
        # Calculate net balance before start date
        debit_total = transactions.filter(is_debit=True).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        credit_total = transactions.filter(is_debit=False).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        
        return debit_total - credit_total
    
    def get_closing_balance(self, start_date=None, end_date=None):
        """Get closing balance for this cost center"""
        opening_balance = self.get_opening_balance(start_date)
        inflow = self.get_cash_inflow(start_date, end_date)
        outflow = self.get_cash_outflow(start_date, end_date)
        
        return opening_balance + inflow - outflow


class AccountingPeriod(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الفترة / Period Name')
    start_date = models.DateField(verbose_name='تاريخ البداية / Start Date')
    end_date = models.DateField(verbose_name='تاريخ النهاية / End Date')
    is_closed = models.BooleanField(default=False, verbose_name='مقفلة / Closed')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإقفال / Closed At')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_periods', verbose_name='أُقفل بواسطة / Closed By')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'الفترة المحاسبية / Accounting Period'
        verbose_name_plural = 'الفترات المحاسبية / Accounting Periods'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


class JournalEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ('MANUAL', 'يدوي / Manual'),
        ('enrollment', 'تسجيل / enrollment'),
        ('PAYMENT', 'دفع / Payment'),
        ('COMPLETION', 'إكمال / Completion'),
        ('EXPENSE', 'مصروف / Expense'),
        ('SALARY', 'راتب / Salary'),
        ('ADVANCE', 'سلفة / Advance'),
        ('ADJUSTMENT', 'تسوية / Adjustment'),
    ]

    reference = models.CharField(max_length=50, unique=True, verbose_name='المرجع / Reference')
    date = models.DateField(verbose_name='التاريخ / Date')
    description = models.TextField(verbose_name='الوصف / Description')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES, default='MANUAL', verbose_name='نوع القيد / Entry Type')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ الإجمالي / Total Amount')
    is_posted = models.BooleanField(default=False, verbose_name='مُرحل / Posted')
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الترحيل / Posted At')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_entries', verbose_name='مُرحل بواسطة / Posted By')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='أُنشئ بواسطة / Created By')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'قيد اليومية / Journal Entry'
        verbose_name_plural = 'قيود اليومية / Journal Entries'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.reference} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"JE-{NumberSequence.next_value('journal_entry'):06d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('accounts:journal_entry_detail', kwargs={'pk': self.pk})

    def get_total_debits(self):
        return self.transactions.filter(is_debit=True).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')

    def get_total_credits(self):
        return self.transactions.filter(is_debit=False).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def is_balanced(self):
        return abs(self.get_total_debits() - self.get_total_credits()) < Decimal('0.01')

    def post_entry(self, user):
        """Post the journal entry and update account balances"""
        if self.is_posted:
            raise ValueError("Entry is already posted")
        
        if not self.is_balanced:
            raise ValueError("Entry is not balanced")
        
        self.is_posted = True
        self.posted_at = timezone.now()
        self.posted_by = user
        self.save(update_fields=['is_posted', 'posted_at', 'posted_by'])
        
        # Update account balances
        for transaction in self.transactions.all():
            transaction.account.recalculate_tree_balances()

    def reverse_entry(self, user, description=None):
        """Create a reversing journal entry"""
        if not self.is_posted:
            raise ValueError("Cannot reverse unposted entry")
        
        reversing_entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=description or f"Reversal of {self.reference}",
            entry_type='ADJUSTMENT',
            total_amount=self.total_amount,
            created_by=user
        )
        
        # Create reversing transactions
        for transaction in self.transactions.all():
            Transaction.objects.create(
                journal_entry=reversing_entry,
                account=transaction.account,
                amount=transaction.amount,
                is_debit=not transaction.is_debit,  # Reverse the debit/credit
                description=f"Reversal: {transaction.description}",
                cost_center=transaction.cost_center
            )
        
        # Post the reversing entry
        reversing_entry.post_entry(user)
        return reversing_entry


class Transaction(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='transactions', verbose_name='قيد اليومية / Journal Entry')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions', verbose_name='الحساب / Account')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='المبلغ / Amount')
    is_debit = models.BooleanField(verbose_name='مدين / Debit')
    description = models.CharField(max_length=500, blank=True, verbose_name='الوصف / Description')
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='مركز التكلفة / Cost Center')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'المعاملة / Transaction'
        verbose_name_plural = 'المعاملات / Transactions'

    def __str__(self):
        return f"{self.account.code} - {self.amount} ({'Dr' if self.is_debit else 'Cr'})"

    @property
    def debit_amount(self):
        return self.amount if self.is_debit else Decimal('0.00')

    @property
    def credit_amount(self):
        return self.amount if not self.is_debit else Decimal('0.00')


class Course(models.Model):
    name = models.CharField(max_length=200, verbose_name='اسم الدورة / Course Name')
    name_ar = models.CharField(max_length=200, blank=True, verbose_name='الاسم بالعربية / Arabic Name')
    description = models.TextField(blank=True, verbose_name='الوصف / Description')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='السعر / Price')
    duration_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name='المدة بالساعات / Duration (Hours)')
    
    # Cost center relationship
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='courses', verbose_name='مركز التكلفة / Cost Center')
    
    # Teacher assignments
    assigned_teachers = models.ManyToManyField('employ.Teacher', through='CourseTeacherAssignment',
                                             related_name='assigned_courses', blank=True,
                                             verbose_name='المدرسون المعينون / Assigned Teachers')
    
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'الدورة / Course'
        verbose_name_plural = 'الدورات / Courses'
        ordering = ['name']

    def __str__(self):
        return self.name_ar if self.name_ar else self.name

    def get_absolute_url(self):
        return reverse('accounts:course_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create deferred revenue account for new courses
        if is_new:
            Account.get_or_create_course_deferred_account(self)
    
    def get_total_teacher_salaries(self, start_date=None, end_date=None):
        """Get total teacher salaries for this course"""
        from django.db.models import Sum
        assignments = self.courseteacherassignment_set.all()
        
        if start_date:
            assignments = assignments.filter(start_date__gte=start_date)
        if end_date:
            assignments = assignments.filter(start_date__lte=end_date)
        
        total_salary = Decimal('0.00')
        for assignment in assignments:
            total_salary += assignment.calculate_total_salary()
        
        return total_salary
    
    def get_enrollment_count(self, start_date=None, end_date=None):
        """Get number of enrollments for this course"""
        enrollments = self.enrollments.all()
        
        if start_date:
            enrollments = enrollments.filter(enrollment_date__gte=start_date)
        if end_date:
            enrollments = enrollments.filter(enrollment_date__lte=end_date)
        
        return enrollments.count()
    
    def get_total_revenue(self, start_date=None, end_date=None):
        """Get total revenue from this course"""
        from django.db.models import Sum
        enrollments = self.enrollments.all()
        
        if start_date:
            enrollments = enrollments.filter(enrollment_date__gte=start_date)
        if end_date:
            enrollments = enrollments.filter(enrollment_date__lte=end_date)
        
        return enrollments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')


class CourseTeacherAssignment(models.Model):
    """Model to track teacher assignments to courses with salary details"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='الدورة / Course')
    teacher = models.ForeignKey('employ.Teacher', on_delete=models.CASCADE, verbose_name='المدرس / Teacher')
    
    # Assignment details
    start_date = models.DateField(verbose_name='تاريخ البداية / Start Date')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاريخ النهاية / End Date')
    
    # Salary details for this course
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                    verbose_name='أجر الساعة / Hourly Rate')
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name='الراتب الشهري / Monthly Rate')
    total_hours = models.PositiveIntegerField(null=True, blank=True, 
                                            verbose_name='إجمالي الساعات / Total Hours')
    
    # Assignment status
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    notes = models.TextField(blank=True, verbose_name='ملاحظات / Notes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تعيين مدرس للدورة / Course Teacher Assignment'
        verbose_name_plural = 'تعيينات المدرسين للدورات / Course Teacher Assignments'
        unique_together = ('course', 'teacher', 'start_date')

    def __str__(self):
        return f"{self.teacher.full_name} - {self.course.name_ar or self.course.name}"

    def calculate_total_salary(self):
        """Calculate total salary for this assignment"""
        if self.hourly_rate and self.total_hours:
            return self.hourly_rate * self.total_hours
        elif self.monthly_rate:
            return self.monthly_rate
        return Decimal('0.00')

    def get_cost_center(self):
        """Get the cost center for this assignment"""
        return self.course.cost_center if self.course.cost_center else None


class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True, verbose_name='رقم الطالب / Student ID')
    name = models.CharField(max_length=200, verbose_name='الاسم / Name')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني / Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='الهاتف / Phone')
    address = models.TextField(blank=True, verbose_name='العنوان / Address')
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'الطالب / Student'
        verbose_name_plural = 'الطلاب / Students'
        ordering = ['name']

    def __str__(self):
        return f"{self.student_id} - {self.name}"

    @property
    def ar_account(self):
        """Get or create AR account for this student"""
        return Account.get_or_create_student_ar_account(self)


class Studentenrollment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'نقد / Cash'),
        ('BANK', 'بنك / Bank'),
        ('CARD', 'بطاقة / Card'),
        ('TRANSFER', 'تحويل / Transfer'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='enrollments', verbose_name='الطالب / Student')
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='enrollments', verbose_name='الدورة / Course')
    enrollment_date = models.DateField(verbose_name='تاريخ التسجيل / enrollment Date')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ الإجمالي / Total Amount')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم % / Discount Percent')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='قيمة الخصم / Discount Amount')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH', verbose_name='طريقة الدفع / Payment Method')
    notes = models.TextField(blank=True, verbose_name='ملاحظات / Notes')
    is_completed = models.BooleanField(default=False, verbose_name='مكتمل / Completed')
    completion_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الإكمال / Completion Date')
    
    # Journal entry references
    enrollment_journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments', verbose_name='قيد التسجيل / enrollment Entry')
    completion_journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='completions', verbose_name='قيد الإكمال / Completion Entry')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تسجيل الطالب / Student enrollment'
        verbose_name_plural = 'تسجيلات الطلاب / Student enrollments'
        ordering = ['-enrollment_date']
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.full_name} - {self.course.name}"

    @property
    def net_amount(self):
        """Calculate net amount after discounts"""
        after_percent = self.total_amount - (self.total_amount * self.discount_percent / Decimal('100'))
        return max(Decimal('0'), after_percent - self.discount_amount)

    @property
    def amount_paid(self):
        """Total amount paid for this enrollment"""
        return self.payments.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')

    @property
    def balance_due(self):
        """Remaining balance due"""
        return max(Decimal('0'), self.net_amount - self.amount_paid)

    def create_accrual_enrollment_entry(self, user):
        """Create enrollment accrual entry: DR Student AR, CR Deferred Revenue"""
        if self.enrollment_journal_entry:
            return self.enrollment_journal_entry
        
        net_amount = self.net_amount
        if net_amount <= 0:
            return None
        
        # Get accounts
        student_ar_account = self.student.ar_account
        course_deferred_account = Account.get_or_create_course_deferred_account(self.course)
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=self.enrollment_date,
            description=f"Student enrollment - {self.student.full_name} in {self.course.name}",
            entry_type='enrollment',
            total_amount=net_amount,
            created_by=user
        )
        
        # DR: Student AR
        Transaction.objects.create(
            journal_entry=entry,
            account=student_ar_account,
            amount=net_amount,
            is_debit=True,
            description=f"enrollment - {self.student.full_name}"
        )
        
        # CR: Deferred Revenue
        Transaction.objects.create(
            journal_entry=entry,
            account=course_deferred_account,
            amount=net_amount,
            is_debit=False,
            description=f"Deferred revenue - {self.course.name}"
        )
        
        # Post the entry
        entry.post_entry(user)
        
        # Link to enrollment
        self.enrollment_journal_entry = entry
        self.save(update_fields=['enrollment_journal_entry'])
        
        return entry


class StudentReceipt(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'نقد / Cash'),
        ('BANK', 'بنك / Bank'),
        ('CARD', 'بطاقة / Card'),
        ('TRANSFER', 'تحويل / Transfer'),
    ]

    receipt_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الإيصال / Receipt Number')
    date = models.DateField(verbose_name='التاريخ / Date')
    student_name = models.CharField(max_length=200, verbose_name='اسم الطالب / Student Name')
    course_name = models.CharField(max_length=200, blank=True, verbose_name='اسم الدورة / Course Name')
    
    # Foreign key relationships
    student_profile = models.ForeignKey('students.Student', on_delete=models.PROTECT, null=True, blank=True, related_name='receipts', verbose_name='ملف الطالب / Student Profile')
    student = models.ForeignKey(Student, on_delete=models.PROTECT, null=True, blank=True, related_name='receipts', verbose_name='الطالب / Student')
    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True, blank=True, related_name='receipts', verbose_name='الدورة / Course')
    enrollment = models.ForeignKey(Studentenrollment, on_delete=models.PROTECT, null=True, blank=True, related_name='payments', verbose_name='التسجيل / enrollment')
    
    # Financial fields
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='المبلغ / Amount')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ المدفوع / Paid Amount')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم % / Discount Percent')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='قيمة الخصم / Discount Amount')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH', verbose_name='طريقة الدفع / Payment Method')
    notes = models.TextField(blank=True, verbose_name='ملاحظات / Notes')
    is_printed = models.BooleanField(default=False, verbose_name='مطبوع / Printed')
    
    # Journal entry reference
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='receipts', verbose_name='قيد اليومية / Journal Entry')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='أُنشئ بواسطة / Created By')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'إيصال الطالب / Student Receipt'
        verbose_name_plural = 'إيصالات الطلاب / Student Receipts'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.receipt_number} - {self.student_name}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"SR-{NumberSequence.next_value('student_receipt'):06d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('accounts:student_receipt_detail', kwargs={'pk': self.pk})

    @property
    def net_amount(self):
        """Calculate net amount after discounts"""
        base_amount = self.amount or self.paid_amount or Decimal('0')
        after_percent = base_amount - (base_amount * self.discount_percent / Decimal('100'))
        return max(Decimal('0'), after_percent - self.discount_amount)

    def get_student_name(self):
        if self.student_profile:
            return self.student_profile.full_name
        return self.student_name

    def get_course_name(self):
        if self.course:
            return self.course.name
        return self.course_name

    def create_accrual_journal_entry(self, user):
        """Create journal entry for student payment: DR Cash, CR Student AR"""
        if self.journal_entry:
            return self.journal_entry
        
        paid_amount = self.paid_amount or Decimal('0')
        if paid_amount <= 0:
            return None
        
        # Get accounts
        cash_account, _ = Account.objects.get_or_create(
            code='121',
            defaults={
                'name': 'Cash',
                'name_ar': 'النقدية',
                'account_type': 'ASSET',
                'is_active': True,
            }
        )
        
        student_ar_account = None
        if self.student_profile:
            student_ar_account = self.student_profile.ar_account
        elif self.student:
            student_ar_account = self.student.ar_account
        
        if not student_ar_account:
            raise ValueError("No student AR account found")
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=self.date,
            description=f"Student payment - {self.get_student_name()} for {self.get_course_name()}",
            entry_type='PAYMENT',
            total_amount=paid_amount,
            created_by=user
        )
        
        # DR: Cash
        Transaction.objects.create(
            journal_entry=entry,
            account=cash_account,
            amount=paid_amount,
            is_debit=True,
            description=f"Cash received - {self.get_student_name()}"
        )
        
        # CR: Student AR
        Transaction.objects.create(
            journal_entry=entry,
            account=student_ar_account,
            amount=paid_amount,
            is_debit=False,
            description=f"Payment received - {self.get_course_name()}"
        )
        
        # Post the entry
        entry.post_entry(user)
        
        # Link to receipt
        self.journal_entry = entry
        self.save(update_fields=['journal_entry'])
        
        return entry


class ExpenseEntry(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'نقد / Cash'),
        ('BANK', 'بنك / Bank'),
        ('CARD', 'بطاقة / Card'),
        ('TRANSFER', 'تحويل / Transfer'),
    ]
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    reference = models.CharField(max_length=50, unique=True, verbose_name='المرجع / Reference')
    date = models.DateField(verbose_name='التاريخ / Date')
    description = models.CharField(max_length=500, verbose_name='الوصف / Description')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ / Amount')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH', verbose_name='طريقة الدفع / Payment Method')
    # receipt_number = models.CharField(max_length=100, blank=True, verbose_name='رقم الإيصال / Receipt Number')
    notes = models.TextField(blank=True, verbose_name='ملاحظات / Notes')
    
    # Foreign key relationships
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses', verbose_name='قيد اليومية / Journal Entry')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='أُنشئ بواسطة / Created By')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'قيد المصروف / Expense Entry'
        verbose_name_plural = 'قيود المصروفات / Expense Entries'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.reference} - {self.description}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"EX-{NumberSequence.next_value('expense'):06d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('accounts:expense_detail', kwargs={'pk': self.pk})

    def create_journal_entry(self, user):
        """Create journal entry for expense: DR Expense Account, CR Cash/Bank"""
        if self.journal_entry:
            return self.journal_entry
        
        # Get expense account from the selected account
        expense_account = self.account
        
        # Get payment account
        payment_account = self.get_payment_account()
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=self.date,
            description=f"Expense - {self.description}",
            entry_type='EXPENSE',
            total_amount=self.amount,
            created_by=user
        )
        
        # DR: Expense Account
        Transaction.objects.create(
            journal_entry=entry,
            account=expense_account,
            amount=self.amount,
            is_debit=True,
            description=self.description
        )
        
        # CR: Payment Account
        Transaction.objects.create(
            journal_entry=entry,
            account=payment_account,
            amount=self.amount,
            is_debit=False,
            description=f"Payment - {self.get_payment_method_display()}"
        )
        
        # Post the entry
        entry.post_entry(user)
        
        # Link to expense
        self.journal_entry = entry
        self.save(update_fields=['journal_entry'])
        
        return entry

    def get_payment_account(self):
        """Get payment account based on payment method"""
        account_mapping = {
            'CASH': ('121', 'Cash', 'النقدية'),
            'BANK': ('1120', 'Bank Account', 'حساب البنك'),
            'CARD': ('1120', 'Bank Account', 'حساب البنك'),
            'TRANSFER': ('1120', 'Bank Account', 'حساب البنك'),
        }
        
        code, name, name_ar = account_mapping.get(self.payment_method, account_mapping['CASH'])
        account, _ = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'name_ar': name_ar,
                'account_type': 'ASSET',
                'is_active': True,
            }
        )
        return account

    @property
    def category(self):
        """Get category from account code (503-599)"""
        if self.account and self.account.code:
            try:
                account_code = int(self.account.code)
                if 503 <= account_code <= 599:
                    return self.account.name
            except (ValueError, TypeError):
                pass
        return "Other"

    def get_category_display(self):
        """Display category name"""
        return self.category

class EmployeeAdvance(models.Model):
    employee = models.ForeignKey('employ.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='advances', verbose_name='الموظف / Employee')
    employee_name = models.CharField(max_length=200, verbose_name='اسم الموظف / Employee Name')
    date = models.DateField(verbose_name='التاريخ / Date')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ / Amount')
    purpose = models.CharField(max_length=500, verbose_name='الغرض / Purpose')
    repayment_date = models.DateField(null=True, blank=True, verbose_name='تاريخ السداد / Repayment Date')
    is_repaid = models.BooleanField(default=False, verbose_name='مسدد / Repaid')
    repaid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='المبلغ المسدد / Repaid Amount')
    reference = models.CharField(max_length=50, unique=True, verbose_name='المرجع / Reference')
    
    # Journal entry reference
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='advances', verbose_name='قيد اليومية / Journal Entry')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='أُنشئ بواسطة / Created By')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'سلفة الموظف / Employee Advance'
        verbose_name_plural = 'سلف الموظفين / Employee Advances'
        ordering = ['-date']

    def __str__(self):
        return f"{self.reference} - {self.employee_name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"ADV-{NumberSequence.next_value('advance'):06d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('accounts:advance_detail', kwargs={'pk': self.pk})

    @property
    def advance_number(self):
        return self.reference

    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        return max(Decimal('0'), self.amount - self.repaid_amount)

    def create_advance_entry(self, user):
        """Create advance journal entry: DR Employee Advance, CR Cash"""
        if self.journal_entry:
            return self.journal_entry
        
        # Get accounts
        advance_account = get_or_create_employee_advance_account(self.employee)
        cash_account, _ = Account.objects.get_or_create(
            code='121',
            defaults={
                'name': 'Cash',
                'name_ar': 'النقدية',
                'account_type': 'ASSET',
                'is_active': True,
            }
        )
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=self.date,
            description=f"Employee advance - {self.employee_name}",
            entry_type='ADVANCE',
            total_amount=self.amount,
            created_by=user
        )
        
        # DR: Employee Advance
        Transaction.objects.create(
            journal_entry=entry,
            account=advance_account,
            amount=self.amount,
            is_debit=True,
            description=f"Advance - {self.employee_name}"
        )
        
        # CR: Cash
        Transaction.objects.create(
            journal_entry=entry,
            account=cash_account,
            amount=self.amount,
            is_debit=False,
            description=f"Cash advance payment"
        )
        
        # Post the entry
        entry.post_entry(user)
        
        # Link to advance
        self.journal_entry = entry
        self.save(update_fields=['journal_entry'])
        
        return entry

    def create_advance_journal_entry(self, user):
        """Alias for create_advance_entry for compatibility"""
        return self.create_advance_entry(user)


class TeacherAdvance(models.Model):
    teacher = models.ForeignKey('employ.Teacher', on_delete=models.CASCADE, related_name='advances', verbose_name='المعلم / Teacher')
    date = models.DateField(verbose_name='التاريخ / Date')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ / Amount')
    purpose = models.CharField(max_length=500, verbose_name='الغرض / Purpose')
    is_repaid = models.BooleanField(default=False, verbose_name='مسدد / Repaid')
    repaid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='المبلغ المسدد / Repaid Amount')
    
    # Journal entry reference
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_advances', verbose_name='قيد اليومية / Journal Entry')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='أُنشئ بواسطة / Created By')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سلفة المعلم / Teacher Advance'
        verbose_name_plural = 'سلف المعلمين / Teacher Advances'
        ordering = ['-date']

    def __str__(self):
        return f"Advance - {self.teacher.full_name} - {self.amount}"

    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        return max(Decimal('0'), self.amount - self.repaid_amount)

    def create_advance_journal_entry(self, user):
        """Create advance journal entry: DR Teacher Advance, CR Cash"""
        if self.journal_entry:
            return self.journal_entry
        
        # Get accounts
        advance_account = get_or_create_teacher_advance_account(self.teacher)
        cash_account, _ = Account.objects.get_or_create(
            code='121',
            defaults={
                'name': 'Cash',
                'name_ar': 'النقدية',
                'account_type': 'ASSET',
                'is_active': True,
            }
        )
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=self.date,
            description=f"Teacher advance - {self.teacher.full_name}",
            entry_type='ADVANCE',
            total_amount=self.amount,
            created_by=user
        )
        
        # DR: Teacher Advance
        Transaction.objects.create(
            journal_entry=entry,
            account=advance_account,
            amount=self.amount,
            is_debit=True,
            description=f"Advance - {self.teacher.full_name}"
        )
        
        # CR: Cash
        Transaction.objects.create(
            journal_entry=entry,
            account=cash_account,
            amount=self.amount,
            is_debit=False,
            description=f"Cash advance payment"
        )
        
        # Post the entry
        entry.post_entry(user)
        
        # Link to advance
        self.journal_entry = entry
        self.save(update_fields=['journal_entry'])
        
        return entry


class Budget(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='الحساب / Account')
    period = models.ForeignKey(AccountingPeriod, on_delete=models.CASCADE, verbose_name='الفترة / Period')
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ المخطط / Budgeted Amount')
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='المبلغ الفعلي / Actual Amount')
    notes = models.TextField(blank=True, verbose_name='ملاحظات / Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'الميزانية / Budget'
        verbose_name_plural = 'الميزانيات / Budgets'
        unique_together = ('account', 'period')

    def __str__(self):
        return f"{self.account.code} - {self.period.name}"

    @property
    def variance(self):
        return self.actual_amount - self.budgeted_amount

    @property
    def variance_percentage(self):
        if self.budgeted_amount > 0:
            return (self.variance / self.budgeted_amount) * 100
        return Decimal('0')

    def calculate_variance(self):
        return self.variance


class DiscountRule(models.Model):
    reason = models.CharField(max_length=200, unique=True, verbose_name='سبب الخصم / Discount Reason')
    reason_ar = models.CharField(max_length=200, blank=True, verbose_name='السبب بالعربية / Reason in Arabic')
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name='نسبة الخصم % / Discount Percent'
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='قيمة الخصم الثابت / Fixed Discount Amount'
    )
    description = models.TextField(blank=True, verbose_name='الوصف / Description')
    is_active = models.BooleanField(default=True, verbose_name='نشط / Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'قاعدة الخصم / Discount Rule'
        verbose_name_plural = 'قواعد الخصم / Discount Rules'
        ordering = ['reason']

    def __str__(self):
        return self.reason


class StudentAccountLink(models.Model):
    student = models.OneToOneField('students.Student', on_delete=models.CASCADE, related_name='account_link', verbose_name='الطالب / Student')
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='student_link', verbose_name='الحساب / Account')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ربط حساب الطالب / Student Account Link'
        verbose_name_plural = 'روابط حسابات الطلاب / Student Account Links'

    def __str__(self):
        return f"{self.student.full_name} - {self.account.code}"


# Helper functions for account creation
def get_or_create_teacher_salary_account(teacher):
    """Get or create salary expense account for teacher"""
    # Ensure parent account exists
    parent_account, _ = Account.objects.get_or_create(
        code='501',
        defaults={
            'name': 'Teacher Salaries',
            'name_ar': 'رواتب المدرسين',
            'account_type': 'EXPENSE',
            'is_active': True,
        }
    )
    
    # Create teacher-specific salary account
    teacher_code = f"501-{teacher.id:03d}"
    account, created = Account.objects.get_or_create(
        code=teacher_code,
        defaults={
            'name': f"Salary Expense - {teacher.full_name}",
            'name_ar': f"راتب - {teacher.full_name}",
            'account_type': 'EXPENSE',
            'parent': parent_account,
            'is_active': True,
        }
    )
    return account


def get_or_create_teacher_dues_account(teacher):
    """Get or create teacher dues liability account"""
    # Ensure parent account exists
    parent_account, _ = Account.objects.get_or_create(
        code='22',
        defaults={
            'name': 'Teacher Dues',
            'name_ar': 'مستحقات المدرسين',
            'account_type': 'LIABILITY',
            'is_active': True,
        }
    )
    
    # Create teacher-specific dues account
    teacher_code = f"22-{teacher.id:03d}"
    account, created = Account.objects.get_or_create(
        code=teacher_code,
        defaults={
            'name': f"Teacher Dues - {teacher.full_name}",
            'name_ar': f"مستحقات - {teacher.full_name}",
            'account_type': 'LIABILITY',
            'parent': parent_account,
            'is_active': True,
        }
    )
    return account


def get_or_create_teacher_advance_account(teacher):
    """Get or create teacher advance asset account"""
    # Ensure parent account exists
    parent_account, _ = Account.objects.get_or_create(
        code='1242',
        defaults={
            'name': 'Teacher Advances',
            'name_ar': 'سلف المدرسين',
            'account_type': 'ASSET',
            'is_active': True,
        }
    )
    
    # Create teacher-specific advance account
    teacher_code = f"1242-{teacher.id:03d}"
    account, created = Account.objects.get_or_create(
        code=teacher_code,
        defaults={
            'name': f"Teacher Advance - {teacher.full_name}",
            'name_ar': f"سلفة - {teacher.full_name}",
            'account_type': 'ASSET',
            'parent': parent_account,
            'is_active': True,
        }
    )
    return account


def get_or_create_employee_salary_account(employee):
    """Get or create salary expense account for employee"""
    # Ensure parent account exists
    parent_account, _ = Account.objects.get_or_create(
        code='502',
        defaults={
            'name': 'Employee Salaries',
            'name_ar': 'رواتب الموظفين',
            'account_type': 'EXPENSE',
            'is_active': True,
        }
    )
    
    # Create employee-specific salary account
    employee_code = f"502-{employee.id:03d}"
    account, created = Account.objects.get_or_create(
        code=employee_code,
        defaults={
            'name': f"Salary Expense - {employee.full_name}",
            'name_ar': f"راتب - {employee.full_name}",
            'account_type': 'EXPENSE',
            'parent': parent_account,
            'is_active': True,
        }
    )
    return account


def get_or_create_employee_advance_account(employee):
    """Get or create employee advance asset account"""
    # Ensure parent account exists
    parent_account, _ = Account.objects.get_or_create(
        code='1241',
        defaults={
            'name': 'Employee Advances',
            'name_ar': 'سلف الموظفين',
            'account_type': 'ASSET',
            'is_active': True,
        }
    )
    
    # Create employee-specific advance account
    employee_code = f"1241-{employee.id:03d}"
    account, created = Account.objects.get_or_create(
        code=employee_code,
        defaults={
            'name': f"Employee Advance - {employee.full_name}",
            'name_ar': f"سلفة - {employee.full_name}",
            'account_type': 'ASSET',
            'parent': parent_account,
            'is_active': True,
        }
    )
    return account