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
OLLAMA_API_URL = "http://127.0.0.1:11434/api/chat"

def process_chat_message(user_id, message, conversation_id=None, image=None):
    """
    Traite un message de l'utilisateur et génère une réponse structurée en utilisant l'API d'Ollama avec Gemma-2b.
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

        # Vérifier la disponibilité d'Ollama
        try:
            response = requests.get("http://127.0.0.1:11434/", timeout=2)
            response.raise_for_status()
            logger.debug("Ollama est accessible.")
        except requests.RequestException as e:
            logger.error(f"Ollama n'est pas accessible : {e.__class__.__name__} - {str(e)}")
            raise ValueError("Le service Ollama n'est pas accessible.")

        # Initialiser la réponse finale
        response_parts = []

        # Ajouter une introduction standard
        response_parts.append("### AgriBot\nJe suis votre assistant agricole expert. Voici ma réponse :")

        # Vérifier si une image est fournie
        if image:
            logger.debug("Analyse de l'image pour détecter une maladie des plantes...")
            result = detect_plant_disease(image, user_id)
            disease = result["disease"]
            confidence = result.get("confidence", 0)
            recommendation = result["recommendation"]

            # Structurer l'analyse de l'image
            image_response = (
                "\n### Analyse de l'image\n"
                f"- **Maladie détectée** : {disease}\n"
                f"- **Confiance** : {confidence * 100:.2f}%\n"
                f"- **Recommandation** : {recommendation}"
            )
            response_parts.append(image_response)
            logger.debug(f"Résultat de l'analyse de l'image : {image_response}")

        # Vérifier si une réponse statique est disponible
        static_response = get_static_response(message)
        if static_response:
            logger.debug(f"Réponse statique trouvée : {static_response}")
            if response_parts and image:  # Si une image a été analysée
                response_parts.append(
                    "\n### Réponse à votre question\n"
                    f"{static_response}"
                )
            else:
                response_parts.append(f"\n### Réponse\n{static_response}")
        else:
            # Préparer le message pour Ollama
            full_message = message
            if response_parts and image:  # Si une image a été analysée
                full_message = f"{response_parts[1]}\n\nUtilisateur : {message}"

            # Préparer la requête pour l'API Ollama avec une instruction claire
            logger.debug(f"Envoi de la requête à Ollama avec le message : {full_message}")
            payload = {
                "model": "gemma:2b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Vous êtes AgriBot, un assistant agricole expert. Votre rôle est de fournir des conseils pratiques et précis sur la plantation, "
                            "l'entretien des cultures, la gestion des sols, les engrais, et les maladies des plantes. Répondez de manière structurée et concise :\n"
                            "- Utilisez des en-têtes avec ### pour les sections (ex. ### Services, ### Conseils pratiques).\n"
                            "- Présentez les informations sous forme de listes avec - pour chaque point.\n"
                            "- Soyez clair, pratique et conversationnel."
                        )
                    },
                    {
                        "role": "user",
                        "content": full_message
                    }
                ],
                "stream": False,
                "temperature": 0.7
            }

            # Envoyer la requête à Ollama avec un timeout
            try:
                logger.debug(f"Payload envoyé à Ollama : {payload}")
                response = requests.post(OLLAMA_API_URL, json=payload)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Erreur lors de la communication avec l'API Ollama : {e.__class__.__name__} - {str(e)}")
                error_response = (
                    "### AgriBot\n"
                    "\n### Erreur\n"
                    f"- Une erreur s'est produite avec l'API Ollama : {e.__class__.__name__} - {str(e)}.\n"
                    "- Veuillez réessayer plus tard."
                )
                chat = ChatMessage(
                    user_id=user_id,
                    message=message,
                    response=error_response,
                    conversation_id=conversation_id
                )
                db.session.add(chat)
                db.session.commit()
                return error_response

            # Extraire et structurer la réponse
            response_data = response.json()
            ollama_response = response_data["message"]["content"].strip()
            logger.debug(f"Réponse d'Ollama : {ollama_response}")

            # Ajouter la réponse d'Ollama
            if response_parts and image:  # Si une image a été analysée
                response_parts.append(
                    "\n### Réponse à votre question\n"
                    f"{ollama_response}"
                )
            else:
                response_parts.append(f"\n{ollama_response}")

        # Combiner les parties en une réponse finale
        final_response = "\n".join(response_parts)

        # Limiter la longueur de la réponse
        if len(final_response) > 500:
            final_response = final_response[:500] + "... (réponse tronquée)"

        # Enregistrer dans la base de données
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=final_response,
            conversation_id=conversation_id
        )
        db.session.add(chat)
        db.session.commit()
        logger.debug(f"Message et réponse enregistrés pour l'utilisateur {user_id}.")

        return final_response

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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur inattendue dans process_chat_message : {e}")
        error_response = (
            "### AgriBot\n"
            "\n### Erreur\n"
            "- Désolé, une erreur inattendue s'est produite.\n"
            "- Veuillez réessayer plus tard."
        )
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=error_response,
            conversation_id=conversation_id
        )
        db.session.add(chat)
        db.session.commit()
        return error_response