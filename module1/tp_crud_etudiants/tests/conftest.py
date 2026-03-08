# contient les fonction de preparation
"""
conftest.py : les fixtures définies ici sont disponibles dans
TOUS les fichiers de test sans qu'il soit nécessaire de les importer.
Une fixture est une fonction qui prépare des données ou un état
avant chaque test, puis effectue le nettoyage après.
"""

import pytest
from api_etudiants import create_app, db as _db



@pytest.fixture(scope='session')
def app():
    """
    Crée l'application Flask en mode 'testing'.
    scope='session' : cette fixture est exécutée UNE SEULE FOIS
    pour toute la session de tests.
    La config 'testing' utilise une BDD SQLite en mémoire (:memory:).
    """
    application = create_app('testing')
    with application.app_context():
        _db.create_all()
        yield application   # Les tests s'exécutent ici
        _db.drop_all()      # Nettoyage après la session


@pytest.fixture(scope='function')
def db(app):
    """
    Fournit une base de données propre pour CHAQUE fonction de test.
    scope='function' : cette fixture est exécutée avant et après
    chaque test individuel.
    Après chaque test : rollback + suppression de toutes les lignes.
    """
    with app.app_context():
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    """
    Client HTTP de test fourni par Flask.
    Permet de simuler des requêtes GET, POST, PUT, DELETE
    sans démarrer un vrai serveur HTTP.
    """
    return app.test_client()


@pytest.fixture
def auth_headers(client, db):
    """
    Fixture qui inscrit un utilisateur de test, obtient son token JWT
    et retourne l'en-tête 'Authorization: Bearer <token>'.
    Utilisation dans un test :
        def test_route(client, auth_headers): ...
    """
    # 1. Créer un utilisateur de test
    user = User(nom='Admin', prenom='Test', email='admin@test.com')
    user.password = 'AdminPass123!'
    db.session.add(user)
    db.session.commit()

    # 2. Obtenir le token via l’API
    rep = client.post('/api/v1/auth/token',
                      json={'email': 'admin@test.com', 'password': 'AdminPass123!'})
    token = rep.get_json()['access_token']

    # 3. Renvoyer l’en-tête prêt à l’emploi
    return {'Authorization': f'Bearer {token}'}