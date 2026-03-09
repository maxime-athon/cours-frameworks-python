from django.urls import path
from . import views
from .views import TokenObtainView, TokenRefreshView, ProfilView, LogoutView

app_name = 'etudiants'  # Namespace pour éviter les conflits

urlpatterns = [
    path('', views.liste_etudiants, name='liste'),
    path('<int:pk>/', views.detail_etudiant, name='detail'),
    path('nouveau/', views.formulaire_etudiant, name='creer'),
    path('<int:pk>/modifier/', views.formulaire_etudiant, name='modifier'),
    path('<int:pk>/supprimer/', views.supprimer_etudiant, name='supprimer'),
    path('token/', TokenObtainView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfilView.as_view(), name='profil'),
    path('logout/', LogoutView.as_view(), name='logout'),
]