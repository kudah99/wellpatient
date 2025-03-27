import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'well_patient.settings')

app = Celery('well_patient')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Define periodic tasks
app.conf.beat_schedule = {
    'check-medication-resupply-daily': {
        'task': 'patients.tasks.check_medication_resupply',
        'schedule': crontab(hour=9, minute=0),  # Run at 9 AM every day
        'args': (),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
