# config/config/settings/dev.py
from .base import *
from dotenv import load_dotenv
load_dotenv()


SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = True
ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
