from models.user import User
from extensions import db
from flask import current_app
from flask_jwt_extended import create_access_token

def register_user(username, email, password, role):
    with current_app.app_context():
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Utilisateur inscrit : {user.username}, Mot de passe haché : {user.password_hash}")
        return user

def login_user(email, password):
    with current_app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            current_app.logger.debug(f"Utilisateur trouvé : {user.username}")
            current_app.logger.debug(f"Mot de passe haché dans la base de données : {user.password_hash}")
            if user.check_password(password):
                current_app.logger.info("Mot de passe correct")
                access_token = create_access_token(identity=user.id)
                return {"user": user, "access_token": access_token}
            else:
                current_app.logger.warning("Mot de passe incorrect")
        else:
            current_app.logger.warning("Utilisateur non trouvé")
        return None