from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg


class Filiere(models.Model):
    code = models.CharField(max_length=10, unique=True)
    nom = models.CharField(max_length=100)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filieres_dirigees'
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Filière'
        verbose_name_plural = 'Filières'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} -- {self.nom}'


class Etudiant(models.Model):
    ANNEES = [(i, f'Année {i}') for i in range(1, 6)]

    # Informations personnelles
    nom = models.CharField(max_length=100, verbose_name='Nom')
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    email = models.EmailField(unique=True, verbose_name='Email')
    matricule = models.CharField(max_length=20, unique=True)
    date_naissance = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)

    # Scolarité
    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.PROTECT,  # Interdit de supprimer une filière si des étudiants y sont rattachés
        related_name='etudiants'
    )
    annee = models.IntegerField(choices=ANNEES, default=1)
    actif = models.BooleanField(default=True)

    # Métadonnées automatiques
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Étudiant'
        verbose_name_plural = 'Étudiants'
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['nom', 'prenom']),
            models.Index(fields=['filiere', 'annee']),
        ]

    def __str__(self):
        return f'{self.prenom} {self.nom} ({self.matricule})'

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'

    @property
    def moyenne(self):
        result = self.notes.aggregate(moy=Avg('valeur'))
        return round(result['moy'] or 0.0, 2)

    @property
    def est_admis(self):
        return self.moyenne >= 10.0


class Note(models.Model):
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,  # Supprime les notes si l'étudiant est supprimé
        related_name='notes'
    )
    matiere = models.CharField(max_length=100)
    valeur = models.FloatField(
        validators=[
            MinValueValidator(0.0, 'Note minimale : 0'),
            MaxValueValidator(20.0, 'Note maximale : 20'),
        ]
    )
    semestre = models.CharField(max_length=10, default='S1')
    date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'matiere']
        unique_together = [['etudiant', 'matiere', 'semestre']]

    def __str__(self):
        return f'{self.etudiant.matricule} -- {self.matiere} : {self.valeur}/20'