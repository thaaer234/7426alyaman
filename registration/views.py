from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.contrib.auth.models import User
# Create your views here.
class registerview(CreateView):
    template_name = 'registration/signup.html'
    model = User
    form_class = UserCreationForm
    success_url = 'registration/login/'