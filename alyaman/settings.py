"""
Django settings for alyaman project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-change-me"

# DEBUG mode ON (خليه True للتطوير، وفي الإنتاج غيره False)
DEBUG = True

ALLOWED_HOSTS = []

# ==============================
# Applications
# ==============================
INSTALLED_APPS = [
    # Django defaults
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Project apps
    # "pages",
    'pages.apps.PagesConfig',
    "students",
    "employ",
    "attendance",
    "grade",
    "courses",
    "classroom",
    "registration",
    "accounts",
    "sslserver",
    # Third-party apps
    "mptt",
    "crispy_forms",
    "crispy_bootstrap4",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "alyaman.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # custom context processors
                'employ.context_processors.employee_permissions',

            ],
            # Make custom tags/filters globally available without {% load %}
            "builtins": [
                "django.contrib.humanize.templatetags.humanize",
                "accounts.templatetags.formatting",
                "accounts.templatetags.site_formatting",
                "accounts.templatetags.number_formatter_tags",
            ],
        },
    },
]

WSGI_APPLICATION = "alyaman.wsgi.application"
ASGI_APPLICATION = "alyaman.asgi.application"
# ==============================
MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'employ.middleware.EmployeePermissionsMiddleware',  # هنا

]

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'django.template.context_processors.request',
    'employ.context_processors.employee_permissions',   # هنا
]

# ==============================
# Database
# ==============================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ==============================
# Password validators
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ==============================
# Internationalization
# ==============================
LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
USE_TZ = True

# ==============================
# Static & Media
# ==============================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ==============================
# Crispy Forms
# ==============================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# ==============================
# Auth redirects
# ==============================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGOUT_URL = "/logout/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================
# Number formatting (thousand separators)
# ==============================
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ","
NUMBER_GROUPING = 3
