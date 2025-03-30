from extensions import db
from datetime import datetime

class LiveComment(db.Model):
    __tablename__ = 'live_comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LiveComment {self.id}, User: {self.user_id}, Comment: {self.comment[:20]}>"