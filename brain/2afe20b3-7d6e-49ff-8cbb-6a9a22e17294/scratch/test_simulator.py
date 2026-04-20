import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_ai.settings')
django.setup()

from analytics.utils.live_data_generator import _generator
from core.models import Clinic

print("Checking simulator status...")
print(_generator.get_status())

print("\nStarting simulator with interval 2s (Global)...")
_generator.start(interval=2)

print("Waiting 10 seconds for data generation batches...")
for i in range(5):
    time.sleep(2)
    print(f"Batch {i+1} status: {_generator.get_status()}")

print("\nStopping simulator...")
_generator.stop()

print("\nFinal Status:")
print(_generator.get_status())
