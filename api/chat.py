from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.chat_service import process_chat_message
from models.chat_message import ChatMessage
from models.user import User
from extensions import db
import logging
import uuid
from sqlalchemy.exc import IntegrityError, DataError

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ns = Namespace("chat", description="Chatbot pour agriculteurs")

# Modèle pour l'envoi d'un message
message_model = ns.model("ChatMessage", {
    "message": fields.String(required=True, description="Message envoyé par l'utilisateur"),
    "conversation_id": fields.String(description="ID de la conversation (optionnel, généré si non fourni)")
})

# Modèle pour la réponse
response_model = ns.model("ChatResponse", {
    "response": fields.String(description="Réponse générée par le chatbot"),
    "created_at": fields.String(description="Date et heure de création du message"),
    "conversation_id": fields.String(description="ID de la conversation")
})

# Modèle pour les détails d'un message dans l'historique
message_detail_model = ns.model("ChatMessageDetail", {
    "id": fields.Integer(description="ID du message"),
    "message": fields.String(description="Message envoyé par l'utilisateur"),
    "response": fields.String(description="Réponse du chatbot"),
    "created_at": fields.String(description="Date et heure de création")
})

# Modèle pour l'historique
history_model = ns.model("ChatHistory", {
    "conversation_id": fields.String(description="ID de la conversation"),
    "messages": fields.List(fields.Nested(message_detail_model))
})

