from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.live_comment import LiveComment
from models.user import User
from extensions import db, socketio
from datetime import datetime, timedelta
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ns = Namespace("live", description="Commentaires en direct TNT")

comment_model = ns.model("LiveComment", {
    "comment": fields.String(required=True)
})

@ns.route("/comment")
class LiveCommentResource(Resource):
    @jwt_required()
    @ns.expect(comment_model)
    def post(self):
        user_id = get_jwt_identity()
        data = ns.payload
        comment = LiveComment(user_id=user_id, comment=data["comment"])
        db.session.add(comment)
        db.session.commit()
        
        user = User.query.get(user_id)
        comment_data = {
            "username": user.username,
            "comment": comment.comment,
            "created_at": comment.created_at.isoformat()
        }
        logger.debug(f"Émission de new_comment : {comment_data}")
        socketio.emit("new_comment", comment_data, namespace="/live")  # Correction ici
        
        return {"message": "Commentaire ajouté"}, 201

@ns.route("/comments")
class LiveComments(Resource):
    def get(self):
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        comments = LiveComment.query.join(User).filter(LiveComment.created_at >= two_hours_ago).order_by(LiveComment.created_at.desc()).limit(50).all()
        return [
            {
                "username": comment.user.username,
                "comment": comment.comment,
                "created_at": comment.created_at.isoformat()
            } for comment in comments
        ], 200