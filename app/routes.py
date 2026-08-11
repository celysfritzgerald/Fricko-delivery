import uuid
import re
from functools import wraps
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app import mail
from sqlalchemy import or_
from flask_mail import Message
from app.models import User, Client, Voyage, Colis
from app.forms import LoginForm, TrackingSearchForm, ClientForm, VoyageForm, ColisForm, UserForm


bp = Blueprint('main', __name__)
main_bp = bp


@main_bp.context_processor
def inject_now():
    """Injecte la date actuelle UTC dans les templates Jinja2."""
    return {'now': datetime.now(timezone.utc)}

def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs uniquement (HTTP 403)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def generate_tracking_number():
    """Génère un identifiant de suivi unique (ex: FRK-8A3B1C9D)."""
    while True:
        code = f"FRK-{uuid.uuid4().hex[:8].upper()}"
        if not Colis.query.filter_by(tracking_id=code).first():
            return code


# ==========================================
# ROUTES PUBLIQUES
# ==========================================

@main_bp.route('/', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def index():
    form = TrackingSearchForm()
    if form.validate_on_submit():
        return redirect(url_for('main.tracking', tracking_id=form.tracking_id.data.strip()))
    
    filtre_exclure_arrives = ~or_(
        Voyage.statut.ilike('%arriv%'),
        Voyage.statut.ilike('%haiti%'),
        Voyage.statut.ilike('%livr%'),
        Voyage.statut.ilike('%termin%')
    )

    prochains_voyages = Voyage.query.filter(
        filtre_exclure_arrives
    ).order_by(Voyage.date_depart.asc()).limit(2).all()

    voyages_actifs = Voyage.query.filter(
        filtre_exclure_arrives
    ).order_by(Voyage.date_depart.desc()).all()

    return render_template(
        'home.html', 
        form=form, 
        voyages=prochains_voyages, 
        voyages_actifs=voyages_actifs
    )

@main_bp.route('/tracking/<tracking_id>')
@limiter.limit("5 per minute")
def tracking(tracking_id):
    colis = Colis.query.filter_by(tracking_id=tracking_id.strip()).first()
    return render_template('tracking.html', colis=colis, search_id=tracking_id)


# ==========================================
# AUTHENTIFICATION
# ==========================================

@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            flash(f'Bienvenue, {user.nom} !', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Identifiants invalides ou compte désactivé.', 'danger')

    return render_template('login.html', form=form)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.index'))


# ==========================================
# DASHBOARD
# ==========================================

@main_bp.route('/dashboard')
@login_required
@limiter.limit("5 per minute")
def dashboard():
    search_query = request.args.get('search', '').strip()
    
    query = Colis.query
    if search_query:
        query = query.filter(Colis.tracking_id.ilike(f"%{search_query}%"))
        
    colis_list = query.order_by(Colis.created_at.desc()).all()
    
    stats = {}
    clients_list = []

    if current_user.is_admin:
        stats = {
            'total_voyages': Voyage.query.count(),
            'total_colis': Colis.query.count(),
            'colis_en_attente': Colis.query.filter_by(statut_livraison='EN_ATTENTE').count(),
            'colis_livres': Colis.query.filter_by(statut_livraison='LIVRE').count(),
        }
        clients_list = Client.query.order_by(Client.created_at.desc()).limit(5).all()
        
    return render_template('dashboard.html', 
                           stats=stats, 
                           colis_list=colis_list, 
                           clients_list=clients_list, 
                           search_query=search_query)


# ==========================================
# CRUD CLIENTS (ADMIN SEULEMENT)
# ==========================================

@main_bp.route('/clients')
@login_required
@admin_required
def clients_list():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    return render_template('clients.html', clients=clients)


@main_bp.route('/clients/create', methods=['GET', 'POST'])
@login_required
@admin_required
def client_create():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            nom=form.nom.data,
            prenom=form.prenom.data,
            telephone=form.telephone.data,
            email=form.email.data,
            adresse=form.adresse.data
        )
        db.session.add(client)
        db.session.commit()
        flash('Client créé avec succès.', 'success')
        return redirect(url_for('main.clients_list'))
    return render_template('clients.html', form=form, action='create')


@main_bp.route('/clients/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def client_edit(id):
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash('Informations du client mises à jour.', 'success')
        return redirect(url_for('main.clients_list'))
    return render_template('clients.html', form=form, client=client, action='edit')


@main_bp.route('/clients/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def client_delete(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash('Client supprimé.', 'info')
    return redirect(url_for('main.clients_list'))


@main_bp.route('/politique-confidentialite')
def politique_confidentialite():
    return render_template('politique_confidentialite.html')

@main_bp.route('/conditions-utilisation')
def conditions_utilisation():
    return render_template('conditions_utilisation.html')


# ==========================================
# CRUD VOYAGES (ADMIN SEULEMENT)
# ==========================================

@main_bp.route('/voyages')
@login_required
@admin_required
def voyages_list():
    voyages = Voyage.query.order_by(Voyage.date_depart.desc()).all()
    return render_template('voyages.html', voyages=voyages)


@main_bp.route('/voyages/create', methods=['GET', 'POST'])
@login_required
@admin_required
def voyage_create():
    form = VoyageForm()
    if form.validate_on_submit():
        voyage = Voyage(
            nom=form.nom.data,
            date_depart=form.date_depart.data,
            date_arrivee_estimee=form.date_arrivee_estimee.data,
            statut=form.statut.data
        )
        db.session.add(voyage)
        db.session.commit()
        flash('Voyage créé avec succès.', 'success')
        return redirect(url_for('main.voyages_list'))
    return render_template('voyages.html', form=form, action='create')


@main_bp.route('/voyages/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def voyage_edit(id):
    voyage = Voyage.query.get_or_404(id)
    form = VoyageForm(obj=voyage)
    if form.validate_on_submit():
        form.populate_obj(voyage)
        db.session.commit()
        flash('Voyage mis à jour.', 'success')
        return redirect(url_for('main.voyages_list'))
    return render_template('voyages.html', form=form, voyage=voyage, action='edit')


@main_bp.route('/voyage/<int:id>/update-status', methods=['POST'])
@login_required
def update_voyage_status(id):
    voyage = Voyage.query.get_or_404(id)
    nouveau_statut = request.form.get('statut')
    
    voyage.statut = nouveau_statut
    db.session.commit()
    
    flash('Statut du voyage mis à jour avec succès !', 'success')
    return redirect(url_for('main.dashboard'))

    
@main_bp.route('/voyages/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def voyage_delete(id):
    voyage = Voyage.query.get_or_404(id)
    db.session.delete(voyage)
    db.session.commit()
    flash('Voyage supprimé.', 'info')
    return redirect(url_for('main.voyages_list'))


# ==========================================
# GESTION DES COLIS
# ==========================================

@main_bp.route('/colis')
@login_required
def colis_list():
    """Affiche la liste complète des colis avec option de recherche."""
    search = request.args.get('search', '').strip()
    query = Colis.query
    if search:
        query = query.filter(Colis.tracking_id.ilike(f"%{search}%"))
    colis_items = query.order_by(Colis.created_at.desc()).all()
    return render_template('colis.html', colis_list=colis_items, search=search, action='list')


@main_bp.route('/colis/create', methods=['GET', 'POST'])
@login_required
@admin_required
def colis_create():
    """Création d'un colis (Réservé aux ADMINS)."""
    form = ColisForm()
    
    clients_db = Client.query.order_by(Client.nom).all()
    form.client_id.choices = [(0, '-- Sélectionner un client --')] + [
        (c.id, f"{c.prenom} {c.nom} ({c.telephone})") for c in clients_db
    ]
    
    voyages_permis = Voyage.query.filter(
        ~or_(
            Voyage.statut.ilike('%route%'),
            Voyage.statut.ilike('%haiti%'),
            Voyage.statut.ilike('%haïti%'),
            Voyage.statut.ilike('%arriv%'),
            Voyage.statut.ilike('%livr%')
        )
    ).order_by(Voyage.date_depart.desc()).all()

    form.voyage_id.choices = [(0, '-- Aucun voyage assigné --')] + [
        (v.id, f"{v.nom} [{v.statut}]") for v in voyages_permis
    ]

    if form.validate_on_submit():
        if form.client_id.data == 0:
            flash("Veuillez sélectionner un client valide.", "danger")
            return render_template('colis.html', form=form, action='create')

        selected_voyage_id = form.voyage_id.data if form.voyage_id.data != 0 else None
        
        if selected_voyage_id:
            voyage = Voyage.query.get(selected_voyage_id)
            if voyage:
                statut_lower = (voyage.statut or '').lower()
                if any(m in statut_lower for m in ['route', 'haiti', 'haïti', 'arriv', 'livr']):
                    flash(f"Action bloquée : Le voyage '{voyage.nom}' est '{voyage.statut}'. Impossible d'y ajouter de nouveaux colis.", 'danger')
                    return render_template('colis.html', form=form, action='create')
                
        auto_tracking_id = generate_tracking_number()
        colis = Colis(
            tracking_id=auto_tracking_id,
            client_id=form.client_id.data,
            voyage_id=selected_voyage_id,
            description=form.description.data,
            poids=form.poids.data,
            quantite=form.quantite.data,
            statut_livraison=form.statut_livraison.data
        )
        if form.statut_livraison.data == 'LIVRE':
            colis.marquer_comme_livre()

        db.session.add(colis)
        db.session.commit()
        flash(f'Colis enregistré avec le numéro : {colis.tracking_id}', 'success')
        return redirect(url_for('main.colis_list'))

    return render_template('colis.html', form=form, action='create')


@main_bp.route('/colis/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def colis_edit(id):
    """Édition complète (ADMIN) ou mise à jour du statut uniquement (USER)."""
    colis = Colis.query.get_or_404(id)

    # ADMIN : Modification complète
    if current_user.is_admin:
        form = ColisForm(original_tracking_id=colis.tracking_id, obj=colis)
        form.client_id.choices = [(c.id, f"{c.prenom} {c.nom} ({c.telephone})") for c in Client.query.order_by(Client.nom).all()]
        form.voyage_id.choices = [(0, '-- Aucun voyage assigné --')] + [(v.id, f"{v.nom} [{v.statut}]") for v in Voyage.query.order_by(Voyage.date_depart.desc()).all()]

        if request.method == 'GET':
            form.voyage_id.data = colis.voyage_id if colis.voyage_id else 0

        if form.validate_on_submit():
            colis.client_id = form.client_id.data
            colis.voyage_id = form.voyage_id.data if form.voyage_id.data != 0 else None
            colis.description = form.description.data
            colis.poids = form.poids.data
            colis.quantite = form.quantite.data
            
            if form.statut_livraison.data == 'LIVRE' and colis.statut_livraison != 'LIVRE':
                colis.marquer_comme_livre()
            else:
                colis.statut_livraison = form.statut_livraison.data

            db.session.commit()
            flash('Colis mis à jour.', 'success')
            return redirect(url_for('main.colis_list'))

        return render_template('colis.html', form=form, colis=colis, action='edit')

    # USER : Modification du statut uniquement
    else:
        if request.method == 'POST':
            nouveau_statut = request.form.get('statut_livraison')
            statuts_valides = ['EN_ATTENTE', 'EN_TRANSIT', 'EN_ROUTE', 'EN_HAITI', 'ARRIVE', 'LIVRE']
            
            if nouveau_statut in statuts_valides:
                if nouveau_statut == 'LIVRE' and colis.statut_livraison != 'LIVRE':
                    colis.marquer_comme_livre()
                else:
                    colis.statut_livraison = nouveau_statut
                
                db.session.commit()
                flash(f'Statut du colis {colis.tracking_id} mis à jour : {nouveau_statut}', 'success')
            else:
                flash('Statut invalide.', 'danger')
                
            return redirect(url_for('main.colis_list'))

        # CHARGEMENT DU TEMPLATE : Nom corrigé pour éviter l'erreur TemplateNotFound
        return render_template('colis_status.html', colis=colis)


@main_bp.route('/colis/<int:id>/livrer', methods=['POST'])
@login_required
def colis_marquer_livre(id):
    """Raccourci rapide pour marquer un colis comme LIVRÉ."""
    colis = Colis.query.get_or_404(id)
    colis.marquer_comme_livre()
    db.session.commit()
    flash(f'Le colis {colis.tracking_id} a été marqué comme LIVRÉ avec succès.', 'success')
    return redirect(request.referrer or url_for('main.colis_list'))


@main_bp.route('/colis/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def colis_delete(id):
    """Suppression d'un colis (Réservé aux ADMINS)."""
    colis = Colis.query.get_or_404(id)
    db.session.delete(colis)
    db.session.commit()
    flash('Colis supprimé.', 'info')
    return redirect(url_for('main.colis_list'))


# ==========================================
# CRUD UTILISATEURS (ADMIN UNIQUEMENT)
# ==========================================

@main_bp.route('/users')
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)


@main_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash('Le mot de passe est obligatoire pour un nouvel utilisateur.', 'danger')
            return render_template('users.html', form=form, action='create')

        user = User(
            nom=form.nom.data,
            email=form.email.data.strip().lower(),
            role=form.role.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Utilisateur créé avec succès.', 'success')
        return redirect(url_for('main.users_list'))

    return render_template('users.html', form=form, action='create')


@main_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(id):
    user = User.query.get_or_404(id)
    form = UserForm(original_email=user.email, obj=user)

    if form.validate_on_submit():
        user.nom = form.nom.data
        user.email = form.email.data.strip().lower()
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash('Utilisateur mis à jour.', 'success')
        return redirect(url_for('main.users_list'))

    return render_template('users.html', form=form, user=user, action='edit')


@main_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def user_delete(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('main.users_list'))

    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé.', 'info')
    return redirect(url_for('main.users_list'))


def est_email_valide(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def nettoyer_texte(texte):
    if not texte:
        return ""
    return re.sub(r'[\r\n]', ' ', texte).strip()

@main_bp.route('/contact', methods=['POST'])
def handle_contact():
    nom = nettoyer_texte(request.form.get('nom'))
    email = request.form.get('email', '').strip()
    sujet = nettoyer_texte(request.form.get('sujet', 'Nouveau message de contact'))
    message_contenu = request.form.get('message', '').strip()

    if not nom or not email or not message_contenu:
        flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        return redirect(url_for('main.index') + '#contact')

    try:
        destinataire = current_app.config.get('MAIL_RECIPIENT') or current_app.config.get('MAIL_USERNAME')
        
        msg = Message(
            subject=f"[LOGITRACK Contact] {sujet}",
            recipients=[destinataire],
            reply_to=email
        )

        msg.body = f"Expéditeur : {nom}\nEmail : {email}\n\nMessage :\n{message_contenu}"

        mail.send(msg)
        flash('Votre message a été envoyé avec succès !', 'success')

    except Exception as e:
        print(f"\n[ERREUR EMAIL] : {e}\n")
        flash(f"Erreur d'envoi : {e}", 'danger')

    return redirect(url_for('main.index') + '#contact')