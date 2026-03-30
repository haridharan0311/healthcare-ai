from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        """Connect cache invalidation signals on new data."""
        from django.db.models.signals import post_save
        from django.core.cache import cache

        def invalidate_analytics_cache(sender, **kwargs):
            """
            New Feature 8: Cache invalidation on new appointment/prescription.
            Clears all analytics cache keys so APIs return fresh data.
            """
            cache.delete_many([
                'top_medicines_*',
                'district_restock_*',
            ])
            # Pattern-based clear for versioned keys
            cache.clear()

        try:
            from core.models import Appointment
            from inventory.models import Prescription
            post_save.connect(invalidate_analytics_cache, sender=Appointment)
            post_save.connect(invalidate_analytics_cache, sender=Prescription)
        except Exception:
            pass