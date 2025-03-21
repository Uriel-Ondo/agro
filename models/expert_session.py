from app import db
from datetime import datetime

class ExpertSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Expert assigné dès la réponse
    public_request_id = db.Column(db.Integer, db.ForeignKey('public_request.id'), nullable=True)  # Lien vers la demande initiale
    session_type = db.Column(db.String(50), nullable=False)  # "text", "audio", "image", "audio_call", "video_call"
    message = db.Column(db.Text, nullable=True)  # Contenu ou chemin du fichier
    status = db.Column(db.String(20), default="active")  # "active", "completed"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)