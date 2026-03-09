from django.contrib import admin
from django.utils.html import format_html
from .models import Etudiant, Filiere, Note


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'nb_etudiants', 'actif']
    list_filter = ['actif']
    search_fields = ['code', 'nom']

    def nb_etudiants(self, obj):
        return obj.etudiants.filter(actif=True).count()
    nb_etudiants.short_description = 'Étudiants actifs'


class NoteInline(admin.TabularInline):
    """Affichage des notes directement dans l’admin Étudiant"""
    model = Note
    extra = 1
    fields = ['matiere', 'valeur', 'semestre']


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = [
        'matricule', 'prenom', 'nom', 'filiere',
        'annee', 'moyenne_affichee', 'badge_statut'
    ]
    list_filter = ['actif', 'filiere', 'annee']
    search_fields = ['nom', 'prenom', 'email', 'matricule']
    ordering = ['nom', 'prenom']
    list_per_page = 25
    inlines = [NoteInline]

    fieldsets = [
        ('Informations personnelles', {
            'fields': ['nom', 'prenom', 'email', 'date_naissance', 'photo'],
        }),
        ('Scolarité', {
            'fields': ['matricule', 'filiere', 'annee', 'actif'],
        }),
    ]

    actions = ['desactiver_etudiants']

    def moyenne_affichee(self, obj):
        moy = obj.moyenne
        couleur = 'green' if moy >= 10 else 'red'
        return format_html(
            '<span style="color:{};font-weight:bold;">{:.2f}/20</span>',
            couleur, moy
        )
    moyenne_affichee.short_description = 'Moyenne'

    def badge_statut(self, obj):
        if obj.est_admis:
            return format_html(
                '<span style="background:green;color:white;padding:2px 8px;'
                'border-radius:4px;">Admis</span>'
            )
        return format_html(
            '<span style="background:red;color:white;padding:2px 8px;'
            'border-radius:4px;">Échec</span>'
        )
    badge_statut.short_description = 'Statut'

    def desactiver_etudiants(self, request, queryset):
        count = queryset.update(actif=False)
        self.message_user(request, f'{count} étudiant(s) désactivé(s).')
    desactiver_etudiants.short_description = 'Désactiver la sélection'