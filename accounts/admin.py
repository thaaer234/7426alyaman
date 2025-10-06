from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.html import format_html
from .models import (
    Account, JournalEntry, Transaction, StudentReceipt, ExpenseEntry,
    Course, Student, Studentenrollment, EmployeeAdvance, CostCenter,
    AccountingPeriod, Budget, StudentAccountLink,
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_ar', 'account_type', 'balance', 'is_active']
    list_filter = ['account_type', 'is_active']
    search_fields = ['code', 'name', 'name_ar']
    ordering = ['code']
    readonly_fields = ['balance', 'created_at', 'updated_at']


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ['debit_amount', 'credit_amount']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['reference', 'date', 'description', 'total_amount', 'is_posted', 'created_by']
    list_filter = ['is_posted', 'entry_type', 'date']
    search_fields = ['reference', 'description']
    readonly_fields = ['created_at', 'updated_at', 'posted_at', 'posted_by']
    inlines = [TransactionInline]
    # Force a safe default ordering on valid fields only
    ordering = ('-date', '-created_at', 'reference', 'id')

    def get_ordering(self, request):
        # Ignore any invalid external ordering parameters
        return ('-date', '-created_at', 'reference', 'id')

    def get_changelist(self, request, **kwargs):
        # Use a ChangeList that doesn't attempt to order by invalid field names
        class SafeChangeList(ChangeList):
            def get_ordering(self, request, qs):
                # Always use the ModelAdmin's validated ordering
                return list(self.model_admin.get_ordering(request))

        return SafeChangeList


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'amount', 'is_debit', 'description']
    list_filter = ['is_debit', 'journal_entry__date']
    search_fields = ['account__name', 'description']


@admin.register(StudentReceipt)
class StudentReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'date', 'student_name', 'course_name', 'paid_amount', 'created_by']
    list_filter = ['date', 'payment_method']
    search_fields = ['receipt_number', 'student_name', 'course_name']
    readonly_fields = ['receipt_number', 'net_amount', 'created_at']


@admin.register(ExpenseEntry)
class ExpenseEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'description', 'amount', 'created_by']
    list_filter = ['date', 'payment_method']  # تم إزالة 'category' من list_filter
    search_fields = ['description', 'vendor']

    def get_list_filter(self, request):
        """
        ديناميكيًا نتحقق من وجود حقل 'category' قبل إضافته إلى list_filter
        """
        list_filter = ['date', 'payment_method']
        
        # تحقق مما إذا كان حقل 'category' موجودًا في الموديل
        # try:
            # from .models import ExpenseEntry
        #     if hasattr(ExpenseEntry, 'category'):
        #         # list_filter.append('category')
        # except:
        #     pass
            
        return list_filter


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_ar', 'price', 'duration_hours', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'name', 'email', 'phone', 'is_active']
    list_filter = ['is_active']
    search_fields = ['student_id', 'name', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Studentenrollment)
class StudentenrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrollment_date', 'total_amount', 'net_amount', 'amount_paid', 'balance_due', 'is_completed']
    list_filter = ['enrollment_date', 'is_completed', 'payment_method']
    search_fields = ['student__name', 'course__name']
    readonly_fields = ['created_at', 'net_amount', 'amount_paid', 'balance_due']
    
    def net_amount(self, obj):
        return obj.net_amount
    net_amount.short_description = 'Net Amount'
    
    def amount_paid(self, obj):
        return obj.amount_paid
    amount_paid.short_description = 'Amount Paid'
    
    def balance_due(self, obj):
        return obj.balance_due
    balance_due.short_description = 'Balance Due'


@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'date', 'amount', 'purpose', 'is_repaid', 'created_by']
    list_filter = ['date', 'is_repaid']
    search_fields = ['employee_name', 'purpose']
    readonly_fields = ['outstanding_amount', 'created_at']
    
    def outstanding_amount(self, obj):
        return obj.outstanding_amount
    outstanding_amount.short_description = 'Outstanding Amount'


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_ar', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'name_ar']


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_closed', 'is_current']
    list_filter = ['is_closed']
    search_fields = ['name']
    readonly_fields = ['closed_at', 'closed_by']
    
    def is_current(self, obj):
        return obj.is_current
    is_current.boolean = True
    is_current.short_description = 'Current Period'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['account', 'period', 'budgeted_amount', 'actual_amount', 'variance']
    list_filter = ['period']
    search_fields = ['account__name', 'period__name']
    readonly_fields = ['variance']


@admin.register(StudentAccountLink)
class StudentAccountLinkAdmin(admin.ModelAdmin):
    list_display = ['student', 'account', 'created_at']
    search_fields = ['student__full_name', 'account__name']
    readonly_fields = ['created_at']