# views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from students.models import Student
from employ.models import Employee, Teacher
from accounts.models import Transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum ,Q
from .models import ActivityLog  # استيراد النموذج الجديد
from datetime import timedelta, datetime
from django.contrib.auth.models import User

class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'pages/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات الطلاب والمدرسين
        context['students_count'] = Student.objects.count()
        context['teachers_count'] = Teacher.objects.count()
        
        # حساب الدخل والمصروفات الشهرية
        start_date = timezone.now().replace(day=1)
        end_date = start_date + timedelta(days=31)
        
        # context['monthly_income'] = Transaction.objects.filter(
        #     type='income',
        #     date__gte=start_date,
        #     date__lte=end_date
        # ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # context['monthly_expenses'] = Transaction.objects.filter(
        #     type='expense',
        #     date__gte=start_date,
        #     date__lte=end_date
        # ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # جلب جميع المستخدمين للفلترة باستثناء admin
        context['users'] = User.objects.exclude(username='admin')
        
        # جلب معاملات الفلترة من الطلب
        user_filter = self.request.GET.get('user', '')
        start_date_filter = self.request.GET.get('start_date', '')
        end_date_filter = self.request.GET.get('end_date', '')
        
        # حفظ قيم الفلترة للعرض في القوائم
        context['selected_user'] = user_filter
        context['start_date'] = start_date_filter
        context['end_date'] = end_date_filter
        
        # بناء الاستعلام مع الفلترة - استبعاد نشاطات admin
        activity_query = ActivityLog.objects.filter(
            Q(user__is_superuser=False) | Q(user__isnull=True)
        ).exclude(content_type='LogEntry')
        
        # استبعاد نشاطات المستخدم admin إذا كان اسم المستخدم admin
        activity_query = activity_query.exclude(user__username='admin')
        
        # تطبيق فلترة المستخدم
        if user_filter:
            activity_query = activity_query.filter(user_id=user_filter)
        
        # تطبيق فلترة التاريخ
        if start_date_filter:
            try:
                start_date = datetime.strptime(start_date_filter, '%Y-%m-%d')
                activity_query = activity_query.filter(timestamp__gte=start_date)
            except ValueError:
                pass  # تجاهل في حالة تاريخ غير صحيح
        
        if end_date_filter:
            try:
                end_date = datetime.strptime(end_date_filter, '%Y-%m-%d')
                # إضافة يوم كامل للتأكد من تضمين اليوم المحدد
                end_date = end_date + timedelta(days=1)
                activity_query = activity_query.filter(timestamp__lt=end_date)
            except ValueError:
                pass  # تجاهل في حالة تاريخ غير صحيح
        
        # ترتيب النتائج وتحديد العدد
        context['recent_activities'] = activity_query.order_by('-timestamp')[:50]  # تحديد 50 نشاط فقط
        
        return context
    
    
class welcome(TemplateView):
    template_name =   'pages/welcome.html'      