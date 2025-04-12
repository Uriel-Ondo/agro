from extensions import db
from datetime import datetime

class LiveSession(db.Model):
    __tablename__ = 'live_sessions'  # Ajout explicite du nom de la table
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Corrigé de 'user.id' à 'users.id'
    stream_url = db.Column(db.String(255), nullable=False)
    stream_type = db.Column(db.String(10), default='hls')  # hls ou srs
    title = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, ended
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)  # Ajout de nullable=True pour clarté
    expert = db.relationship('User', backref='live_sessions')

    def __repr__(self):
        return f'<LiveSession {self.title} - {self.status}>'