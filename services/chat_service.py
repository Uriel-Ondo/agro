from models.chat_message import ChatMessage
from models.user import User
from extensions import db
import logging
from services.knowledge_base import get_static_response
from services.plant_service import detect_plant_disease
from sqlalchemy.exc import IntegrityError, DataError
import os
import cohere

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Charger la clé d'API Cohere depuis l'environnement
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    logger.error("COHERE_API_KEY non défini dans l'environnement")
    raise ValueError("COHERE_API_KEY doit être défini dans l'environnement")

# Initialiser le client Cohere
co = cohere.Client(COHERE_API_KEY)

def process_chat_message(user_id, message, conversation_id=None, image=None):
    """
    Traite un message de l'utilisateur et génère une réponse conversationnelle en utilisant l'API de Cohere.
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

        # Initialiser la réponse finale
        response_parts = []

        # Vérifier si une image est fournie
        if image:
            logger.debug("Analyse de l'image pour détecter une maladie des plantes...")
            result = detect_plant_disease(image, user_id)
            disease = result["disease"]
            confidence = result.get("confidence", 0)
            recommendation = result["recommendation"]

            # Structurer l'analyse de l'image
            image_response = (
                f"J'ai analysé l'image fournie. Voici les résultats : une maladie ({disease}) a été détectée avec une confiance de {confidence * 100:.2f}%. Voici ma recommandation : {recommendation}."
            )
            response_parts.append(image_response)
            logger.debug(f"Résultat de l'analyse de l'image : {image_response}")

        # Vérifier si une réponse statique est disponible
        static_response = get_static_response(message)
        if static_response:
            logger.debug(f"Réponse statique trouvée : {static_response}")
            response_parts.append(static_response)
        else:
            # Préparer le message pour Cohere
            full_message = message
            if response_parts and image:  # Si une image a été analysée
                full_message = f"{response_parts[0]}\n\nQuestion de l'utilisateur : {message}"

            # Instruction système pour Cohere
            system_prompt = (
                "Vous êtes AgriBot, un assistant agricole expert s'exprimant en français. Votre rôle est de fournir des réponses claires, pratiques et bien organisées sur la plantation, "
                "l'entretien des cultures, la gestion des sols, les engrais et les maladies des plantes. Répondez de manière conversationnelle, en utilisant des paragraphes clairs et logiques, "
                "comme si vous expliquiez à un agriculteur. Évitez les termes trop techniques ou confus, et assurez-vous que la réponse est facile à comprendre. Ne pas utiliser de mise en forme comme des en-têtes ou des listes à puces. "
                "Adaptez-vous à la question posée et fournissez des informations précises et pertinentes. Si la question concerne une culture spécifique, donnez des étapes ou des conseils pratiques adaptés à cette culture."
            )

            # Envoyer la requête à Cohere
            try:
                logger.debug(f"Envoi de la requête à Cohere avec le message : {full_message}")
                response = co.generate(
                    model="command",
                    prompt=f"{system_prompt}\n\nQuestion de l'utilisateur : {full_message}",
                    max_tokens=1500,  # Augmenter pour des réponses plus détaillées
                    temperature=0.6,  # Réduire pour des réponses plus cohérentes
                    k=0,  # Désactiver le top-k sampling pour plus de précision
                    p=0.75  # Ajuster le top-p pour équilibrer créativité et pertinence
                )
                cohere_response = response.generations[0].text.strip()
                logger.debug(f"Réponse de Cohere : {cohere_response}")

                # Ajouter la réponse de Cohere
                response_parts.append(cohere_response)

            except Exception as e:
                logger.error(f"Erreur lors de la communication avec l'API Cohere : {e}")
                error_response = (
                    f"Une erreur s'est produite lors de la génération de la réponse : {str(e)}. Veuillez réessayer plus tard."
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

        # Combiner les parties en une réponse finale
        final_response = "\n\n".join(response_parts)

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
            "Désolé, une erreur inattendue s'est produite. Veuillez réessayer plus tard."
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