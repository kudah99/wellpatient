"""
Django settings for well_patient project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-9dm=0pgo6y1f&^kkw66xn(e_4j#1yj1&uz4*^7g)#pqbr5k+m3')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    'unfold',  # django-unfold for admin UI
    'unfold.contrib.filters',  # Optional for better filter UI
    'unfold.contrib.forms',  # Optional for better form UI
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'widget_tweaks',
    'django_celery_beat',
    'django_celery_results',
    'import_export',
    'patients',
    'account',
    'message_logs'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'well_patient.urls'

AUTH_USER_MODEL = 'account.CustomUser'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'well_patient.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'well_patient',
        'USER': 'chris',
        'PASSWORD': 'vd7uHW1M',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Harare'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STORAGES = {
    # ...
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

WHITENOISE_MANIFEST_STRICT = False
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join("static")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = (
    ("css", BASE_DIR / "assets/css"),
    ("js", BASE_DIR / "assets/js"),
    ("images", BASE_DIR / "assets/images")
)


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Twilio settings
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# WhatsApp Business API settings
WHATSAPP_API_KEY = os.getenv('WHATSAPP_API_KEY', '')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')

# Unfold admin settings
UNFOLD = {
    "SITE_TITLE": "WELL PATIENT",
    "SITE_HEADER": "WELL PATIENT",
    "SITE_SYMBOL": "local_pharmacy",
    "SHOW_HISTORY": False,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "patients.views.dashboard_callback",
    "THEME": "light",
    "SITE_ICON": {
        "light": lambda request: static("images/favicon.ico"),
        "dark": lambda request: static("images/favicon.ico"),
    },
    "SITE_LOGO": {
        "light": lambda request: static("images/favicon-96x96.png"),
        "dark": lambda request: static("images/favicon-96x96.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "type": "image/x-icon",
            "href": lambda request: static("images/favicon.ico"),
        },
    ],
    "STYLES": [
        lambda request: static("css/custom.css"),
    ],
    "SCRIPTS": [
        lambda request: static("js/custom.js"),
    ],
    "COLORS": {
"base": {
            "50": "249 250 251",
            "100": "243 244 246",
            "200": "229 231 235",
            "300": "209 213 219",
            "400": "156 163 175",
            "500": "107 114 128",
            "600": "75 85 99",
            "700": "55 65 81",
            "800": "31 41 55",
            "900": "17 24 39",
            "950": "3 7 18",
        },
    "primary": {
        "50": "240 253 244",
        "100": "220 252 231",
        "200": "187 247 208",
        "300": "134 239 172",
        "400": "74 222 128",
        "500": "34 197 94",
        "600": "22 163 74",
        "700": "21 128 61",
        "800": "22 101 52",
        "900": "20 83 45",
        "950": "5 46 22"
    },
    "font": {
        "subtle-light": "var(--color-base-500)",
        "subtle-dark": "var(--color-base-400)",
        "default-light": "var(--color-base-600)",
        "default-dark": "var(--color-base-300)",
        "important-light": "var(--color-base-900)",
        "important-dark": "var(--color-base-100)"
    }
},
        "SIDEBAR": {
        "show_search": False,  # Search in applications and models names
        "show_all_applications": False,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _(""),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "Dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    
                ],
            },
            {
                "title": _("Manage Admin Accounts"),
                "separator": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "Person",
                        "link": reverse_lazy("admin:accounts_customuser_changelist"),
                    },
                    
                ],
            },
             {
                "title": _("General"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Locations Management"),
                        "icon": "person_pin_circle",
                        "link": reverse_lazy("admin:patients_location_changelist"),
                    },
                     {
                        "title": _("BroadCast Messages Management"),
                        "icon": "cell_tower ",
                        "link": reverse_lazy("admin:broadcast_messages")
                    },
                ]
                        },
                       {
    "title": _("Client Management"),
    "separator": True,
    "collapsible": False,
    "items": [
        {
            "title": _("Patients"),
            "icon": "people",
            "link": reverse_lazy("admin:patients_patient_changelist"),
        },
        {
            "title": _("Patient Medication"),
            "icon": "medical_information",
            "link": reverse_lazy("admin:patients_patientmedication_changelist"),
        },
       {
            "title": _("Corporate Clients"),
            "icon": "business",  # You can replace with any icon name used by your UI
            "link": reverse_lazy("admin:patients_corporateclient_changelist"),
        },
    ]
},

                        {
                "title": _("Notifications Management"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Notifications Logs"),
                        "icon": "list",
                        "link": reverse_lazy("admin:patients_notificationlog_changelist"),
                    },
                     {
                        "title": _("Notifications Templates"),
                        "icon": "Notifications",
                        "link": reverse_lazy("admin:patients_notificationtype_changelist"),
                    },
                ]
                        },
                        {
                "title": _("Advanced Settings"),
                "collapsible": False,
                "items": [
                    {
                        "title": _("Periodic tasks"),
                        "icon": "task",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_periodictask_changelist"
                        ),
                    },
                ],
            },]       
        }

}
