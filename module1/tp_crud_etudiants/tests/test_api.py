# contient les cas de test organises par classes.

"""Tests pour les routes utilisateurs et l'authentification."""
import pytest


class TestInscription:
    """Tests pour POST /api/v1/auth/register"""

    def test_inscription_valide(self, client, db):
        """Un utilisateur peut s'inscrire avec des données correctes."""
        rep = client.post('/api/v1/auth/register', json={
            'nom': 'Koffi', 'prenom': 'Amina',
            'email': 'amina@kara.tg', 'password': 'MotDePasse123!'
        })
        assert rep.status_code == 201
        data = rep.get_json()
        assert 'user' in data
        assert data['user']['email'] == 'amina@kara.tg'
        assert 'password' not in data['user']  # Le mdp ne doit JAMAIS être exposé !

    def test_email_duplique(self, client, db):
        """Deux inscriptions avec le même email -> 409 Conflict."""
        payload = {'nom': 'A', 'prenom': 'B',
                   'email': 'dup@test.com', 'password': 'MotDePasse123!'}
        client.post('/api/v1/auth/register', json=payload)
        rep2 = client.post('/api/v1/auth/register', json=payload)
        assert rep2.status_code == 409

    def test_donnees_incompletes(self, client, db):
        """Inscription sans email -> 422 Unprocessable Entity."""
        rep = client.post('/api/v1/auth/register',
                          json={'nom': 'A', 'prenom': 'B', 'password': 'X1!'})
        assert rep.status_code == 422

    @pytest.mark.parametrize('mdp,attendu', [
        ('court', 422),             # Trop court (< 8 caractères)
        ('touttoutminu1', 422),     # Pas de majuscule
        ('MotDePasse123!', 201),    # Valide
    ])
    def test_validation_mdp(self, client, db, mdp, attendu):
        """Validation du mot de passe avec plusieurs jeux de données."""
        rep = client.post('/api/v1/auth/register', json={
            'nom': 'T', 'prenom': 'U',
            'email': f'user_{mdp[:4]}@test.com',
            'password': mdp
        })
        assert rep.status_code == attendu


class TestConnexion:
    """Tests pour POST /api/v1/auth/token"""

    @pytest.fixture(autouse=True)
    def creer_user(self, client, db):
        """Créer un utilisateur avant chaque test de la classe."""
        client.post('/api/v1/auth/register', json={
            'nom': 'Admin', 'prenom': 'Test',
            'email': 'admin@test.com', 'password': 'Admin123!'
        })

    def test_connexion_succes(self, client, db):
        """La connexion retourne un access_token et un refresh_token."""
        rep = client.post('/api/v1/auth/token',
                          json={'email': 'admin@test.com', 'password': 'Admin123!'})
        assert rep.status_code == 200
        data = rep.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'Bearer'

    def test_mauvais_mdp(self, client, db):
        """Mauvais mot de passe -> 401 Unauthorized."""
        rep = client.post('/api/v1/auth/token',
                          json={'email': 'admin@test.com', 'password': 'Mauvais!'})
        assert rep.status_code == 401

    def test_route_protegee_sans_token(self, client, db):
        """Accéder à /me sans token -> 401."""
        rep = client.get('/api/v1/auth/me')
        assert rep.status_code == 401

    def test_route_protegee_avec_token(self, client, db, auth_headers):
        """Accéder à /me avec un token valide -> 200."""
        rep = client.get('/api/v1/auth/me', headers=auth_headers)
        assert rep.status_code == 200
        assert 'email' in rep.get_json()


class TestEtudiants:
    """Tests CRUD pour /api/etudiants"""

    def test_liste_vide(self, client, db):
        """Au départ, la liste des étudiants est vide."""
        rep = client.get('/api/etudiants')
        assert rep.status_code == 200
        assert rep.get_json()['total'] == 0

    def test_creer_etudiant(self, client, db, auth_headers):
        """Créer un étudiant retourne 201 avec les données créées."""
        rep = client.post('/api/etudiants', headers=auth_headers, json={
            'matricule': 'ETU001', 'nom': 'Koffi', 'prenom': 'Jean',
            'email': 'jean@kara.tg', 'filiere': 'Maths', 'annee': 2
        })
        assert rep.status_code == 201
        data = rep.get_json()
        assert data['matricule'] == 'ETU001'
        assert 'id' in data  # L'id est généré automatiquement

    def test_etudiant_inexistant(self, client, db):
        """Récupérer un étudiant avec un id inconnu -> 404."""
        rep = client.get('/api/etudiants/9999')
        assert rep.status_code == 404

    def test_supprimer_etudiant(self, client, db, auth_headers):
        """Créer puis supprimer un étudiant : vérifier qu'il n'existe plus."""
        # 1. Créer
        cree = client.post('/api/etudiants', headers=auth_headers, json={
            'matricule': 'DEL001', 'nom': 'A', 'prenom': 'B',
            'email': 'del@test.com', 'filiere': 'Info', 'annee': 1
        })
        eid = cree.get_json()['id']
        # 2. Supprimer
        rep = client.delete(f'/api/etudiants/{eid}', headers=auth_headers)
        assert rep.status_code == 200
        # 3. Vérifier que la ressource n'existe plus
        assert client.get(f'/api/etudiants/{eid}').status_code == 404