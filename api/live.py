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

# Simulation des URL de flux HLS (remplacer par des URL réelles et légales)
HLS_STREAMS = {
    "euronews": "http://mafreebox.freebox.fr:8765/service/205/sd/master.m3u8",
    "france24": "https://static.france24.com/Live/F24_FR_HI_HLS/live_tv.m3u8",
    "m6": "https://www.youtube.com/embed/l8PMl7tUDIE?hl=fr&showinfo=0&color=white&rel=1&enablejsapi=1&origin=https%3A%2F%2Fwww.france24.com&autoplay=1&controls=1&modestbranding=0&disablekb=0&mute=0&embed_config=%7B%22primaryThemeColor%22%3A%22%23011d26%22%2C%22relatedChannels%22%3A%5B%22UCCCPCZNChQdGa9EkATeye4g%22%5D%2C%22autonavRelatedVideos%22%3Atrue%2C%22hideInfoBar%22%3Atrue%2C%22adsConfig%22%3A%7B%22disableAds%22%3Atrue%7D%2C%22enableIma%22%3Atrue%7D&widgetid=1&forigin=https%3A%2F%2Fwww.france24.com%2Ffr%2Fdirect&aoriginsup=1&gporigin=https%3A%2F%2Fwww.france24.com%2Ffr%2Fdirect&vf=1"
}

comment_model = ns.model("LiveComment", {
    "comment": fields.String(required=True)
})

@ns.route("/stream/<channel>")
class LiveStreamResource(Resource):
    def get(self, channel):
        """Récupérer l'URL du flux HLS pour une chaîne donnée."""
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