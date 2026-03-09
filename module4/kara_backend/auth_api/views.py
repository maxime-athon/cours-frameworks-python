from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, redirect
from django.contrib import messages

def connexion(request):
    if request.user.is_authenticated:
        return redirect('etudiants:liste')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenue, {user.first_name or user.username} !')
            next_url = request.GET.get('next', 'etudiants:liste')
            return redirect(next_url)
        else:
            messages.error(request, 'Identifiant ou mot de passe incorrect.')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/connexion.html', {'form': form})

def deconnexion(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Vous avez été déconnecté.')
        return redirect('auth:connexion')

@permission_required('etudiants.delete_etudiant', raise_exception=True)
def supprimer_admin(request, pk):
    # Exemple de vue protégée par permission
    pass