from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.chat_service import process_chat_message
from models.chat_message import ChatMessage
from app import db
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ns = Namespace("chat", description="Chatbot pour agriculteurs")

# Modèle pour l'envoi d'un message
message_model = ns.model("ChatMessage", {
    "message": fields.String(required=True, description="Message envoyé par l'utilisateur")
})

# Modèle pour la réponse
response_model = ns.model("ChatResponse", {
    "response": fields.String(description="Réponse générée par le chatbot"),
    "created_at": fields.String(description="Date et heure de création du message")
})

# Modèle pour l'historique (optionnel, utilisé dans /history)
history_model = ns.model("ChatHistory", {
    "message": fields.String(description="Message envoyé par l'utilisateur"),
    "response": fields.String(description="Réponse du chatbot"),
    "created_at": fields.String(description="Date et heure de création")
})

@ns.route("/send")
class ChatSend(Resource):
    @jwt_required()
    @ns.expect(message_model)
    @ns.marshal_with(response_model, code=200)
    def post(self):
        """
        Envoie un message au chatbot et reçoit une réponse.
        """
        try:
            user_id = get_jwt_identity()
            data = ns.payload
            message = data.get("message")

            if not message or not message.strip():
                logger.warning("Message vide envoyé par l'utilisateur.")
                return {"message": "Le message ne peut pas être vide."}, 400

            response = process_chat_message(user_id, message)
            
            # Récupérer le dernier message enregistré pour obtenir la date de création
            last_message = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.desc()).first()
            created_at = last_message.created_at.isoformat() if last_message else None

            return {"response": response, "created_at": created_at}, 200

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message au chatbot : {e}")
            return {"message": "Une erreur s'est produite lors du traitement de votre message."}, 500

@ns.route("/history")
class ChatHistory(Resource):
    @jwt_required()
    @ns.marshal_list_with(history_model, code=200)
    def get(self):
        """
        Récupère l'historique des messages de l'utilisateur.
        """
        try:
            user_id = get_jwt_identity()
            messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.asc()).all()
            return [
                {
                    "message": m.message,
                    "response": m.response,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ], 200

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique : {e}")
            return {"message": "Une erreur s'est produite lors de la récupération de l'historique."}, 500

@ns.route("/history/delete")
class ChatHistoryDelete(Resource):
    @jwt_required()
    def delete(self):
        """
        Supprime l'historique des messages de l'utilisateur.
        """
        try:
            user_id = get_jwt_identity()
            # Récupérer tous les messages de l'utilisateur
            messages = ChatMessage.query.filter_by(user_id=user_id).all()
            
            if not messages:
                logger.info(f"Aucun message à supprimer pour l'utilisateur {user_id}.")
                return {"message": "Aucun historique à supprimer."}, 200

            # Supprimer tous les messages
            for message in messages:
                db.session.delete(message)
            db.session.commit()

            logger.info(f"Historique supprimé avec succès pour l'utilisateur {user_id}.")
            return {"message": "Historique supprimé avec succès."}, 200

        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'historique : {e}")
            db.session.rollback()  # Annuler les changements en cas d'erreur
            return {"message": "Une erreur s'est produite lors de la suppression de l'historique."}, 500