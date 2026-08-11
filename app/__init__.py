import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

# Configuration du Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialisation de Flask-Mail
mail = Mail()


def create_app():
    app = Flask(__name__)
    
    # Configuration de base de l'application
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_cle_secrete_ici')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuration de Flask-Mail via variables d'environnement
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
    app.config['MAIL_RECIPIENT'] = os.environ.get('MAIL_RECIPIENT', os.environ.get('MAIL_USERNAME'))

    

    # Liaison des extensions à l'instance Flask
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)


    app.config.update(
    SESSION_COOKIE_HTTPONLY=True,     # Empêche l'accès aux cookies via JavaScript (XSS)
    SESSION_COOKIE_SECURE=True,       # Force l'envoi des cookies uniquement via HTTPS
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SECURE=True,
)

    # -------------------------------------------------------------
    # INJECTEUR DE CONTEXTE GLOBAL
    # Rend ces variables accessibles automatiquement dans tous vos templates HTML
    # -------------------------------------------------------------
    @app.context_processor
    def inject_company_info():
        return dict(
            app_name=os.environ.get('APP_NAME', 'Fricko Delivery'),
            company_phone=os.environ.get('COMPANY_PHONE', '+509 3910-2160'),
            company_email=os.environ.get('COMPANY_EMAIL', 'celysfritzgerald39@gmail.com')
        )

    # Enregistrement des Blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app