from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from extensions import db

ns = Namespace("admin", description="Gestion des utilisateurs (admin)")

user_model = ns.model("User", {
    "username": fields.String(required=True, description="Nom d'utilisateur"),
    "email": fields.String(required=True, description="Adresse email"),
    "password": fields.String(required=False, description="Mot de passe initial (optionnel)"),
    "role": fields.String(required=True, description="Rôle de l'utilisateur (admin, expert, farmer)", enum=["admin", "expert", "farmer"]),
    "is_admin": fields.Boolean(default=False, description="Statut administrateur")
})

def admin_required():
    def decorator(fn):
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                return {"message": "Accès réservé aux administrateurs"}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@ns.route("/users")
class AdminUsers(Resource):
    @admin_required()
    def get(self):
        users = User.query.all()
        return [{"id": u.id, "username": u.username, "email": u.email, "role": u.role, "is_admin": u.is_admin} for u in users], 200

    @admin_required()
    @ns.expect(user_model)
    def post(self):
        data = ns.payload
        if User.query.filter_by(email=data["email"]).first():
            return {"message": "Email déjà utilisé"}, 400
        # Vérifier que le rôle est valide
        valid_roles = ["admin", "expert", "farmer"]
        if data["role"] not in valid_roles:
            return {"message": "Rôle invalide. Utilisez 'admin', 'expert' ou 'farmer'."}, 400
        user = User(
            username=data["username"],
            email=data["email"],
            role=data["role"],
            is_admin=data["is_admin"]
        )
        password = data.get("password", "default_password")  # Mot de passe optionnel
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return {"message": "Utilisateur créé"}, 201

@ns.route("/users/<int:user_id>")
class AdminUser(Resource):
    @admin_required()
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        return {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "is_admin": user.is_admin}, 200

    @admin_required()
    @ns.expect(user_model)
    def put(self, user_id):
        user = User.query.get_or_404(user_id)
        data = ns.payload
        valid_roles = ["admin", "expert", "farmer"]
        if data["role"] not in valid_roles:
            return {"message": "Rôle invalide. Utilisez 'admin', 'expert' ou 'farmer'."}, 400
        user.username = data["username"]
        user.email = data["email"]
        user.role = data["role"]
        user.is_admin = data["is_admin"]
        db.session.commit()
        return {"message": "Utilisateur mis à jour"}, 200

    @admin_required()
    def delete(self, user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "Utilisateur supprimé"}, 200