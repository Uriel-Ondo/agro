from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request, send_from_directory
from extensions import db
from models.user import User
from models.public_request import PublicRequest
from models.expert_session import ExpertSession, SessionMessage
import os
from datetime import datetime
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ns = Namespace("expert", description="Communication avec experts")

public_request_model = ns.model("PublicRequest", {
    "request_type": fields.String(required=True, enum=["text", "audio", "image", "video"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
})

message_model = ns.model("Message", {
    "message_type": fields.String(required=True, enum=["text", "audio", "image", "video", "audio_call", "video_call", "audio_call_signal", "video_call_signal"]),
    "content": fields.String(description="Texte ou chemin fichier"),
    "status": fields.String(enum=["sent", "received", "read"], default="sent")  # Ajout de status
})

file_parser = ns.parser()
file_parser.add_argument('file', type='file', location='files', required=False)

@ns.route("/public_request")
class PublicRequestResource(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self):
        """Créer une nouvelle demande publique"""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != "farmer":
            logger.error(f"Accès refusé - user_id: {user_id}, role: {user.role if user else 'inconnu'}")
            return {"message": "Seuls les fermiers peuvent créer des demandes."}, 403

        file = request.files.get("file")
        content = request.form.get("content")
        request_type = request.form.get("request_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                logger.error(f"Format non supporté: {ext}")
                return {"message": "Format non supporté."}, 400
            file_path = f"uploads/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = f"http://127.0.0.1:5000/uploads/{os.path.basename(file_path)}"
            request_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif not content:
            logger.error("Contenu ou fichier requis manquant")
            return {"message": "Contenu ou fichier requis."}, 400

        try:
            request_obj = PublicRequest(user_id=user_id, request_type=request_type, content=content)
            db.session.add(request_obj)
            db.session.commit()
            logger.debug(f"Demande publique créée - request_id: {request_obj.id}")
            from services.expert_service import notify_all_experts
            notify_all_experts(request_obj)
            return {"request_id": request_obj.id}, 201
        except Exception as e:
            logger.error(f"Erreur lors de la création de la demande publique: {e}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

    @jwt_required()
    def get(self):
        """Récupérer les demandes publiques"""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            logger.error(f"Utilisateur non trouvé - user_id: {user_id}")
            return {"message": "Utilisateur non trouvé."}, 404

        try:
            requests = PublicRequest.query.filter_by(user_id=user_id).all() if user.role == "farmer" else PublicRequest.query.filter_by(responded=False).all()
            logger.debug(f"Requêtes récupérées - user_id: {user_id}, nombre: {len(requests)}")
            return [{
                "request_id": req.id,
                "username": User.query.get(req.user_id).username,
                "request_type": req.request_type,
                "content": req.content,
                "created_at": req.created_at.isoformat(),
                "responded": req.responded
            } for req in requests], 200
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des demandes: {e}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/public_request/<int:request_id>/respond")
class RespondRequest(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, request_id):
        """Répondre à une demande publique et démarrer une session privée"""
        expert_id = int(get_jwt_identity())
        expert = User.query.get(expert_id)
        if not expert or expert.role != "expert":
            logger.error(f"Accès refusé - expert_id: {expert_id}, role: {expert.role if expert else 'inconnu'}")
            return {"message": "Vous devez être un expert."}, 403

        public_request = PublicRequest.query.get(request_id)
        if not public_request or public_request.responded:
            logger.error(f"Demande invalide - request_id: {request_id}, responded: {public_request.responded if public_request else 'introuvable'}")
            return {"message": "Demande introuvable ou déjà répondue."}, 404

        file = request.files.get("file")
        content = request.form.get("content", "Conversation démarrée")
        message_type = request.form.get("message_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            file_path = f"uploads/{expert_id}_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = f"http://127.0.0.1:5000/uploads/{os.path.basename(file_path)}"
            message_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"

        try:
            session = ExpertSession(user_id=public_request.user_id, expert_id=expert_id, public_request_id=request_id, status="active")
            db.session.add(session)
            db.session.flush()

            logger.debug(f"Session créée - id: {session.id}, user_id: {session.user_id}, expert_id: {session.expert_id}, status: {session.status}")

            message = SessionMessage(session_id=session.id, sender_id=expert_id, message_type=message_type, content=content, status="sent")
            db.session.add(message)
            public_request.responded = True
            db.session.commit()

            from services.expert_service import respond_to_request
            respond_to_request(request_id, expert_id, content, message_type)

            farmer = User.query.get(public_request.user_id)
            logger.debug(f"Réponse réussie - farmer: {farmer.username}, expert: {expert.username}")
            return {"farmer_username": farmer.username, "expert_username": expert.username}, 201
        except Exception as e:
            logger.error(f"Erreur lors de la réponse à la demande {request_id}: {e}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>/message")
class SendPrivateMessage(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, farmer_username, expert_username):
        """Envoyer un message dans une session privée"""
        sender_id = int(get_jwt_identity())
        logger.debug(f"POST /session/{farmer_username}/{expert_username}/message - sender_id: {sender_id}")

        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id, status="active").first()
        if not session:
            session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).order_by(ExpertSession.created_at.desc()).first()
            if not session:
                logger.error(f"Aucune session trouvée pour farmer_id: {farmer.id}, expert_id: {expert.id}")
                return {"message": "Aucune session trouvée."}, 404
            logger.warning(f"Session non active sélectionnée - id: {session.id}, status: {session.status}")

        logger.debug(f"Session trouvée: id={session.id}, user_id={session.user_id}, expert_id={session.expert_id}, status={session.status}")

        if session.status == "completed" and sender_id == farmer.id:
            logger.warning(f"Tentative d'envoi dans une session terminée par farmer_id: {farmer.id}")
            return {"message": "Cette session est terminée, vous ne pouvez plus envoyer de messages."}, 403

        if sender_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - sender_id: {sender_id} n'est ni user_id: {session.user_id} ni expert_id: {session.expert_id}")
            return {"message": "Accès refusé : vous n’êtes pas autorisé à envoyer dans cette session."}, 403

        file = request.files.get("file")
        content = request.form.get("content")
        message_type = request.form.get("message_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                logger.error(f"Format non supporté: {ext}")
                return {"message": "Format non supporté."}, 400
            file_path = f"uploads/{sender_id}_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = f"http://127.0.0.1:5000/uploads/{os.path.basename(file_path)}"
            message_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif not content and message_type not in ["audio_call", "video_call", "audio_call_signal", "video_call_signal"]:
            logger.error("Contenu requis manquant")
            return {"message": "Contenu requis."}, 400

        try:
            message = SessionMessage(session_id=session.id, sender_id=sender_id, message_type=message_type, content=content, status="sent")
            db.session.add(message)
            db.session.commit()
            logger.debug(f"Message envoyé - message_id: {message.id}, type: {message_type}, content: {content}")

            from services.expert_service import send_private_message as notify_private_message
            notify_private_message(session.id, sender_id, message_type, content)

            return {"message_id": message.id}, 201
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message dans la session {session.id}: {e}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>/messages")
class GetSessionMessages(Resource):
    @jwt_required()
    def get(self, farmer_username, expert_username):
        """Récupérer les messages d'une session"""
        user_id = int(get_jwt_identity())
        logger.debug(f"GET /session/{farmer_username}/{expert_username}/messages - user_id: {user_id}")

        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id, status="active").first()
        if not session:
            session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).order_by(ExpertSession.created_at.desc()).first()
            if not session:
                logger.error(f"Aucune session trouvée pour farmer_id: {farmer.id}, expert_id: {expert.id}")
                return {"message": "Aucune session trouvée."}, 404
            logger.warning(f"Session non active sélectionnée - id: {session.id}, status: {session.status}")

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id} n'est ni farmer_id: {session.user_id} ni expert_id: {session.expert_id}")
            return {"message": "Accès refusé : vous n’êtes pas autorisé à voir ces messages."}, 403

        try:
            messages = SessionMessage.query.filter_by(session_id=session.id).order_by(SessionMessage.created_at.asc()).all()
            # Marquer les messages comme "read" si l'utilisateur les consulte
            for msg in messages:
                if msg.sender_id != user_id and msg.status != "read":
                    msg.status = "read"
            db.session.commit()

            logger.debug(f"Messages récupérés - session_id: {session.id}, nombre: {len(messages)}")
            return [{
                "id": msg.id,
                "session_id": msg.session_id,
                "sender_username": User.query.get(msg.sender_id).username,
                "message_type": msg.message_type,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "status": msg.status  # Ajout de status dans la réponse
            } for msg in messages], 200
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des messages: {e}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/sessions")
class UserSessions(Resource):
    @jwt_required()
    def get(self):
        """Récupérer toutes les sessions de l'utilisateur connecté"""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            logger.error(f"Utilisateur non trouvé - user_id: {user_id}")
            return {"message": "Utilisateur non trouvé."}, 404

        try:
            sessions = ExpertSession.query.filter_by(user_id=user_id).all() if user.role == "farmer" else ExpertSession.query.filter_by(expert_id=user_id).all()
            logger.debug(f"Sessions récupérées - user_id: {user_id}, nombre: {len(sessions)}")
            return [{
                "session_id": s.id,
                "farmer_username": User.query.get(s.user_id).username,
                "expert_username": User.query.get(s.expert_id).username,
                "request_id": s.public_request_id,
                "last_message": s.messages[-1].content if s.messages else None,
                "created_at": s.created_at.isoformat()
            } for s in sessions], 200
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des sessions: {e}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>")
class DeleteSession(Resource):
    @jwt_required()
    def delete(self, farmer_username, expert_username):
        """Supprimer une session"""
        user_id = int(get_jwt_identity())
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).order_by(ExpertSession.created_at.desc()).first()
        if not session:
            logger.error(f"Aucune session trouvée pour farmer_id: {farmer.id}, expert_id: {expert.id}")
            return {"message": "Session introuvable."}, 404

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id} n'est ni farmer_id: {session.user_id} ni expert_id: {session.expert_id}")
            return {"message": "Accès refusé : vous n’êtes pas autorisé à supprimer cette session."}, 403

        try:
            db.session.delete(session)
            db.session.commit()
            logger.debug(f"Session {session.id} supprimée par user_id: {user_id}")

            from services.expert_service import notify_session_deleted
            notify_session_deleted(session.id, farmer.id, expert.id, user_id)

            return {"message": "Session supprimée avec succès."}, 200
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la session: {e}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/uploads/<path:filename>")
class ServeUploads(Resource):
    def get(self, filename):
        """Servir les fichiers uploadés"""
        try:
            return send_from_directory("uploads", filename)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du fichier {filename}: {e}")
            return {"message": "Fichier non trouvé."}, 404

