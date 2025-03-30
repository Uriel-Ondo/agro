from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.live_comment import LiveComment
from models.user import User
from extensions import db
from datetime import datetime, timedelta
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ns = Namespace("live", description="Commentaires en direct TNT")

HLS_STREAMS = {
    "tv5monde": "https://ott.tv5monde.com/Content/HLS/Live/channel(info)/index.m3u8",
    "france24": "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_5000.m3u8",
    "info6": "https://live-hls-web-aja.getaj.net/AJA/index.m3u8",
    "animesama": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
    "tvanime": "https://www.w3schools.com/html/mov_bbb.mp4"
}

comment_model = ns.model("LiveComment", {
    "comment": fields.String(required=True)
})

@ns.route("/stream/<channel>")
class LiveStreamResource(Resource):
    def get(self, channel):
        stream_url = HLS_STREAMS.get(channel.lower(), "")
        if not stream_url:
            logger.error(f"Chaîne non trouvée : {channel}")
            return {"error": "Chaîne non trouvée"}, 404
        logger.debug(f"Flux HLS récupéré pour la chaîne {channel} : {stream_url}")
        return {"stream_url": stream_url}, 200

@ns.route("/comment")
class LiveCommentResource(Resource):
    @jwt_required()
    @ns.expect(comment_model)
    def post(self):
        from app import socketio  # Importer socketio ici, pas au niveau du module
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
        socketio.emit("new_comment", comment_data, namespace="/live")
        
        return {"message": "Commentaire ajouté"}, 201

@ns.route("/comments")
class LiveComments(Resource):
    def get(self):
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        comments = LiveComment.query.join(User).filter(LiveComment.created_at >= two_hours_ago).order_by(LiveComment.created_at.asc()).limit(50).all()
        return [
            {
                "username": comment.user.username,
                "comment": comment.comment,
                "created_at": comment.created_at.isoformat()
            } for comment in comments
        ], 200