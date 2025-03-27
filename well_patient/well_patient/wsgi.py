"""
WSGI config for well_patient project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'well_patient.settings')

application = get_wsgi_application()
