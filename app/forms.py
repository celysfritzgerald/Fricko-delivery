from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, IntegerField, TextAreaField, DateField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models import User, Colis


class LoginForm(FlaskForm):
    email = StringField('Adresse e-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')


class TrackingSearchForm(FlaskForm):
    tracking_id = StringField('Numéro de suivi (Tracking ID)', validators=[DataRequired(), Length(min=3, max=50)])
    submit = SubmitField('SUIVRE MON COLIS')


class ClientForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    prenom = StringField('Prénom', validators=[DataRequired(), Length(max=100)])
    telephone = StringField('Téléphone', validators=[DataRequired(), Length(max=30)])
    email = StringField('E-mail', validators=[Optional(), Email(), Length(max=120)])
    adresse = TextAreaField('Adresse', validators=[Optional()])
    submit = SubmitField('Enregistrer le client')


class VoyageForm(FlaskForm):
    nom = StringField('Nom du Voyage', validators=[DataRequired(), Length(max=100)])
    date_depart = DateField('Date de départ', validators=[DataRequired()], format='%Y-%m-%d')
    date_arrivee_estimee = DateField('Date d\'arrivée estimée', validators=[DataRequired()], format='%Y-%m-%d')
    statut = SelectField('Statut du Voyage', choices=[
        ('En préparation', 'En préparation'),
        ('En transit', 'En transit'),
        ('En douane', 'En douane'),
        ('Arrivé en Haïti', 'Arrivé en Haïti'),  # <-- Sélectionner ceci masquera le voyage de l'accueil
        ('Livré', 'Livré')
    ], validators=[DataRequired()])
    submit = SubmitField('Enregistrer le voyage')

class ColisForm(FlaskForm):
    tracking_id = StringField('Numéro de suivi', validators=[Optional()]) # <--- Ajouté ici
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    voyage_id = SelectField('Voyage Associé', coerce=int, validators=[Optional()])
    description = StringField('Description de la marchandise', validators=[DataRequired()])
    poids = FloatField('Poids (lbs / kg)', validators=[Optional()])
    quantite = IntegerField('Quantité de paquets', default=1, validators=[DataRequired()])
    statut_livraison = SelectField('Statut de Livraison', choices=[
        ('EN_ATTENTE', 'En Attente / Reçu à l\'entrepôt'),
        ('EN_TRANSIT', 'En Transit'),
        ('ARRIVE', 'Arrivé à destination'),
        ('LIVRE', 'Livré au destinataire')
    ], default='EN_ATTENTE')
    submit = SubmitField('Enregistrer le colis')
        
    def __init__(self, original_tracking_id=None, *args, **kwargs):
        super(ColisForm, self).__init__(*args, **kwargs)
        self.original_tracking_id = original_tracking_id

    def validate_tracking_id(self, field):
        if field.data != self.original_tracking_id:
            if Colis.query.filter_by(tracking_id=field.data).first():
                raise ValidationError('Ce Tracking ID est déjà utilisé par un autre colis.')


class UserForm(FlaskForm):
    nom = StringField('Nom complet', validators=[DataRequired(), Length(max=100)])
    email = StringField('Adresse e-mail', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Mot de passe', validators=[Optional(), Length(min=6)])
    role = SelectField('Rôle', choices=[('USER', 'Utilisateur (Agent)'), ('ADMIN', 'Administrateur')], default='USER')
    is_active = BooleanField('Compte actif', default=True)
    submit = SubmitField('Enregistrer l\'utilisateur')

    def __init__(self, original_email=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if field.data != self.original_email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Cet email est déjà attribué à un autre compte.')