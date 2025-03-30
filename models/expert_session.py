from extensions import db
from datetime import datetime

class ExpertSession(db.Model):
    __tablename__ = 'expert_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    public_request_id = db.Column(db.Integer, db.ForeignKey('public_requests.id'), nullable=True)
    status = db.Column(db.String(20), default='active')  # 'active' ou 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('SessionMessage', backref='session', lazy=True, cascade="all, delete-orphan")

class SessionMessage(db.Model):
    __tablename__ = 'session_messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('expert_sessions.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10), default='sent')  # Ajout de la colonne status