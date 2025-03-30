from extensions import db
from datetime import datetime

class PublicRequest(db.Model):
    __tablename__ = 'public_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    responded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)