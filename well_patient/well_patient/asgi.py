"""
ASGI config for well_patient project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'well_patient.settings')

application = get_asgi_application()
