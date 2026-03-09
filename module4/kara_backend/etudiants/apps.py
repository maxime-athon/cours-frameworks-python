from django.apps import AppConfig

class EtudiantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'etudiants'

    def ready(self):
        # Importer les signals au démarrage de l'application
        import etudiants.signals