from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models.user import User
from extensions import db, mail
from flask_mail import Message
from services.auth_service import register_user, login_user

# Créer un namespace pour les opérations d'authentification
ns = Namespace("auth", description="Opérations d'authentification")

# Modèle pour l'inscription
register_model = ns.model("Register", {
    "username": fields.String(required=True, description="Nom d'utilisateur"),
    "email": fields.String(required=True, description="Adresse e-mail"),
    "password": fields.String(required=True, description="Mot de passe"),
    "confirm_password": fields.String(required=True, description="Confirmation du mot de passe"),
    "role": fields.String(required=True, enum=["farmer", "expert"], description="Rôle de l'utilisateur")
})

# Modèle pour la connexion
login_model = ns.model("Login", {
    "email": fields.String(required=True, description="Adresse e-mail"),
    "password": fields.String(required=True, description="Mot de passe")
})

# Modèle pour la mise à jour du profil
update_profile_model = ns.model("UpdateProfile", {
    "username": fields.String(required=False, description="Nouveau nom d'utilisateur"),
    "email": fields.String(required=False, description="Nouvel e-mail")
})

profile_model = ns.model("Profile", {
    "username": fields.String,
    "email": fields.String,
    "role": fields.String,
    "is_admin": fields.Boolean
})

# Modèle pour la réinitialisation du mot de passe
reset_password_model = ns.model("ResetPassword", {
    "old_password": fields.String(required=True, description="Ancien mot de passe"),
    "new_password": fields.String(required=True, description="Nouveau mot de passe")
})

# Modèle pour la demande de réinitialisation de mot de passe
reset_password_request_model = ns.model("ResetPasswordRequest", {
    "email": fields.String(required=True, description="Adresse e-mail de l'utilisateur")
})

# Modèle pour la réinitialisation du mot de passe via e-mail
reset_password_email_model = ns.model("ResetPasswordEmail", {
    "token": fields.String(required=True, description="Token de réinitialisation"),
    "new_password": fields.String(required=True, description="Nouveau mot de passe")
})

# Endpoint pour l'inscription
@ns.route("/register")
class Register(Resource):
    @ns.expect(register_model)
    def post(self):
        data = ns.payload

        # Vérifier que les mots de passe correspondent
        if data["password"] != data["confirm_password"]:
            return {"message": "Les mots de passe ne correspondent pas"}, 400

        # Vérifier que l'e-mail n'est pas déjà utilisé
        if User.query.filter_by(email=data["email"]).first():
            return {"message": "Email déjà utilisé"}, 400

        # Vérifier que le rôle est valide
        if data["role"] not in ["farmer", "expert"]:
            return {"message": "Rôle invalide, doit être 'farmer' ou 'expert'"}, 400

        # Créer un nouvel utilisateur
        user = register_user(data["username"], data["email"], data["password"], data["role"])
        return {"message": "Utilisateur créé avec succès", "role": user.role}, 201

# Endpoint pour la connexion
@ns.route("/login")
class Login(Resource):
    @ns.expect(login_model)
    def post(self):
        data = ns.payload

        # Vérifier les identifiants de l'utilisateur
        user = login_user(data["email"], data["password"])
        if user:
            # Créer un token JWT
            token = create_access_token(identity=str(user.id))  # Convertir l'ID en chaîne de caractères
            return {"access_token": token, "role": user.role}, 200
        return {"message": "Identifiants invalides"}, 401