# Modèle pour la mise à jour d'un message
update_message_model = ns.model("UpdateMessage", {
    "message": fields.String(required=True, description="Nouveau contenu du message")
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
            # Vérifier si l'utilisateur existe
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur avec ID {user_id} non trouvé.")
                return {"message": "Utilisateur non trouvé."}, 404

            data = ns.payload
            message = data.get("message")
            conversation_id = data.get("conversation_id") or str(uuid.uuid4())  # Générer un nouvel ID si non fourni

            if not message or not message.strip():
                logger.warning("Message vide envoyé par l'utilisateur.")
                return {"message": "Le message ne peut pas être vide."}, 400

            # Valider le format de conversation_id comme UUID
            try:
                uuid_obj = uuid.UUID(conversation_id)
                conversation_id = str(uuid_obj)  # Normaliser l'UUID
            except ValueError:
                logger.warning(f"conversation_id invalide : {conversation_id}")
                return {"message": "L'ID de la conversation doit être un UUID valide."}, 400

            # Traiter le message via le service
            response = process_chat_message(user_id, message, conversation_id=conversation_id)

            # Récupérer le dernier message pour la date de création
            last_message = ChatMessage.query.filter_by(user_id=user_id, conversation_id=conversation_id).order_by(ChatMessage.created_at.desc()).first()
            if not last_message:
                logger.error("Échec de l'enregistrement du message dans la base de données.")
                return {"message": "Erreur lors de l'enregistrement du message."}, 500

            created_at = last_message.created_at.isoformat()
            return {"response": response, "created_at": created_at, "conversation_id": conversation_id}, 200

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Erreur d'intégrité lors de l'envoi du message : {e}")
            return {"message": "Erreur : utilisateur ou conversation invalide."}, 400
        except DataError as e:
            db.session.rollback()
            logger.error(f"Erreur de type de données lors de l'envoi du message : {e}")
            return {"message": "Erreur : les types de données fournis sont incorrects."}, 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de l'envoi du message au chatbot : {e}")
            return {"message": "Une erreur s'est produite lors du traitement de votre message."}, 500

@ns.route("/history")
class ChatHistory(Resource):
    @jwt_required()
    @ns.marshal_list_with(history_model, code=200)
    def get(self):
        """
        Récupère l'historique des messages de l'utilisateur, regroupés par conversation.
        """
        try:
            user_id = get_jwt_identity()
            # Vérifier si l'utilisateur existe
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur avec ID {user_id} non trouvé.")
                return {"message": "Utilisateur non trouvé."}, 404

            # Récupérer les conversations distinctes
            conversations = db.session.query(ChatMessage.conversation_id).filter_by(user_id=user_id).distinct().all()
            conversation_ids = [conv[0] for conv in conversations]

            # Récupérer les messages pour chaque conversation
            result = []
            for conv_id in conversation_ids:
                messages = ChatMessage.query.filter_by(user_id=user_id, conversation_id=conv_id).order_by(ChatMessage.created_at.asc()).all()
                result.append({
                    "conversation_id": conv_id,
                    "messages": [
                        {
                            "id": m.id,  # Ajout de l'ID du message
                            "message": m.message,
                            "response": m.response,
                            "created_at": m.created_at.isoformat()
                        }
                        for m in messages
                    ]
                })
            return result, 200

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
            # Vérifier si l'utilisateur existe
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur avec ID {user_id} non trouvé.")
                return {"message": "Utilisateur non trouvé."}, 404

            messages = ChatMessage.query.filter_by(user_id=user_id).all()
            
            if not messages:
                logger.info(f"Aucun message à supprimer pour l'utilisateur {user_id}.")
                return {"message": "Aucun historique à supprimer."}, 200

            for message in messages:
                db.session.delete(message)
            db.session.commit()

            logger.info(f"Historique supprimé avec succès pour l'utilisateur {user_id}.")
            return {"message": "Historique supprimé avec succès."}, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la suppression de l'historique : {e}")
            return {"message": "Une erreur s'est produite lors de la suppression de l'historique."}, 500

@ns.route("/conversations")
class Conversations(Resource):
    @jwt_required()
    def post(self):
        """
        Crée une nouvelle conversation.
        """
        try:
            user_id = get_jwt_identity()
            # Vérifier si l'utilisateur existe
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur avec ID {user_id} non trouvé.")
                return {"message": "Utilisateur non trouvé."}, 404

            conversation_id = str(uuid.uuid4())
            return {"id": conversation_id}, 201

        except Exception as e:
            logger.error(f"Erreur lors de la création de la conversation : {e}")
            return {"message": "Une erreur s'est produite lors de la création de la conversation."}, 500

@ns.route("/conversations/<string:conversation_id>")
class Conversation(Resource):
    @jwt_required()
    def delete(self, conversation_id):
        """
        Supprime une conversation spécifique.
        """
        try:
            user_id = get_jwt_identity()
            # Vérifier si l'utilisateur existe
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur avec ID {user_id} non trouvé.")
                return {"message": "Utilisateur non trouvé."}, 404

            # Valider le format de conversation_id comme UUID
            try:
                uuid_obj = uuid.UUID(conversation_id)
                conversation_id = str(uuid_obj)  # Normaliser l'UUID
            except ValueError:
                logger.warning(f"conversation_id invalide : {conversation_id}")
                return {"message": "L'ID de la conversation doit être un UUID valide."}, 400

            messages = ChatMessage.query.filter_by(user_id=user_id, conversation_id=conversation_id).all()
            
            if not messages:
                logger.info(f"Aucune conversation trouvée avec l'ID {conversation_id} pour l'utilisateur {user_id}.")
                return {"message": "Conversation non trouvée."}, 404

            for message in messages:
                db.session.delete(message)
            db.session.commit()

            logger.info(f"Conversation {conversation_id} supprimée avec succès pour l'utilisateur {user_id}.")
            return {"message": "Conversation supprimée avec succès."}, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la suppression de la conversation : {e}")
            return {"message": "Une erreur s'est produite lors de la suppression de la conversation."}, 500

@ns.route("/messages/<int:message_id>")
class ChatMessageResource(Resource):
    @jwt_required()
    def delete(self, message_id):
        """
        Supprime un message spécifique.
        """
        try:
            user_id = get_jwt_identity()
            message = ChatMessage.query.filter_by(id=message_id, user_id=user_id).first()
            if not message:
                logger.warning(f"Message avec ID {message_id} non trouvé pour l'utilisateur {user_id}.")
                return {"message": "Message non trouvé."}, 404

            db.session.delete(message)
            db.session.commit()
            logger.info(f"Message {message_id} supprimé avec succès pour l'utilisateur {user_id}.")
            return {"message": "Message supprimé avec succès."}, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la suppression du message : {e}")
            return {"message": "Une erreur s'est produite lors de la suppression du message."}, 500

    @jwt_required()
    @ns.expect(update_message_model)
    def put(self, message_id):
        """
        Met à jour un message spécifique.
        """
        try:
            user_id = get_jwt_identity()
            message = ChatMessage.query.filter_by(id=message_id, user_id=user_id).first()
            if not message:
                logger.warning(f"Message avec ID {message_id} non trouvé pour l'utilisateur {user_id}.")
                return {"message": "Message non trouvé."}, 404

            data = ns.payload
            new_message = data.get("message")
            if not new_message or not new_message.strip():
                logger.warning("Message vide envoyé pour la mise à jour.")
                return {"message": "Le message ne peut pas être vide."}, 400

            message.message = new_message
            # Regénérer la réponse si nécessaire
            message.response = process_chat_message(user_id, new_message, message.conversation_id)
            db.session.commit()
            logger.info(f"Message {message_id} mis à jour avec succès pour l'utilisateur {user_id}.")
            return {"message": "Message mis à jour avec succès."}, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la mise à jour du message : {e}")
            return {"message": "Une erreur s'est produite lors de la mise à jour du message."}, 500