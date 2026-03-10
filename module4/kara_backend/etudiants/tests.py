from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from etudiants.models import Etudiant, Filiere, Note

# ============================================================
# TESTS DES MODELES
# ============================================================
class EtudiantModelTest(TestCase):
    def setUp(self):
        # On mock la tâche asynchrone pour ne pas polluer la sortie des tests
        # et pour isoler notre test des services externes (email, etc.)
        patcher = patch('etudiants.signals.envoyer_email_bienvenue.delay')
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.filiere = Filiere.objects.create(code='L3', nom='Licence 3')
        self.etudiant = Etudiant.objects.create(
            nom='Mensah', prenom='Amina', email='amina@kara.tg',
            matricule='UK2024001', filiere=self.filiere, annee=3
        )

    def test_str_representation(self):
        self.assertEqual(str(self.etudiant), 'Amina Mensah (UK2024001)')

    def test_nom_complet(self):
        self.assertEqual(self.etudiant.nom_complet, 'Amina Mensah')

    def test_moyenne_sans_notes(self):
        self.assertEqual(self.etudiant.moyenne, 0.0)

    def test_moyenne_avec_notes(self):
        Note.objects.create(etudiant=self.etudiant, matiere='Maths', valeur=16.0, semestre='S1')
        Note.objects.create(etudiant=self.etudiant, matiere='Info', valeur=14.0, semestre='S1')
        self.assertAlmostEqual(self.etudiant.moyenne, 15.0, places=2)

    def test_est_admis_vrai(self):
        Note.objects.create(etudiant=self.etudiant, matiere='Maths', valeur=12.0, semestre='S1')
        self.assertTrue(self.etudiant.est_admis)

    def test_est_admis_faux(self):
        Note.objects.create(etudiant=self.etudiant, matiere='Maths', valeur=8.0, semestre='S1')
        self.assertFalse(self.etudiant.est_admis)

    def test_signal_bienvenue_envoye(self):
        """Vérifie que le signal d'envoi d'email est bien appelé à la création."""
        # L'étudiant a été créé dans setUp(), on vérifie que le mock a été appelé.
        self.mock_delay.assert_called_once_with('amina@kara.tg', 'Amina Mensah')


# ============================================================
# TESTS DE L'API REST (DRF)
# ============================================================
class EtudiantAPITest(APITestCase):
    def setUp(self):
        patcher = patch('etudiants.signals.envoyer_email_bienvenue.delay')
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.filiere = Filiere.objects.create(code='L2', nom='Licence 2')
        self.user = User.objects.create_user(username='testuser', password='Azerty123!')
        # Obtenir le token JWT
        url = reverse('etudiants:token_obtain_pair')
        rep = self.client.post(url, {'username': 'testuser', 'password': 'Azerty123!'}, format='json')
        self.token = rep.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        self.etudiant = Etudiant.objects.create(
            nom='Test', prenom='User', email='test@kara.tg',
            matricule='UK2024999', filiere=self.filiere, annee=2
        )
        # Le mock a été appelé une fois dans le setup, on le réinitialise
        # pour que les tests suivants partent d'un état propre.
        self.mock_delay.reset_mock()

    def test_lister_etudiants(self):
        url = reverse('etudiant-list')
        rep = self.client.get(url)
        self.assertEqual(rep.status_code, status.HTTP_200_OK)
        self.assertIn('results', rep.data)

    def test_creer_etudiant(self):
        url = reverse('etudiant-list')
        donnees = {
            'nom': 'Koffi', 'prenom': 'Jean',
            'email': 'jean@kara.tg', 'matricule': 'UK2024002',
            'filiere': self.filiere.pk, 'annee': 2,
        }
        rep = self.client.post(url, donnees, format='json')
        self.assertEqual(rep.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Etudiant.objects.count(), 2)
        # On vérifie que la tâche asynchrone a bien été appelée
        self.mock_delay.assert_called_once_with('jean@kara.tg', 'Jean Koffi')

    def test_email_duplique_retourne_400(self):
        url = reverse('etudiant-list')
        donnees = {
            'nom': 'Autre', 'prenom': 'Personne',
            'email': 'test@kara.tg', # déjà pris
            'matricule': 'UK2024003',
            'filiere': self.filiere.pk, 'annee': 1,
        }
        rep = self.client.post(url, donnees, format='json')
        self.assertEqual(rep.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', rep.data)

    def test_acces_sans_token_retourne_401(self):
        self.client.credentials()  # Supprimer le token
        rep = self.client.get(reverse('etudiant-list'))
        self.assertEqual(rep.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_modifier_etudiant(self):
        url = reverse('etudiant-detail', kwargs={'pk': self.etudiant.pk})
        rep = self.client.patch(url, {'annee': 3}, format='json')
        self.assertEqual(rep.status_code, status.HTTP_200_OK)
        self.etudiant.refresh_from_db()
        self.assertEqual(self.etudiant.annee, 3)

    def test_supprimer_etudiant(self):
        url = reverse('etudiant-detail', kwargs={'pk': self.etudiant.pk})
        rep = self.client.delete(url)
        self.assertEqual(rep.status_code, status.HTTP_204_NO_CONTENT)