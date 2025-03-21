from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.expert_service import create_public_request, respond_to_request, send_private_message
from models.user import User
from flask import request
import os
from datetime import datetime

ns = Namespace("expert", description="Communication avec experts")

# Modèle pour une demande publique
public_request_model = ns.model("PublicRequest", {
    "request_type": fields.String(required=True, enum=["text", "audio", "image"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
})

# Modèle pour une réponse
response_model = ns.model("Response", {
    "response_type": fields.String(required=True, enum=["text", "audio", "image"]),
    "content": fields.String(description="Texte ou laissé vide pour fichier")
})

# Parser pour les fichiers
file_parser = ns.parser()
file_parser.add_argument('file', type='file', location='files', required=False, help="Fichier audio ou image")

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
            file.save(file_path)
            content = file_path
            request_type = "image" if ext in {'.jpg', '.jpeg', '.png'} else "audio"
        elif not content:
            return {"message": "Contenu ou fichier requis."}, 400

        request_obj = create_public_request(user_id, request_type, content)
        return {"request_id": request_obj.id}, 201

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
            return {"message": "Vous devez être un expert pour répondre."}, 403

        file = request.files.get("file")
        content = request.form.get("content")
        response_type = request.form.get("response_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                return {"message": "Format de fichier non supporté."}, 400
            file_path = f"uploads/{expert_id}_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.makedirs("uploads", exist_ok=True)
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
        file = request.files.get("file")
        content = request.form.get("content")
        message_type = request.form.get("message_type", "text")

        if file:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.wav', '.mp3'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
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