from models.chat_message import ChatMessage
from models.user import User
from extensions import db
import requests
import logging
from services.knowledge_base import get_static_response
from services.plant_service import detect_plant_disease
from sqlalchemy.exc import IntegrityError, DataError

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# URL de l'API Ollama
OLLAMA_API_URL = "http://localhost:11434/api/chat"

def process_chat_message(user_id, message, conversation_id=None, image=None):
    """
    Traite un message de l'utilisateur et génère une réponse en utilisant l'API d'Ollama avec Gemma-2b.
    Si une image est fournie, analyse l'image pour détecter une maladie des plantes.
    """
    try:
        # Convertir user_id en entier
        user_id = int(user_id)
        
        # Vérifier si l'utilisateur existe
        user = User.query.get(user_id)
        if not user:
            logger.error(f"Utilisateur avec ID {user_id} non trouvé.")
            raise ValueError("Utilisateur non trouvé.")

        # Vérifier si une image est fournie
        image_description = ""
        if image:
            logger.debug("Analyse de l'image pour détecter une maladie des plantes...")
            result = detect_plant_disease(image, user_id)
            disease = result["disease"]
            recommendation = result["recommendation"]
            image_description = f"L'image montre une plante atteinte de : {disease}. Recommandation : {recommendation}."
            logger.debug(f"Résultat de l'analyse de l'image : {image_description}")

        # Vérifier si une réponse statique est disponible
        static_response = get_static_response(message)
        if static_response:
            logger.debug(f"Réponse statique trouvée : {static_response}")
            response = static_response
            if image_description:
                response = f"{image_description}\n\nConcernant votre question : {response}"
        else:
            # Combiner le message et la description de l'image (si présente)
            full_message = message
            if image_description:
                full_message = f"{image_description}\n\nUtilisateur : {message}"

            # Préparer la requête pour l'API Ollama
            logger.debug(f"Envoi de la requête à Ollama avec le message : {full_message}")
            payload = {
                "model": "gemma:2b",
                "messages": [
                    {
                        "role": "system",
                        "content": "Vous êtes AgriBot, un assistant agricole expert. Vous aidez les agriculteurs avec des conseils pratiques sur la plantation, l'entretien des cultures, la gestion des sols, les engrais, les maladies des plantes, et plus encore. Répondez de manière claire, concise et conversationnelle."
                    },
                    {
                        "role": "user",
                        "content": full_message
                    }
                ],
                "stream": False,
                "temperature": 0.7
            }

            # Envoyer la requête à Ollama
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()

            # Extraire la réponse
            response_data = response.json()
            response = response_data["message"]["content"].strip()
            logger.debug(f"Réponse d'Ollama : {response}")

        # Limiter la longueur de la réponse
        if len(response) > 500:
            response = response[:500] + "..."

        # Enregistrer dans la base de données
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=response,
            conversation_id=conversation_id
        )
        db.session.add(chat)
        db.session.commit()
        logger.debug(f"Message et réponse enregistrés pour l'utilisateur {user_id}.")

        return response

    except ValueError as e:
        logger.error(f"Erreur de validation : {e}")
        raise
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Erreur d'intégrité lors de l'enregistrement du message : {e}")
        raise ValueError("Erreur : utilisateur ou conversation invalide.")
    except DataError as e:
        db.session.rollback()
        logger.error(f"Erreur de type de données lors de l'enregistrement du message : {e}")
        raise ValueError("Erreur : les types de données fournis sont incorrects.")
    except requests.exceptions.RequestException as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la communication avec l'API Ollama : {e}")
        error_response = "Désolé, une erreur s'est produite avec le service de chat. Veuillez réessayer plus tard."
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=error_response,
            conversation_id=conversation_id
        )
        db.session.add(chat)
        db.session.commit()
        return error_response
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur inattendue dans process_chat_message : {e}")
        error_response = "Désolé, une erreur s'est produite. Veuillez réessayer plus tard."
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=error_response,
            conversation_id=conversation_id
        )
        db.session.add(chat)
        db.session.commit()
        return error_response