"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

# Import dj-database-url at the beginning of the file.
import dj_database_url
from pathlib import Path
import os
import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read the environment variable file
environ.Env.read_env(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = [
    "*"
]  # change this to the DNS of the server where the backend is hosted

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "https://agri-connect-five.vercel.app"]
# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "drf_yasg",
    "rest_framework",
    "knox",
    "dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "dashboard.middleware.TrafficMiddleware",
    "dashboard.middleware.SiteVisitMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
DATABASE_URL = env('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.config(
        # Replace this value with your local database's connection string.
        default=os.getenv(DATABASE_URL),
        conn_max_age=600
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "staticfiles/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Uploads
MEDIA_URL = "uploads/"
MEDIA_ROOT = os.path.join(BASE_DIR, "staticfiles/uploads")

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
    
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'knox.auth.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

AUTH_USER_MODEL = "dashboard.CustomUser"
PASSWORD_RESET_TIMEOUT = 1800
FRONTEND_URL = 'http://127.0.0.1:8000'

# Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = ''
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = ''
ADMINS = []
SERVER_EMAIL = ""

# Mpesa settings
MPESA_CONSUMER_KEY = '8mJj8JJCU5XewrVBCQgF3NXEPmnV2lyYButF7PqPhGXMOP9u'
MPESA_CONSUMER_SECRET = 'LtlKCLYANCRJH8jpW3UID6O0anRzFS9XqfcT2HG3oGehx941c6JE0ixvJgraA8T2'
MPESA_API_URL = 'https://sandbox.safaricom.co.ke/'
MPESA_SHORTCODE = '174379'
MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
MPESA_CALLBACK_URL = 'http://127.0.0.1:8000/api/mpesa/callback/'