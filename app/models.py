from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    """Utilisateurs internes (ADMIN ou USER)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='USER')  # ADMIN ou USER
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        """Hache et définit le mot de passe de l'utilisateur."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifie si le mot de passe fourni correspond au hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Vérifie si l'utilisateur possède le rôle ADMIN."""
        return self.role == 'ADMIN'


# ==========================================
# FLASK-LOGIN USER LOADER
# ==========================================
@login_manager.user_loader
def load_user(user_id):
    """Charge l'utilisateur en mémoire depuis la session via son ID."""
    return User.query.get(int(user_id))


class Client(db.Model):
    """Clients destinataires/expéditeurs."""
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    adresse = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    colis = db.relationship('Colis', backref='client', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.prenom} {self.nom}>"


class Voyage(db.Model):
    """Voyages USA -> Haïti."""
    __tablename__ = 'voyages'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    date_depart = db.Column(db.Date, nullable=False)
    date_arrivee_estimee = db.Column(db.Date, nullable=False)
    statut = db.Column(db.String(30), nullable=False, default='EN_PREPARATION')  # EN_PREPARATION, EN_ROUTE, EN_HAITI
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    colis = db.relationship('Colis', backref='voyage', lazy=True)

    def __repr__(self):
        return f"<Voyage {self.nom} [{self.statut}]>"


class Colis(db.Model):
    """Colis expédiés."""
    __tablename__ = 'colis'

    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    voyage_id = db.Column(db.Integer, db.ForeignKey('voyages.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    poids = db.Column(db.Float, nullable=True)
    quantite = db.Column(db.Integer, default=1, nullable=False)
    statut_livraison = db.Column(db.String(20), nullable=False, default='EN_ATTENTE')  # EN_ATTENTE, EN_ROUTE, EN_HAITI, LIVRE
    date_livraison = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def est_livre(self):
        return self.statut_livraison == 'LIVRE'

    def marquer_comme_livre(self):
        """Marque le colis comme livré avec la date et l'heure courante du serveur."""
        self.statut_livraison = 'LIVRE'
        self.date_livraison = datetime.now(timezone.utc)

    @property
    def etape_suivi(self):
        """
        Calcule l'étape (1 à 4) pour l'affichage client :
        1: Colis reçu
        2: En route
        3: En Haïti
        4: Livré
        """
        if self.statut_livraison == 'LIVRE':
            return 4
        if self.statut_livraison in ['EN_HAITI', 'ARRIVE']:
            return 3
        if self.statut_livraison in ['EN_ROUTE', 'EN_TRANSIT']:
            return 2
            
        if self.voyage:
            if self.voyage.statut == 'EN_HAITI':
                return 3
            if self.voyage.statut == 'EN_ROUTE':
                return 2
        return 1

    def __repr__(self):
        return f"<Colis {self.tracking_id} [{self.statut_livraison}]>"