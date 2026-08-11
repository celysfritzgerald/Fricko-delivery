import os
from app import create_app, db
from app.models import User, Client, Voyage, Colis

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Raccourcis pour tester dans le terminal via `flask shell`."""
    return {'db': db, 'User': User, 'Client': Client, 'Voyage': Voyage, 'Colis': Colis}


if __name__ == '__main__':
    # Détecte FLASK_DEBUG dans l'environnement.
    # En local (si FLASK_DEBUG=True), debug sera True.
    # Sur Railway ou par défaut, debug sera False.
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    
    # Récupère le port fourni par Railway ou utilise 5000 par défaut
    port = int(os.getenv('PORT', 5000))
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)