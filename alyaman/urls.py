# alyaman/urls.py
from django.contrib import admin
from django.urls import path, include, reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

def root(request):
    if not request.user.is_authenticated:
        return redirect('login')
    for name in ('pages:welcome', 'students:student', 'accounts:dashboard'):
        try:
            reverse(name)
            return redirect(name)
        except Exception:
            continue
    return redirect('/admin/')

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('admin/', admin.site.urls),
    path('', root, name='root'),   # جذر آمن

    # نقلنا pages تحت /pages/ لتجنب تضارب الجذر
    path('pages/', include('pages.urls')),
    path('students/', include('students.urls')),
    path('employ/', include('employ.urls')),
    path('attendance/', include('attendance.urls')),
    path('grade/', include('grade.urls')),
    path('courses/', include('courses.urls')),
    path('classroom/', include('classroom.urls')),
    path('registration/', include('registration.urls')),
    path('accounts/', include('accounts.urls')),
]
