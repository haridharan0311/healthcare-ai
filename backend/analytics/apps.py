from django.apps import AppConfig
import sys


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        """Connect cache invalidation signals on new data."""
        from django.db.models.signals import post_save
        from django.core.cache import cache

        def invalidate_analytics_cache(sender, **kwargs):
            """
            Granular cache invalidation instead of cache.clear().
            Prevents the 'Death Loop' where background generation wipes performance.
            """
            # cache.clear()  <-- REMOVED: Too aggressive, kills dashboard performance
            cache.delete('platform_dashboard_data') # Targeted invalidation only
            pass

        try:
            from core.models import Appointment
            from inventory.models import Prescription
            post_save.connect(invalidate_analytics_cache, sender=Appointment)
            post_save.connect(invalidate_analytics_cache, sender=Prescription)
        except Exception:
            pass
        
        # FIXED: Removed auto-starting generator from here. 
        # Starting background threads in ready() causes deadlocks with Django's reloader.
        # Use 'python manage.py generate_live_data' instead.
        """
        if 'test' not in sys.argv:
            try:
                from .utils.live_data_generator import start_live_data_generator
                start_live_data_generator()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f'Failed to start live data generator: {e}')
        """