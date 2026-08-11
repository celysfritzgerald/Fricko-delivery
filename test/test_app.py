import pytest
from app import create_app, db
from app.models import User, Client, Voyage, Colis
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    """Configuration de l'application en mode test avec base SQLite en mémoire."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Désactive CSRF pour simplifier les requêtes de test
        "RATELIMIT_ENABLED": False  # Désactive le rate-limiter pour les tests
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    """Création des données de test de base."""
    # Création d'un Admin et d'un Utilisateur standard
    admin = User(nom="Admin Test", email="admin@test.com", role="ADMIN")
    admin.set_password("password123")
    
    user = User(nom="User Test", email="user@test.com", role="USER")
    user.set_password("password123")

    # Création d'un client
    cli = Client(nom="Jean", prenom="Paul", telephone="+50937000000", email="jean@test.com")

    db.session.add_all([admin, user, cli])
    db.session.commit()

    # Création d'un colis lié
    colis = Colis(
        tracking_id="FRK-TEST001",
        client_id=cli.id,
        description="Boîte de vêtements",
        poids=15.0,
        statut_livraison="EN_ATTENTE"
    )
    db.session.add(colis)
    db.session.commit()

    return {"admin": admin, "user": user, "client": cli, "colis": colis}


# ==========================================
# TESTS D'AUTHENTIFICATION ET SÉCURITÉ
# ==========================================

def test_login_logout(client, init_database):
    """Vérifie la connexion et la déconnexion d'un utilisateur."""
    # Connexion valide
    res = client.post('/login', data={'email': 'admin@test.com', 'password': 'password123'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Bienvenue' in res.data or b'Tableau de Bord' in res.data

    # Déconnexion
    res_logout = client.get('/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b'connect' in res_logout.data.lower()

def test_acces_admin_restreint(client, init_database):
    """Vérifie qu'un rôle USER ne peut pas accéder aux routes ADMIN (ex: /users)."""
    # Connexion en tant que simple USER
    client.post('/login', data={'email': 'user@test.com', 'password': 'password123'})
    
    # Tentative d'accès à la liste des utilisateurs (Réservée ADMIN)
    res = client.get('/users')
    assert res.status_code == 403  # Forbidden


# ==========================================
# TESTS METIER : COLIS & SUIVI
# ==========================================

def test_recherche_tracking_public(client, init_database):
    """Vérifie qu'un client public peut suivre son colis sans se connecter."""
    res = client.get('/tracking/FRK-TEST001')
    assert res.status_code == 200
    assert b'FRK-TEST001' in res.data
    assert b'Bo\xc3\xaete de v\xc3\xaatement' in res.data or b'v\xc3\xaatement' in res.data

def test_mise_a_jour_statut_colis(client, init_database):
    """Vérifie la mise à jour du statut d'un colis par un employé."""
    client.post('/login', data={'email': 'user@test.com', 'password': 'password123'})
    
    colis_id = init_database["colis"].id
    res = client.post(f'/colis/edit/{colis_id}', data={'statut_livraison': 'EN_ROUTE'}, follow_redirects=True)
    
    assert res.status_code == 200
    
    # Vérification en BDD
    colis_db = Colis.query.get(colis_id)
    assert colis_db.statut_livraison == 'EN_ROUTE'