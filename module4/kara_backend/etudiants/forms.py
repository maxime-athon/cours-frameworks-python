from django import forms
from django.core.exceptions import ValidationError
from .models import Etudiant


class EtudiantForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = [
            'nom', 'prenom', 'email', 'matricule',
            'filiere', 'annee', 'date_naissance', 'actif'
        ]
        # Personnalisation des widgets HTML (Bootstrap)
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Mensah'
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Amina'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'prenom.nom@kara.tg'
            }),
            'matricule': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: UK2024001'
            }),
            'filiere': forms.Select(attrs={'class': 'form-select'}),
            'annee': forms.Select(attrs={'class': 'form-select'}),
            'date_naissance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # Validation individuelle : email unique
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        qs = Etudiant.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Cet email est déjà utilisé.')
        return email

    # Validation individuelle : matricule format
    def clean_matricule(self):
        matricule = self.cleaned_data.get('matricule', '').upper().strip()
        if len(matricule) < 5:
            raise ValidationError('Le matricule doit comporter au moins 5 caractères.')
        return matricule

    # Validation croisée : cohérence filière/année
    def clean(self):
        cleaned = super().clean()
        filiere = cleaned.get('filiere')
        annee = cleaned.get('annee')
        if filiere and annee:
            if filiere.code.startswith('M') and annee < 4:
                raise ValidationError('Un étudiant en Master doit être en année 4 ou 5.')
        return cleaned