import os
import click
from app import create_app, db
from app.models import User, Client, Voyage, Colis

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Raccourcis pour tester dans le terminal via `flask shell`."""
    return {'db': db, 'User': User, 'Client': Client, 'Voyage': Voyage, 'Colis': Colis}


@app.cli.command("create-admin")
def create_admin():
    """Commande CLI pour créer un compte administrateur."""
    email = input("Email de l'admin : ").strip()
    nom = input("Nom de l'admin : ").strip()
    password = input("Mot de passe : ").strip()

    if not email or not nom or not password:
        click.echo("❌ Tous les champs sont obligatoires.")
        return

    # Vérification si l'utilisateur existe déjà
    user_exists = User.query.filter_by(email=email).first()
    if user_exists:
        click.echo("❌ Un utilisateur avec cet email existe déjà.")
        return

    # Création de l'administrateur
    admin = User(
        nom=nom,
        email=email,
        role='ADMIN',
        is_active=True
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo(f"✅ Administrateur '{nom}' ({email}) créé avec succès !")


if __name__ == '__main__':
    # Détecte FLASK_DEBUG dans l'environnement.
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    
    # Récupère le port fourni par Railway ou utilise 5000 par défaut
    port = int(os.getenv('PORT', 5000))
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)