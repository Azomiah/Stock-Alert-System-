from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Only start the updater in the main process
        import os
        if os.environ.get('RUN_MAIN', None) != 'true':
            from .tasks import price_updater
            price_updater.start()