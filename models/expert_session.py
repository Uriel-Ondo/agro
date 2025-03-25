#from app import db
from extensions import db  
from datetime import datetime

class ExpertSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Fermier
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Expert
    public_request_id = db.Column(db.Integer, db.ForeignKey('public_request.id'), nullable=True)  # Lien vers la demande initiale
    status = db.Column(db.String(20), default="active")  # "active", "completed"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('SessionMessage', backref='session', lazy=True, cascade="all, delete-orphan")  # Relation avec les messages

class SessionMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('expert_session.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Qui a envoyé (fermier ou expert)
    message_type = db.Column(db.String(50), nullable=False)  # "text", "audio", "image", "audio_call", "video_call"
    content = db.Column(db.Text, nullable=True)  # Contenu ou chemin du fichier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)