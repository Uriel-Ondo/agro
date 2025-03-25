#from app import db
from datetime import datetime
from extensions import db  

class PublicRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)  # "text", "audio", "image"
    content = db.Column(db.Text, nullable=False)  # Texte ou chemin du fichier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded = db.Column(db.Boolean, default=False)  # Marque si une réponse a été donnée