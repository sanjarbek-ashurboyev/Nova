import os
from os.path import join
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_flag(name, default):
    return os.environ.get(name, default).strip().lower() in {'1', 'true', 'yes', 'on'}


def _dev_secret_key():
    path = BASE_DIR / '.secret_key'
    if not path.exists():
        path.write_text(get_random_secret_key())
        path.chmod(0o600)
    return path.read_text().strip()


DEBUG = _env_flag('DJANGO_DEBUG', '1')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or ''
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY muhit o'zgaruvchisi DEBUG=False bo'lganda majburiy."
        )
    SECRET_KEY = _dev_secret_key()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.humanize",
    'accounts',
    'orders',
    'catalog',
    'operator_app',
    'driver_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'root.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DJANGO_DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('DJANGO_DB_USER', ''),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', ''),
        'HOST': os.environ.get('DJANGO_DB_HOST', ''),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'accounts.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('phone', 'first_name', 'last_name', 'email'),
        },
    },
    {
        'NAME': 'accounts.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'accounts.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'accounts.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True



STATIC_URL = 'static/'
STATIC_ROOT = join(BASE_DIR, 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'

STATICFILES_DIRS = [BASE_DIR / 'static']

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
        if origin.strip()
    ]
