import os
import sys
import time
import cProfile
import pstats
import io
from datetime import date, timedelta

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from analytics.services.dashboard_service import DashboardService

def profile_payload(days, forecast_days):
    print(f"\n{'='*60}")
    print(f"PROFILING PAYLOAD: days={days}, forecast_days={forecast_days}")
    print(f"{'='*60}")
    
    pr = cProfile.Profile()
    pr.enable()
    
    start_time = time.time()
    result = DashboardService.get_unified_dashboard(days=days, forecast_days=forecast_days)
    end_time = time.time()
    
    pr.disable()
    
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(15) # Show top 15 heavy hitters
    
    print(f"\nTotal Execution Time: {end_time - start_time:.4f} seconds")
    print("\nTop Performance Bottlenecks:")
    print(s.getvalue())
    
    return end_time - start_time

if __name__ == "__main__":
    payloads = [
        (30, 8),
        (60, 14),
        (7, 3)
    ]
    
    results = {}
    for days, f_days in payloads:
        duration = profile_payload(days, f_days)
        results[f"days_{days}"] = duration
    
    print("\nSummary of Results:")
    for key, duration in results.items():
        print(f"  - {key}: {duration:.4f}s")