# Endpoint pour le profil utilisateur
# Endpoint pour le profil utilisateur
@ns.route("/profile")
class Profile(Resource):
    @jwt_required()
    @ns.marshal_with(profile_model)
    def get(self):
        # Récupérer l'identité de l'utilisateur à partir du token JWT
        user_id = get_jwt_identity()
        user = User.query.get_or_404(int(user_id))  # Convertir en entier et gérer 404

        return {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin
        }, 200

    @jwt_required()
    @ns.expect(update_profile_model)
    def put(self):
        # Récupérer l'identité de l'utilisateur à partir du token JWT
        user_id = get_jwt_identity()
        user = User.query.get_or_404(int(user_id))

        # Récupérer les données de mise à jour
        data = ns.payload

        # Mettre à jour le nom d'utilisateur si fourni
        if "username" in data:
            new_username = data["username"]
            if new_username != user.username and User.query.filter_by(username=new_username).first():
                return {"message": "Ce nom d'utilisateur est déjà utilisé"}, 400
            user.username = new_username

        # Mettre à jour l'e-mail si fourni
        if "email" in data:
            new_email = data["email"]
            if new_email != user.email and User.query.filter_by(email=new_email).first():
                return {"message": "Cet e-mail est déjà utilisé"}, 400
            user.email = new_email

        # Enregistrer les modifications dans la base de données
        db.session.commit()

        return {"message": "Profil mis à jour avec succès", "username": user.username, "email": user.email}, 200

# Endpoint pour la réinitialisation du mot de passe
@ns.route("/reset-password")
class ResetPassword(Resource):
    @jwt_required()
    @ns.expect(reset_password_model)
    def post(self):
        # Récupérer l'identité de l'utilisateur à partir du token JWT
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return {"message": "Utilisateur non trouvé"}, 404

        # Récupérer les données de réinitialisation du mot de passe
        data = ns.payload

        # Vérifier que l'ancien mot de passe est correct
        if not user.check_password(data["old_password"]):
            return {"message": "Ancien mot de passe incorrect"}, 401

        # Mettre à jour le mot de passe
        user.set_password(data["new_password"])
        db.session.commit()

        return {"message": "Mot de passe réinitialisé avec succès"}, 200

# Endpoint pour demander une réinitialisation de mot de passe
@ns.route("/reset-password/request")
class ResetPasswordRequest(Resource):
    @ns.expect(reset_password_request_model)
    def post(self):
        data = ns.payload
        email = data["email"]

        # Vérifier si l'utilisateur existe
        user = User.query.filter_by(email=email).first()
        if not user:
            return {"message": "Aucun utilisateur trouvé avec cet e-mail"}, 404

        # Générer un token de réinitialisation
        reset_token = create_access_token(identity=str(user.id), expires_delta=False)

        # Envoyer un e-mail avec le lien de réinitialisation
        reset_link = f"http://127.0.0.1:5000/auth/reset-password/confirm?token={reset_token}"
        send_reset_email(email, reset_link)  # Fonction pour envoyer l'e-mail

        return {"message": "Un e-mail de réinitialisation a été envoyé"}, 200

# Endpoint pour confirmer la réinitialisation du mot de passe
@ns.route("/reset-password/confirm")
class ResetPasswordConfirm(Resource):
    @ns.expect(reset_password_email_model)
    def post(self):
        data = ns.payload
        token = data["token"]
        new_password = data["new_password"]

        try:
            # Vérifier et décoder le token
            user_id = decode_token(token)["sub"]
            user = User.query.get(int(user_id))

            if not user:
                return {"message": "Utilisateur non trouvé"}, 404

            # Mettre à jour le mot de passe
            user.set_password(new_password)
            db.session.commit()

            return {"message": "Mot de passe réinitialisé avec succès"}, 200
        except Exception as e:
            return {"message": "Token invalide ou expiré"}, 400

# Fonction pour envoyer un e-mail de réinitialisation
def send_reset_email(email, reset_link):
    msg = Message(
        subject="Réinitialisation de votre mot de passe",
        recipients=[email],
        body=f"Cliquez sur ce lien pour réinitialiser votre mot de passe : {reset_link}",
        html=f"<p>Cliquez sur ce lien pour réinitialiser votre mot de passe : <a href='{reset_link}'>{reset_link}</a></p>"
    )
    mail.send(msg)