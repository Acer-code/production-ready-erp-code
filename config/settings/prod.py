# config/config/settings/prod.py
from .base import *
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = False

ALLOWED_HOSTS = ['*']

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ['DB_NAME'],
#         'USER': os.environ['DB_USER'],
#         'PASSWORD': os.environ['DB_PASSWORD'],
#         'HOST': 'AccureMedicalPvtLtd-4883.postgres.pythonanywhere-services.com',
#         'PORT': '14883',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ['EMAIL_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_PASS']

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },

    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/django.log",
            "maxBytes": 1024 * 1024 * 5,  # 5MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["file"],
        "level": "WARNING",
    },
}
