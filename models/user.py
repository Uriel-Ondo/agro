# models/user.py
from extensions import db  # Changé de "from app import db" à "from extensions import db"
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(db.Model):
    __tablename__ = 'user'  # Défini explicitement comme 'user' au lieu de 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum("farmer", "expert"), nullable=False, default="farmer")
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)  # Statut en ligne
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Dernière activité
    created_at = db.Column(db.DateTime, default=db.func.now())
    favorite_cities = db.Column(db.Text, default='[]')  # Nouveau champ pour les villes favorites

    # Relations
    plant_diseases = db.relationship("PlantDisease", backref="user", lazy=True)
    chat_messages = db.relationship("ChatMessage", backref="user", lazy=True)
    live_comments = db.relationship("LiveComment", backref="user", lazy=True)
    expert_sessions_as_user = db.relationship("ExpertSession", foreign_keys="ExpertSession.user_id", backref="user", lazy=True)
    expert_sessions_as_expert = db.relationship("ExpertSession", foreign_keys="ExpertSession.expert_id", backref="expert", lazy=True)
    public_requests = db.relationship("PublicRequest", backref="user", lazy=True)

    def set_password(self, password):
        """
        Hache le mot de passe et le stocke dans password_hash.
        """
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """
        Vérifie si le mot de passe fourni correspond au mot de passe haché.
        """
        return check_password_hash(self.password_hash, password)

    def set_online(self, status):
        """
        Met à jour le statut en ligne de l'utilisateur.
        """
        self.is_online = status
        self.last_active = datetime.utcnow()
        db.session.commit()

    def get_favorite_cities(self):
        """
        Retourne la liste des villes favorites sous forme de liste Python.
        """
        return json.loads(self.favorite_cities)

    def set_favorite_cities(self, cities):
        """
        Définit la liste des villes favorites et la sauvegarde sous forme JSON.
        """
        self.favorite_cities = json.dumps(cities)
        db.session.commit()

    def add_favorite_city(self, city):
        """
        Ajoute une ville aux favoris si elle n'est pas déjà présente.
        """
        cities = self.get_favorite_cities()
        if city not in cities:
            cities.append(city)
            self.set_favorite_cities(cities)
            return True
        return False

    def remove_favorite_city(self, city):
        """
        Supprime une ville des favoris si elle est présente.
        """
        cities = self.get_favorite_cities()
        if city in cities:
            cities.remove(city)
            self.set_favorite_cities(cities)
            return True
        return False

    def __repr__(self):
        """
        Représentation de l'objet User pour le débogage.
        """
        return f"<User {self.username}, Email: {self.email}, Role: {self.role}, Online: {self.is_online}>"