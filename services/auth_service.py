from models.user import User
from extensions import db

def register_user(username, email, password, role):
    user = User(username=username, email=email, role=role)
    user.set_password(password)  # Hacher le mot de passe
    db.session.add(user)
    db.session.commit()
    print(f"Utilisateur inscrit : {user.username}, Mot de passe haché : {user.password_hash}")
    return user

def login_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user:
        print(f"Utilisateur trouvé : {user.username}")
        print(f"Mot de passe haché dans la base de données : {user.password_hash}")
        if user.check_password(password):
            print("Mot de passe correct")
            return user
        else:
            print("Mot de passe incorrect")
    else:
        print("Utilisateur non trouvé")
    return None