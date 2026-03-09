from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView as BaseRefreshView
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Etudiant
from .forms import EtudiantForm
from .serializers import EtudiantSerializer

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'prenom': user.first_name,
            'nom': user.last_name,
            'is_staff': user.is_staff,
        }
        return data

class TokenObtainView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    permission_classes = [permissions.AllowAny]

class TokenRefreshView(BaseRefreshView):
    permission_classes = [permissions.AllowAny]

class ProfilView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'prenom': user.first_name,
            'nom': user.last_name,
            'is_staff': user.is_staff,
        })

    def patch(self, request):
        user = request.user
        for champ in ['first_name', 'last_name', 'email']:
            if champ in request.data:
                setattr(user, champ, request.data[champ])
        user.save()
        return Response({'message': 'Profil mis à jour.'})

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data['refresh'])
            token.blacklist()
            return Response({'message': 'Déconnexion réussie.'})
        except Exception as e:
            return Response({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EtudiantViewSet(viewsets.ModelViewSet):
    """
    API endpoint pour voir ou modifier les étudiants.
    """
    queryset = Etudiant.objects.all().order_by('-date_inscription')
    serializer_class = EtudiantSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============================================================
# VUES STANDARD (Django Template)
# ============================================================

@login_required
def liste_etudiants(request):
    etudiants = Etudiant.objects.filter(actif=True)
    return render(request, 'etudiants/liste.html', {'etudiants': etudiants})

@login_required
def detail_etudiant(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    return render(request, 'etudiants/detail.html', {'etudiant': etudiant})

@login_required
def formulaire_etudiant(request, pk=None):
    if pk:
        etudiant = get_object_or_404(Etudiant, pk=pk)
        form = EtudiantForm(request.POST or None, request.FILES or None, instance=etudiant)
    else:
        etudiant = None
        form = EtudiantForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Étudiant enregistré avec succès.')
        return redirect('etudiants:liste')

    return render(request, 'etudiants/formulaire.html', {'form': form, 'etudiant': etudiant})

@login_required
def supprimer_etudiant(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    if request.method == 'POST':
        etudiant.actif = False
        etudiant.save()
        messages.warning(request, 'Étudiant supprimé (désactivé).')
        return redirect('etudiants:liste')
    return render(request, 'etudiants/confirmation_suppression.html', {'etudiant': etudiant})