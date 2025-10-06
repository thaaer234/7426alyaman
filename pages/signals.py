from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.exceptions import ObjectDoesNotExist
from .models import ActivityLog
import inspect
from django.db import connection

def table_exists(table_name):
    """يتأكد إذا الجدول موجود فعلاً بالـ DB"""
    return table_name in connection.introspection.table_names()

def get_current_user():
    """الحصول على المستخدم الحالي"""
    try:
        for frame_record in inspect.stack():
            frame = frame_record[0]
            request = frame.f_locals.get('request')
            if request and hasattr(request, 'user'):
                return request.user
    except:
        pass
    return None

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    excluded_models = ['ActivityLog', 'LogEntry', 'Session', 'ContentType']
    if sender.__name__ in excluded_models:
        return
    
    # 🛑 وقف التنفيذ إذا جدول ActivityLog لسا ما انبنى
    if not table_exists('pages_activitylog'):
        return

    try:
        user = get_current_user()
        if user and user.is_superuser:
            return

        action = 'create' if created else 'update'
        ActivityLog.objects.create(
            user=user,
            action=action,
            content_type=sender.__name__,
            object_id=instance.id,
            object_repr=str(instance)[:200],
            details=f"تم {action} {sender.__name__}: {instance}"
        )
    except Exception as e:
        print(f"Error logging activity: {e}")

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    excluded_models = ['ActivityLog', 'LogEntry', 'Session', 'ContentType']
    if sender.__name__ in excluded_models:
        return

    if not table_exists('pages_activitylog'):
        return
    
    try:
        user = get_current_user()
        if user and user.is_superuser:
            return

        ActivityLog.objects.create(
            user=user,
            action='delete',
            content_type=sender.__name__,
            object_id=instance.id,
            object_repr=str(instance)[:200],
            details=f"تم حذف {sender.__name__}: {instance}"
        )
    except Exception as e:
        print(f"Error logging delete activity: {e}")

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    if not table_exists('pages_activitylog'):
        return

    if user.is_superuser:
        return

    ActivityLog.objects.create(
        user=user,
        action='login',
        content_type='User',
        object_id=user.id,
        object_repr=user.username,
        details="تم تسجيل الدخول إلى النظام"
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if not table_exists('pages_activitylog'):
        return

    if user.is_superuser:
        return

    ActivityLog.objects.create(
        user=user,
        action='logout',
        content_type='User',
        object_id=user.id,
        object_repr=user.username,
        details="تم تسجيل الخروج من النظام"
    )
