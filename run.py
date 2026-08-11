from app import create_app, db
from app.models import User, Client, Voyage, Colis

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Raccourcis pour tester dans le terminal via `flask shell`."""
    return {'db': db, 'User': User, 'Client': Client, 'Voyage': Voyage, 'Colis': Colis}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)