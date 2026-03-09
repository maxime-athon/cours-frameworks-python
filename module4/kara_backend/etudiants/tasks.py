# Simulation de tâches asynchrones (ex: Celery)

class MockTask:
    def delay(self, *args, **kwargs):
        # Ici, on simulerait l'envoi d'un email
        print(f"[TASK] Envoi d'email simulé à {args}")

envoyer_email_bienvenue = MockTask()