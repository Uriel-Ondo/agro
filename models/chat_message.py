from extensions import db
import uuid

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)  # Changé de "user.id" à "users.id"
    conversation_id = db.Column(db.String(36), nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<ChatMessage user_id={self.user_id} conversation_id={self.conversation_id}>"