@ns.route("/session/<string:farmer_username>/<string:expert_username>/end")
class EndSession(Resource):
    @jwt_required()
    def post(self, farmer_username, expert_username):
        """Terminer une session"""
        expert_id = int(get_jwt_identity())
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        if expert.id != expert_id:
            logger.error(f"Seul l'expert peut terminer - expert_id: {expert_id}, tenté par: {expert_id}")
            return {"message": "Seul l'expert peut terminer la session."}, 403

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).first()
        if not session:
            logger.error(f"Session introuvable pour farmer_id: {farmer.id}, expert_id: {expert.id}")
            return {"message": "Session introuvable."}, 404

        if session.status == "completed":
            logger.warning(f"Session déjà terminée - session_id: {session.id}")
            return {"message": "Cette session est déjà terminée."}, 400

        try:
            session.status = "completed"
            end_message = SessionMessage(
                session_id=session.id,
                sender_id=expert_id,
                message_type="session_ended",
                content="La session a été terminée par l'expert.",
                status="sent"  # Statut initial
            )
            db.session.add(end_message)
            db.session.commit()
            logger.debug(f"Session terminée - session_id: {session.id}")

            from services.expert_service import send_session_ended
            send_session_ended(session.id, expert_id, farmer.id)

            return {"message": "Session terminée avec succès."}, 200
        except Exception as e:
            logger.error(f"Erreur lors de la fin de la session {session.id}: {e}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500