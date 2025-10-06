from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import financial_reports_views
from . import site_export_views

app_name = 'accounts'

# API Router
router = DefaultRouter()
# router.register(r'courses', api_views.CourseViewSet, basename='course')
# router.register(r'receipts', api_views.StudentReceiptViewSet, basename='receipt')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Chart of Accounts
    path('chart/', views.ChartOfAccountsView.as_view(), name='chart_of_accounts'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('enrollments/<int:student_id>/withdraw/', views.enrollmentWithdrawView.as_view(), name='enrollment_withdraw'),
    # Journal Entries
    path('journal/', views.JournalEntryListView.as_view(), name='journal_entry_list'),
    path('journal/create/', views.JournalEntryCreateView.as_view(), name='journal_entry_create'),
    path('journal/<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_entry_detail'),
    path('journal/<int:pk>/update/', views.JournalEntryUpdateView.as_view(), name='journal_entry_update'),
    path('journal/<int:pk>/post/', views.PostJournalEntryView.as_view(), name='journal_entry_post'),
    path('journal/<int:pk>/reverse/', views.ReverseJournalEntryView.as_view(), name='journal_entry_reverse'),
    
    # Reports
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('reports/trial-balance/', views.TrialBalanceView.as_view(), name='trial_balance'),
    path('reports/income-statement/', views.IncomeStatementView.as_view(), name='income_statement'),
    path('reports/balance-sheet/', views.BalanceSheetView.as_view(), name='balance_sheet'),
    path('reports/ledger/<int:account_id>/', views.LedgerView.as_view(), name='ledger'),
    # Exports
    path('reports/trial-balance/export/xlsx/', views.TrialBalanceExportExcelView.as_view(), name='trial_balance_export'),
    path('reports/income-statement/export/xlsx/', views.IncomeStatementExportExcelView.as_view(), name='income_statement_export'),
    path('reports/balance-sheet/export/xlsx/', views.BalanceSheetExportExcelView.as_view(), name='balance_sheet_export'),
    path('reports/ledger/<int:account_id>/export/xlsx/', views.LedgerExportExcelView.as_view(), name='ledger_export'),
    
    # Student Receipts
    path('receipts/create/', views.StudentReceiptCreateView.as_view(), name='student_receipt_create'),
    path('receipts/<int:pk>/', views.StudentReceiptDetailView.as_view(), name='student_receipt_detail'),
    path('receipts/<int:pk>/print/', views.student_receipt_print, name='student_receipt_print'),
    
    # Expenses
    path('expenses/create/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    
    # Courses
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/update/', views.CourseUpdateView.as_view(), name='course_update'),
    
    # Employee Advances
    path('advances/', views.EmployeeAdvanceListView.as_view(), name='advance_list'),
    path('advances/create/', views.EmployeeAdvanceCreateView.as_view(), name='advance_create'),
    path('advances/<int:pk>/', views.EmployeeAdvanceDetailView.as_view(), name='advance_detail'),
    # enrollment withdraw action
    path('enrollments/<int:pk>/withdraw/', views.enrollmentWithdrawView.as_view(), name='enrollment_withdraw'),
    
    # Employee Financial Profiles
    path('employees/financial/', views.EmployeeFinancialOverviewView.as_view(), name='employee_financial_overview'),
    path('employees/financial/<str:entity_type>/<int:pk>/', views.EmployeeFinancialProfileView.as_view(), name='employee_financial_profile'),

    # Outstanding Reports
    path('reports/outstanding-courses/', views.OutstandingCoursesView.as_view(), name='outstanding_courses'),
    path('reports/outstanding-courses/<int:course_id>/students/', views.OutstandingCourseStudentsView.as_view(), name='outstanding_course_students'),
    
    # Budget Management
    path('budgets/', views.BudgetListView.as_view(), name='budget_list'),
    path('budgets/create/', views.BudgetCreateView.as_view(), name='budget_create'),
    path('budgets/<int:pk>/', views.BudgetDetailView.as_view(), name='budget_detail'),
    path('budgets/<int:pk>/update/', views.BudgetUpdateView.as_view(), name='budget_update'),
    
    # Accounting Periods
    path('periods/', views.AccountingPeriodListView.as_view(), name='period_list'),
    path('periods/create/', views.AccountingPeriodCreateView.as_view(), name='period_create'),
    path('periods/<int:pk>/', views.AccountingPeriodDetailView.as_view(), name='period_detail'),
    path('periods/<int:pk>/update/', views.AccountingPeriodUpdateView.as_view(), name='period_update'),
    path('periods/<int:pk>/close/', views.ClosePeriodView.as_view(), name='period_close'),
    
    # Receipts and Expenses
    path('receipts-expenses/', views.ReceiptsExpensesView.as_view(), name='receipts_expenses'),
    
    # Cost Centers
    path('cost-centers/', views.CostCenterListView.as_view(), name='cost_center_list'),
    path('cost-centers/create/', views.CostCenterCreateView.as_view(), name='cost_center_create'),
    path('cost-centers/<int:pk>/update/', views.CostCenterUpdateView.as_view(), name='cost_center_update'),
    
    # AJAX endpoints
    path('ajax/course/<int:pk>/price/', views.ajax_course_price, name='ajax_course_price'),
    
    # Discount Rules
    path('discount-rules/', views.DiscountRuleListView.as_view(), name='discount_rule_list'),
    path('discount-rules/create/', views.DiscountRuleCreateView.as_view(), name='discount_rule_create'),
    path('discount-rules/<int:pk>/', views.DiscountRuleDetailView.as_view(), name='discount_rule_detail'),
    path('discount-rules/<int:pk>/update/', views.DiscountRuleUpdateView.as_view(), name='discount_rule_update'),
    path('discount-rules/<int:pk>/delete/', views.DiscountRuleDeleteView.as_view(), name='discount_rule_delete'),
    
    # AJAX endpoints for discounts
    path('ajax/discount-rule/<str:reason>/', views.ajax_discount_rule, name='ajax_discount_rule'),
    
    # Financial Reports URLs
    path('reports/financial/', financial_reports_views.financial_reports_dashboard, name='financial_reports_dashboard'),
    path('reports/cost-center-analysis/', financial_reports_views.CostCenterAnalysisReportView.as_view(), name='cost_center_analysis'),
    path('reports/cost-center-cash-flow/', financial_reports_views.CostCenterCashFlowReportView.as_view(), name='cost_center_cash_flow'),
    path('reports/comprehensive/', financial_reports_views.ComprehensiveFinancialReportView.as_view(), name='comprehensive_financial'),
    path('reports/cost-center/<int:cost_center_id>/', financial_reports_views.cost_center_detail_report, name='cost_center_detail'),
    
    # AJAX endpoints for financial reports
    path('ajax/cost-center-data/', financial_reports_views.get_cost_center_data, name='ajax_cost_center_data'),
    
    # Site-wide Export URLs
    path('reports/site-export/', site_export_views.site_export_dashboard, name='site_export_dashboard'),
    path('reports/site-export/comprehensive/', site_export_views.comprehensive_site_export, name='comprehensive_site_export'),
    
    # Number Formatter Demo
    path('reports/number-formatter-demo/', views.number_formatter_demo, name='number_formatter_demo'),
]

