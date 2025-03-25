from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request
from extensions import db
from models.user import User
from models.public_request import PublicRequest
from models.expert_session import ExpertSession, SessionMessage
import os
from datetime import datetime

ns = Namespace("expert", description="Communication avec experts")

public_request_model = ns.model("PublicRequest", {
    "request_type": fields.String(required=True, enum=["text", "audio", "image", "video"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
})

message_model = ns.model("Message", {
    "message_type": fields.String(required=True, enum=["text", "audio", "image", "video", "audio_call", "video_call", "audio_call_signal", "video_call_signal"]),
    "content": fields.String(description="Texte ou chemin fichier")
})

file_parser = ns.parser()
file_parser.add_argument('file', type='file', location='files', required=False)

@ns.route("/public_request")
class PublicRequestResource(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "farmer":
            return {"message": "Seuls les fermiers peuvent créer des demandes."}, 403

        file = request.files.get("file")
        content = request.form.get("content")
        request_type = request.form.get("request_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                return {"message": "Format non supporté."}, 400
            file_path = f"uploads/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = f"http://127.0.0.1:5000/{file_path}"
            request_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif not content:
            return {"message": "Contenu ou fichier requis."}, 400

        request_obj = PublicRequest(user_id=user_id, request_type=request_type, content=content)
        db.session.add(request_obj)
        db.session.commit()
        return {"request_id": request_obj.id}, 201

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"message": "Utilisateur non trouvé."}, 404

        requests = PublicRequest.query.filter_by(user_id=user_id).all() if user.role == "farmer" else PublicRequest.query.filter_by(responded=False).all()
        return [{
            "request_id": req.id,
            "username": User.query.get(req.user_id).username,
            "request_type": req.request_type,
            "content": req.content,
            "created_at": req.created_at.isoformat(),
            "responded": req.responded
        } for req in requests], 200

@ns.route("/public_request/<int:request_id>/respond")
class RespondRequest(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, request_id):
        expert_id = get_jwt_identity()
        expert = User.query.get(expert_id)
        if not expert or expert.role != "expert":
            return {"message": "Vous devez être un expert."}, 403

        public_request = PublicRequest.query.get(request_id)
        if not public_request or public_request.responded:
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
            content = f"http://127.0.0.1:5000/{file_path}"
            message_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"

        session = ExpertSession(user_id=public_request.user_id, expert_id=expert_id, public_request_id=request_id, status="active")
        db.session.add(session)
        db.session.flush()

        message = SessionMessage(session_id=session.id, sender_id=expert_id, message_type=message_type, content=content)
        db.session.add(message)
        public_request.responded = True
        db.session.commit()

        farmer = User.query.get(public_request.user_id)
        return {"farmer_username": farmer.username, "expert_username": expert.username}, 201
    
@ns.route("/session/<string:farmer_username>/<string:expert_username>/message")
class SendPrivateMessage(Resource):
    @jwt_required()
    @ns.expect(file_parser)
    def post(self, farmer_username, expert_username):
        sender_id = get_jwt_identity()
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            return {"message": "Utilisateur non trouvé."}, 404

        # Vérifier ou créer une session
        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).first()
        if not session:
            # Créer une nouvelle session si elle n'existe pas
            session = ExpertSession(user_id=farmer.id, expert_id=expert.id, status="active")
            db.session.add(session)
            db.session.flush()  # Générer l'ID de la session

        # Vérifier que l'utilisateur est autorisé
        if session.user_id != sender_id and session.expert_id != sender_id:
            return {"message": "Accès refusé."}, 403

        file = request.files.get("file")
        content = request.form.get("content")
        message_type = request.form.get("message_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            file_path = f"uploads/{sender_id}_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)
            content = f"http://127.0.0.1:5000/{file_path}"
            message_type = "video" if ext == '.mp4' else "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif message_type in ["audio_call", "video_call"]:
            content = f"{message_type} initié par {User.query.get(sender_id).username}"
        elif message_type.endswith("_call_signal"):
            content = content  # Signal WebRTC
        elif not content:
            return {"message": "Contenu requis."}, 400

        message = SessionMessage(session_id=session.id, sender_id=sender_id, message_type=message_type, content=content)
        db.session.add(message)
        db.session.commit()
        return {"message_id": message.id}, 200

@ns.route("/session/<string:farmer_username>/<string:expert_username>/messages")
class GetSessionMessages(Resource):
    @jwt_required()
    def get(self, farmer_username, expert_username):
        user_id = get_jwt_identity()
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            return {"message": "Utilisateur non trouvé."}, 404

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).first()
        if not session or (session.user_id != user_id and session.expert_id != user_id):
            return {"message": "Session introuvable ou accès refusé."}, 404

        messages = SessionMessage.query.filter_by(session_id=session.id).order_by(SessionMessage.created_at.asc()).all()
        return [{
            "id": msg.id,
            "sender_username": User.query.get(msg.sender_id).username,
            "message_type": msg.message_type,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        } for msg in messages], 200

@ns.route("/sessions")
class UserSessions(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"message": "Utilisateur non trouvé."}, 404

        sessions = ExpertSession.query.filter_by(user_id=user_id).all() if user.role == "farmer" else ExpertSession.query.filter_by(expert_id=user_id).all()
        return [{
            "farmer_username": User.query.get(s.user_id).username,
            "expert_username": User.query.get(s.expert_id).username,
            "request_id": s.public_request_id,
            "last_message": s.messages[-1].content if s.messages else None,
            "created_at": s.created_at.isoformat()
        } for s in sessions], 200

@ns.route("/session/<string:farmer_username>/<string:expert_username>")
class DeleteSession(Resource):
    @jwt_required()
    def delete(self, farmer_username, expert_username):
        user_id = get_jwt_identity()
        farmer = User.query.filter_by(username=farmer_username).first()
        expert = User.query.filter_by(username=expert_username).first()
        if not farmer or not expert:
            return {"message": "Utilisateur non trouvé."}, 404

        session = ExpertSession.query.filter_by(user_id=farmer.id, expert_id=expert.id).first()
        if not session or (session.user_id != user_id and session.expert_id != user_id):
            return {"message": "Session introuvable ou accès refusé."}, 404

        db.session.delete(session)
        db.session.commit()
        return {"message": "Session supprimée."}, 200

# Servir les fichiers uploadés
from flask import send_from_directory
@ns.route("/uploads/<path:filename>")
class ServeUploads(Resource):
    def get(self, filename):
        return send_from_directory("uploads", filename)