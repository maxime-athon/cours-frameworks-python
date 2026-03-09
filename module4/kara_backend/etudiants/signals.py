from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Etudiant
from .tasks import envoyer_email_bienvenue

@receiver(post_save, sender=Etudiant)
def etudiant_cree(sender, instance, created, **kwargs):
    if created:
        # Déclencher une tâche asynchrone (Celery)
        envoyer_email_bienvenue.delay(instance.email, instance.nom_complet)