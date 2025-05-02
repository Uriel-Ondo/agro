from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.expert_service import create_public_request, respond_to_request, send_private_message
from models.user import User
from flask import request
import os
from datetime import datetime
<<<<<<< Updated upstream
=======
import logging
import traceback

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
>>>>>>> Stashed changes

ns = Namespace("expert", description="Communication avec experts")

# Modèle pour une demande publique
public_request_model = ns.model("PublicRequest", {
    "request_type": fields.String(required=True, enum=["text", "audio", "image"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
})

<<<<<<< Updated upstream
# Modèle pour une réponse
response_model = ns.model("Response", {
    "response_type": fields.String(required=True, enum=["text", "audio", "image"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
=======
call_status_model = ns.model('CallStatus', {
    'call_id': fields.Integer(required=True, description='ID de l’appel'),
    'status': fields.String(required=True, enum=['ongoing', 'received', 'missed', 'ended'], description='Statut de l’appel')
})

message_model = ns.model("Message", {
    "message_type": fields.String(required=True, enum=["text", "audio", "image", "video", "audio_call", "video_call", "audio_call_signal", "video_call_signal", "session_ended"]),
    "content": fields.String(description="Texte ou chemin fichier"),
    "status": fields.String(enum=["sent", "received", "read", "pending"], default="sent"),
    "request_id": fields.Integer(description="ID de la demande publique associée", required=False)
>>>>>>> Stashed changes
})

# Parser pour les fichiers
file_parser = ns.parser()
<<<<<<< Updated upstream
file_parser.add_argument('file', type='file', location='files', required=False, help="Fichier audio ou image")
=======
file_parser.add_argument('file', type='file', location='files', required=False)
file_parser.add_argument('request_id', type=int, location='form', required=False)
>>>>>>> Stashed changes

@ns.route("/public_request")
class PublicRequestResource(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self):
        """
        Crée une demande publique visible par tous les experts.
        """
        user_id = get_jwt_identity()
        file = request.files.get("file")
        content = request.form.get("content")
        request_type = request.form.get("request_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                return {"message": "Format de fichier non supporté."}, 400
            file_path = f"uploads/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
<<<<<<< Updated upstream
            file.save(file_path)
            content = file_path
            request_type = "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
=======
            try:
                file.save(file_path)
            except Exception as e:
                logger.error(f"Erreur sauvegarde fichier: {e}")
                return {"message": "Erreur lors de la sauvegarde du fichier."}, 500
            content = f"{request.url_root.rstrip('/')}/uploads/{os.path.basename(file_path)}"
            if ext in {'.jpg', '.jpeg', '.png'}:
                request_type = "image"
            elif ext == '.mp4':
                request_type = "video"
            else:
                request_type = "audio"
            logger.debug(f"Fichier uploadé - chemin: {file_path}, type: {request_type}")
>>>>>>> Stashed changes
        elif not content:
            return {"message": "Contenu ou fichier requis."}, 400

<<<<<<< Updated upstream
        request_obj = create_public_request(user_id, request_type, content)
        return {"request_id": request_obj.id}, 201
=======
        try:
            request_obj = PublicRequest(user_id=user_id, request_type=request_type, content=content)
            db.session.add(request_obj)
            db.session.commit()
            logger.debug(f"Demande publique créée - request_id: {request_obj.id}")
            notify_all_experts(request_obj)
            return {"request_id": request_obj.id}, 201
        except Exception as e:
            logger.error(f"Erreur création demande publique: {e}\n{traceback.format_exc()}")
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
            requests = PublicRequest.query.all()
            logger.debug(f"Requêtes récupérées - user_id: {user_id}, nombre: {len(requests)}")
            return [{
                "request_id": req.id,
                "username": User.query.get(req.user_id).username,
                "request_type": req.request_type,
                "content": req.content,
                "created_at": req.created_at.isoformat(),
                "responded": req.responded,
                "responded_by": User.query.get(ExpertSession.query.filter_by(public_request_id=req.id).first().expert_id).username if req.responded and ExpertSession.query.filter_by(public_request_id=req.id).first() else None
            } for req in requests], 200
        except Exception as e:
            logger.error(f"Erreur récupération demandes: {e}\n{traceback.format_exc()}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500
>>>>>>> Stashed changes

@ns.route("/public_request/<int:request_id>/respond")
class RespondRequest(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, request_id):
        """
        Répond à une demande publique et crée une session privée.
        """
        expert_id = get_jwt_identity()
        expert = User.query.get(expert_id)
        if not expert or expert.role != "expert":
<<<<<<< Updated upstream
            return {"message": "Vous devez être un expert pour répondre."}, 403
=======
            logger.error(f"Accès refusé - expert_id: {expert_id}, role: {expert.role if expert else 'inconnu'}")
            return {"message": "Vous devez être un expert."}, 403

        public_request = PublicRequest.query.get(request_id)
        if not public_request:
            logger.error(f"Demande introuvable - request_id: {request_id}")
            return {"message": "Demande introuvable."}, 404
        if public_request.responded:
            logger.error(f"Demande déjà répondue - request_id: {request_id}")
            return {"message": "Demande déjà répondue."}, 400
>>>>>>> Stashed changes

        file = request.files.get("file")
        content = request.form.get("content")
        response_type = request.form.get("response_type", "text")

        file_path = None
        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                return {"message": "Format de fichier non supporté."}, 400
            file_path = f"uploads/{expert_id}_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
<<<<<<< Updated upstream
            file.save(file_path)
            content = file_path
            response_type = "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"

        result = respond_to_request(request_id, expert_id, content, response_type)
        if isinstance(result, dict):  # Erreur
            return result, 400
        return {"session_id": result.id}, 201

@ns.route("/session/<int:session_id>/message")
class SendPrivateMessage(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, session_id):
        """
        Envoie un message privé dans une session active.
        """
        sender_id = get_jwt_identity()
=======
            try:
                file.save(file_path)
                if not os.path.exists(file_path):
                    logger.error(f"Fichier non sauvegardé: {file_path}")
                    return {"message": "Erreur lors de la sauvegarde du fichier."}, 500
            except Exception as e:
                logger.error(f"Erreur sauvegarde fichier: {e}\n{traceback.format_exc()}")
                return {"message": "Erreur lors de la sauvegarde du fichier."}, 500
            content = f"{request.url_root.rstrip('/')}/uploads/{os.path.basename(file_path)}"
            if ext in {'.jpg', '.jpeg', '.png'}:
                message_type = "image"
            elif ext == '.mp4':
                message_type = "video"
            else:
                message_type = "audio"
            logger.debug(f"Fichier uploadé - chemin: {file_path}, type: {message_type}")

        try:
            existing_session = ExpertSession.query.filter_by(
                user_id=public_request.user_id,
                expert_id=expert_id,
                public_request_id=request_id
            ).first()
            if existing_session:
                logger.warning(f"Session existante trouvée - session_id: {existing_session.id}")
                return {"message": "Une session existe déjà pour cette demande."}, 400

            session = ExpertSession(
                user_id=public_request.user_id,
                expert_id=expert_id,
                public_request_id=request_id,
                status="active",
                created_at=datetime.utcnow()
            )
            db.session.add(session)
            db.session.flush()

            message = SessionMessage(
                session_id=session.id,
                sender_id=expert_id,
                message_type=message_type,
                content=content,
                status="sent",
                created_at=datetime.utcnow()
            )
            db.session.add(message)

            public_request.responded = True
            db.session.commit()

            try:
                respond_to_request(request_id, expert_id, content, message_type)
            except Exception as e:
                logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")
                pass

            farmer = User.query.get(public_request.user_id)
            logger.debug(f"Réponse réussie - farmer: {farmer.username}, expert: {expert.username}, session_id: {session.id}")
            return {
                "farmer_username": farmer.username,
                "expert_username": expert.username,
                "session_id": session.id,
                "request_id": request_id
            }, 201

        except Exception as e:
            logger.error(f"Erreur réponse demande {request_id}: {e}\n{traceback.format_exc()}")
            db.session.rollback()
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Fichier supprimé: {file_path}")
                except Exception as e:
                    logger.error(f"Erreur suppression fichier {file_path}: {e}")
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

        request_id = request.form.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.error(f"Aucune session trouvée pour farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return {"message": "Aucune session trouvée."}, 404

        if session.status == "completed":
            logger.warning(f"Tentative envoi session terminée - session_id: {session.id}")
            return {"message": "Session terminée, envoi impossible."}, 403

        if sender_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - sender_id: {sender_id}")
            return {"message": "Accès refusé à cette session."}, 403

>>>>>>> Stashed changes
        file = request.files.get("file")
        content = request.form.get("content")
        message_type = request.form.get("message_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
<<<<<<< Updated upstream
                return {"message": "Format de fichier non supporté."}, 400
            file_path = f"uploads/{sender_id}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = file_path
            message_type = "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif message_type in ["audio_call", "video_call"]:
            content = None
        elif not content:
            return {"message": "Contenu requis pour ce type de message."}, 400

        result = send_private_message(session_id, sender_id, message_type, content)
        return result, 200
=======
                logger.error(f"Format non supporté: {ext}")
                return {"message": "Format non supporté."}, 400
            file_path = f"uploads/{sender_id}_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            try:
                file.save(file_path)
                if not os.path.exists(file_path):
                    logger.error(f"Fichier non sauvegardé: {file_path}")
                    return {"message": "Erreur lors de la sauvegarde du fichier."}, 500
            except Exception as e:
                logger.error(f"Erreur sauvegarde fichier: {e}\n{traceback.format_exc()}")
                return {"message": "Erreur lors de la sauvegarde du fichier."}, 500
            content = f"{request.url_root.rstrip('/')}/uploads/{os.path.basename(file_path)}"
            if ext in {'.jpg', '.jpeg', '.png'}:
                message_type = "image"
            elif ext == '.mp4':
                message_type = "video"
            else:
                message_type = "audio"
            logger.debug(f"Fichier uploadé - chemin: {file_path}, type: {message_type}")

        elif not content and message_type not in ["audio_call", "video_call", "audio_call_signal", "video_call_signal"]:
            logger.error("Contenu requis manquant")
            return {"message": "Contenu requis."}, 400

        try:
            message = SessionMessage(
                session_id=session.id,
                sender_id=sender_id,
                message_type=message_type,
                content=content,
                status="sent",
                created_at=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            logger.debug(f"Message envoyé - message_id: {message.id}, type: {message_type}")

            try:
                send_private_message(session.id, sender_id, message_type, content)
            except Exception as e:
                logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")
                pass

            return {"message_id": message.id, "content": content, "session_id": session.id}, 201
        except Exception as e:
            logger.error(f"Erreur envoi message session {session.id}: {e}\n{traceback.format_exc()}")
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

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.error(f"Aucune session trouvée - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return {"message": "Aucune session trouvée."}, 404

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id}")
            return {"message": "Accès refusé à ces messages."}, 403

        try:
            messages = SessionMessage.query.filter_by(session_id=session.id).order_by(SessionMessage.created_at.asc()).all()
            for msg in messages:
                if msg.sender_id != user_id and msg.status != "read":
                    msg.status = "read"
                    try:
                        socketio.emit('message_status_update', {
                            'message_id': msg.id,
                            'status': 'read'
                        }, room=f"session_{session.id}", namespace='/expert')
                    except Exception as e:
                        logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")
            db.session.commit()

            logger.debug(f"Messages récupérés - session_id: {session.id}, nombre: {len(messages)}")
            return [{
                "id": msg.id,
                "session_id": msg.session_id,
                "sender_username": User.query.get(msg.sender_id).username,
                "message_type": msg.message_type,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "status": msg.status
            } for msg in messages], 200
        except Exception as e:
            logger.error(f"Erreur récupération messages: {e}\n{traceback.format_exc()}")
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
                "created_at": s.created_at.isoformat(),
                "status": s.status
            } for s in sessions], 200
        except Exception as e:
            logger.error(f"Erreur récupération sessions: {e}\n{traceback.format_exc()}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>")
class SessionResource(Resource):
    @jwt_required()
    def get(self, farmer_username, expert_username):
        """Récupérer une session spécifique"""
        user_id = int(get_jwt_identity())
        logger.debug(f"GET /session/{farmer_username}/{expert_username} - user_id: {user_id}")

        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.debug(f"Aucune session trouvée - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return [], 200

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id}, session_id: {session.id}")
            return {"message": "Accès refusé à cette session."}, 403

        try:
            logger.debug(f"Session récupérée - session_id: {session.id}")
            return {
                "session_id": session.id,
                "farmer_username": farmer.username,
                "expert_username": expert.username,
                "request_id": session.public_request_id,
                "status": session.status,
                "created_at": session.created_at.isoformat()
            }, 200
        except Exception as e:
            logger.error(f"Erreur récupération session: {e}\n{traceback.format_exc()}")
            return {"message": "Erreur serveur."}, 500

    @jwt_required()
    def delete(self, farmer_username, expert_username):
        """Supprimer une session"""
        user_id = int(get_jwt_identity())
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.error(f"Aucune session trouvée - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return {"message": "Session introuvable."}, 404

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id}")
            return {"message": "Accès refusé à cette session."}, 403

        try:
            from services.expert_service import notify_session_deleted
            notify_session_deleted(session.id, session.user_id, session.expert_id, user_id)
            db.session.delete(session)
            db.session.commit()
            logger.debug(f"Session {session.id} supprimée par user_id: {user_id}")
            return {"message": "Session supprimée."}, 200
        except Exception as e:
            logger.error(f"Erreur suppression session: {e}\n{traceback.format_exc()}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/uploads/<path:filename>")
class ServeUploads(Resource):
    def get(self, filename):
        """Servir les fichiers uploadés"""
        try:
            file_path = os.path.join("uploads", filename)
            if not os.path.exists(file_path):
                logger.error(f"Fichier non trouvé: {file_path}")
                return {"message": "Fichier non trouvé."}, 404

            ext = os.path.splitext(filename)[1].lower()
            content_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.mp4': 'video/mp4',
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.webm': 'audio/webm'
            }.get(ext, 'application/octet-stream')

            logger.debug(f"Servir fichier: {file_path}, Content-Type: {content_type}")
            response = send_from_directory("uploads", filename)
            response.headers['Content-Type'] = content_type
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Erreur récupération fichier {filename}: {e}\n{traceback.format_exc()}")
            return {"message": "Erreur serveur."}, 500

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
            logger.error(f"Seul l'expert peut terminer - expert_id: {expert_id}")
            return {"message": "Seul l'expert peut terminer la session."}, 403

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.error(f"Session introuvable - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return {"message": "Session introuvable."}, 404

        if session.status == "completed":
            logger.warning(f"Session déjà terminée - session_id: {session.id}")
            return {"message": "Session déjà terminée."}, 400

        try:
            session.status = "completed"
            end_message = SessionMessage(
                session_id=session.id,
                sender_id=expert_id,
                message_type="session_ended",
                content="La session a été terminée par l'expert.",
                status="sent",
                created_at=datetime.utcnow()
            )
            db.session.add(end_message)
            db.session.commit()
            logger.debug(f"Session terminée - session_id: {session.id}")

            try:
                send_session_ended(session.id, expert_id, farmer.id)
            except Exception as e:
                logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")
                pass

            return {"message": "Session terminée."}, 200
        except Exception as e:
            logger.error(f"Erreur fin session {session.id}: {e}\n{traceback.format_exc()}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>/call_status")
class UpdateCallStatus(Resource):
    @jwt_required()
    @ns.expect(call_status_model)
    def post(self, farmer_username, expert_username):
        """Mettre à jour le statut d'un appel"""
        sender_id = int(get_jwt_identity())
        data = request.get_json()
        call_id = data.get("call_id")
        status = data.get("status")
        logger.debug(f"call_status - call_id: {call_id}, status: {status}, sender_id: {sender_id}")

        if not call_id or not status:
            logger.error(f"Données manquantes - call_id: {call_id}, status: {status}")
            return {"message": "call_id et status requis."}, 400

        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.error(f"Session introuvable - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return {"message": "Session introuvable."}, 404

        if sender_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - sender_id: {sender_id}")
            return {"message": "Accès refusé."}, 403

        try:
            message = SessionMessage(
                session_id=session.id,
                sender_id=sender_id,
                message_type="call_status",
                content=f"Call {call_id} updated to {status}",
                status="sent",
                created_at=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            try:
                socketio.emit('call_status_update', {
                    "session_id": session.id,
                    "call_id": call_id,
                    "status": status
                }, room=f"session_{session.id}", namespace='/expert')
            except Exception as e:
                logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")
            logger.debug(f"Statut appel mis à jour - call_id: {call_id}, status: {status}")
            return {"message": "Statut appel mis à jour."}, 200
        except Exception as e:
            logger.error(f"Erreur mise à jour statut appel: {e}\n{traceback.format_exc()}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/session/<string:farmer_username>/<string:expert_username>/call_logs")
class GetCallLogs(Resource):
    @jwt_required()
    def get(self, farmer_username, expert_username):
        """Récupérer les journaux d'appels d'une session"""
        user_id = int(get_jwt_identity())
        logger.debug(f"GET /session/{farmer_username}/{expert_username}/call_logs - user_id: {user_id}")

        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            logger.error(f"Utilisateur non trouvé - farmer: {farmer_username}, expert: {expert_username}")
            return {"message": "Utilisateur non trouvé."}, 404

        request_id = request.args.get('request_id', type=int)
        query = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id)
        if request_id:
            query = query.filter_by(public_request_id=request_id)
        session = query.order_by(ExpertSession.created_at.desc()).first()

        if not session:
            logger.debug(f"Aucune session trouvée - farmer_id: {farmer.id}, expert_id: {expert.id}, request_id: {request_id}")
            return [], 200

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id}")
            return {"message": "Accès refusé à cette session."}, 403

        try:
            call_logs = SessionMessage.query.filter_by(
                session_id=session.id,
                message_type="call_status"
            ).order_by(SessionMessage.created_at.asc()).all()

            logs = []
            for msg in call_logs:
                try:
                    content = msg.content
                    parts = content.split()
                    call_id = int(parts[1])
                    status = parts[-1]
                    logs.append({
                        "id": call_id,
                        "type": "audio" if "audio" in msg.message_type.lower() else "video",
                        "caller": User.query.get(msg.sender_id).username,
                        "receiver": User.query.get(session.user_id if msg.sender_id == session.expert_id else session.expert_id).username,
                        "status": status,
                        "timestamp": msg.created_at.isoformat()
                    })
                except (IndexError, ValueError) as e:
                    logger.warning(f"Erreur parsing log d'appel - message_id: {msg.id}, erreur: {e}")
                    continue

            logger.debug(f"Logs d'appels récupérés - session_id: {session.id}, nombre: {len(logs)}")
            return logs, 200
        except Exception as e:
            logger.error(f"Erreur récupération logs d'appels: {e}\n{traceback.format_exc()}")
            return {"message": f"Erreur serveur: {str(e)}"}, 500

@ns.route("/call/initiate")
class InitiateCall(Resource):
    @jwt_required()
    @ns.expect(ns.model('CallInitiate', {
        'session_id': fields.Integer(required=True, description='ID de la session'),
        'call_type': fields.String(required=True, enum=['audio', 'video'], description='Type d’appel')
    }))
    def post(self):
        """Initier un appel audio ou vidéo dans une session"""
        user_id = int(get_jwt_identity())
        data = request.get_json()
        session_id = data.get('session_id')
        call_type = data.get('call_type')
        logger.debug(f"POST /call/initiate - user_id: {user_id}, session_id: {session_id}, call_type: {call_type}")

        if not session_id or not call_type or call_type not in ['audio', 'video']:
            logger.error(f"Données invalides - session_id: {session_id}, call_type: {call_type}")
            return {"message": "session_id et call_type (audio ou video) requis."}, 400

        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session introuvable - session_id: {session_id}")
            return {"message": "Session introuvable."}, 404

        if session.status == "completed":
            logger.warning(f"Session terminée - session_id: {session_id}")
            return {"message": "Session terminée, appel impossible."}, 403

        if user_id not in [session.user_id, session.expert_id]:
            logger.error(f"Accès refusé - user_id: {user_id}, session_id: {session_id}")
            return {"message": "Accès refusé à cette session."}, 403

        try:
            message_type = "audio_call_signal" if call_type == "audio" else "video_call_signal"
            content = f"Appel {call_type} initié par {User.query.get(user_id).username}"
            message = SessionMessage(
                session_id=session_id,
                sender_id=user_id,
                message_type=message_type,
                content=content,
                status="sent",
                created_at=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            logger.debug(f"Signal d'appel créé - message_id: {message.id}, type: {message_type}")

            try:
                send_private_message(session_id, user_id, message_type, content)
            except Exception as e:
                logger.error(f"Erreur notification WebSocket: {e}\n{traceback.format_exc()}")

            return {
                "message_id": message.id,
                "session_id": session_id,
                "call_type": call_type,
                "message": content
            }, 201
        except Exception as e:
            logger.error(f"Erreur initiation appel session {session_id}: {e}\n{traceback.format_exc()}")
            db.session.rollback()
            return {"message": f"Erreur serveur: {str(e)}"}, 500
>>>>>>> Stashed changes
