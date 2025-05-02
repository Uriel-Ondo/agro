<<<<<<< Updated upstream
=======
from extensions import socketio, db
>>>>>>> Stashed changes
from models.public_request import PublicRequest
from models.expert_session import ExpertSession
from models.user import User
from app import db, socketio
import os
from datetime import datetime
<<<<<<< Updated upstream
import logging
=======
import traceback
>>>>>>> Stashed changes

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_public_request(user_id, request_type, content):
<<<<<<< Updated upstream
    """
    Crée une demande publique et la diffuse à tous les experts en ligne.
    """
    request = PublicRequest(user_id=user_id, request_type=request_type, content=content)
    db.session.add(request)
    db.session.commit()

    # Diffuser à tous les experts en ligne
    notify_all_experts(request)
    return request

def notify_all_experts(request):
    """
    Notifie tous les experts en ligne via WebSocket.
    """
    experts = User.query.filter_by(role="expert", is_online=True).all()
    for expert in experts:
        socketio.emit(
            "new_public_request",
            {
                "request_id": request.id,
                "user_id": request.user_id,
                "request_type": request.request_type,
                "content": request.content,
                "created_at": request.created_at.isoformat()
            },
            namespace="/expert",
            room=f"expert_{expert.id}"
        )
    logger.debug(f"Demande publique {request.id} diffusée à {len(experts)} experts.")

def respond_to_request(request_id, expert_id, response_content, response_type="text"):
    """
    Crée une session privée lorsqu'un expert répond à une demande publique.
    """
    request = PublicRequest.query.get_or_404(request_id)
    if request.responded:
        return {"message": "Cette demande a déjà été prise en charge."}, 400

    # Marquer la demande comme répondue
    request.responded = True
    session = ExpertSession(
        user_id=request.user_id,
        expert_id=expert_id,
        public_request_id=request_id,
        session_type=response_type,
        message=response_content
    )
    db.session.add(session)
    db.session.commit()

    # Notifier l'agriculteur
    socketio.emit(
        "private_session_started",
        {
            "session_id": session.id,
            "expert_id": expert_id,
            "message": response_content,
            "session_type": response_type
        },
        namespace="/expert",
        room=f"user_{request.user_id}"
    )
    logger.debug(f"Session privée {session.id} créée entre user {request.user_id} et expert {expert_id}.")
    return session

def send_private_message(session_id, sender_id, message_type, content):
    """
    Envoie un message dans une session privée.
    """
    session = ExpertSession.query.get_or_404(session_id)
    recipient_id = session.user_id if sender_id == session.expert_id else session.expert_id

    socketio.emit(
        "new_private_message",
        {
            "session_id": session_id,
            "sender_id": sender_id,
            "message_type": message_type,
            "content": content
        },
        namespace="/expert",
        room=f"user_{recipient_id}"
    )
    logger.debug(f"Message privé envoyé dans la session {session_id}: {message_type} - {content}")
    return {"message": "Message envoyé avec succès"}
=======
    """Crée une demande publique."""
    try:
        request = PublicRequest(user_id=user_id, request_type=request_type, content=content)
        db.session.add(request)
        db.session.commit()
        logger.debug(f"Demande publique créée: {request.id}")
        return request
    except Exception as e:
        logger.error(f"Erreur création demande publique: {e}\n{traceback.format_exc()}")
        db.session.rollback()
        raise

def notify_all_experts(request):
    """Notifie tous les experts en ligne d'une nouvelle demande publique."""
    try:
        experts = User.query.filter_by(role="expert", is_online=True).all()
        for expert in experts:
            socketio.emit(
                "new_public_request",
                {
                    "request_id": request.id,
                    "user_id": request.user_id,
                    "username": User.query.get(request.user_id).username,
                    "request_type": request.request_type,
                    "content": request.content,
                    "created_at": request.created_at.isoformat()
                },
                namespace="/expert",
                room=f"user_{expert.id}"
            )
            logger.debug(f"Demande publique {request.id} envoyée à expert {expert.id}")
        logger.debug(f"Demande publique {request.id} envoyée à {len(experts)} experts")
    except Exception as e:
        logger.error(f"Erreur notification experts: {e}\n{traceback.format_exc()}")
        raise

def respond_to_request(request_id, expert_id, response_content, response_type="text"):
    """Notifie l'agriculteur lorsqu'un expert répond à une demande publique."""
    try:
        request = PublicRequest.query.get(request_id)
        if not request:
            logger.error(f"Demande {request_id} introuvable")
            raise ValueError("Demande introuvable")
        
        if request.responded:
            logger.warning(f"Demande {request_id} déjà répondue")
            raise ValueError("Demande déjà prise en charge")

        session = ExpertSession.query.filter_by(public_request_id=request_id).first()
        if not session:
            logger.error(f"Session introuvable pour request_id: {request_id}")
            raise ValueError("Session introuvable")

        socketio.emit(
            "private_session_started",
            {
                "session_id": session.id,
                "expert_id": expert_id,
                "farmer_username": User.query.get(session.user_id).username,
                "expert_username": User.query.get(expert_id).username,
                "request_id": request_id,
                "message": response_content,
                "session_type": response_type
            },
            namespace="/expert",
            room=f"user_{request.user_id}"
        )
        logger.debug(f"Session privée {session.id} notifiée à user {request.user_id}")
    except ValueError as e:
        logger.warning(f"Erreur validation réponse demande {request_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur notification réponse demande {request_id}: {e}\n{traceback.format_exc()}")
        raise

def send_private_message(session_id, sender_id, message_type, content):
    """Notifie les participants d'une session privée d'un nouveau message."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} non trouvée")
            raise ValueError("Session non trouvée")

        recipient_id = session.user_id if sender_id == session.expert_id else session.expert_id
        recipient = User.query.get(recipient_id)
        if not recipient:
            logger.error(f"Destinataire {recipient_id} non trouvé pour session {session_id}")
            raise ValueError("Destinataire non trouvé")

        # Créer un nouveau message
        new_message = SessionMessage(
            session_id=session_id,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            status="sent",
            created_at=datetime.utcnow()
        )
        db.session.add(new_message)
        db.session.flush()  # Obtenir l'ID du message

        new_status = "received" if recipient.is_online else "sent"
        if message_type in ["audio_call_signal", "video_call_signal"] and not recipient.is_online:
            new_status = "pending"
            new_message.status = "pending"
            db.session.commit()
            logger.debug(f"Signal {message_type} stocké comme pending pour user {recipient_id}")
            return

        new_message.status = new_status
        db.session.commit()

        message_data = {
            'id': new_message.id,
            'session_id': session_id,
            'sender_username': User.query.get(sender_id).username,
            'message_type': message_type,
            'content': content,
            'created_at': new_message.created_at.isoformat(),
            'status': new_status,
            'request_id': session.public_request_id
        }

        # Émettre uniquement au destinataire via sa room personnelle
        if recipient.is_online:
            socketio.emit(
                'new_private_message',
                message_data,
                namespace="/expert",
                room=f"user_{recipient_id}"
            )
            logger.debug(f"Message {new_message.id} émis à user_{recipient_id}: {message_type}")

        # Mettre à jour le statut pour l'expéditeur
        socketio.emit(
            'message_status_update',
            {'message_id': new_message.id, 'status': new_status},
            namespace="/expert",
            room=f"user_{sender_id}"
        )
        logger.debug(f"Statut message {new_message.id} émis à user_{sender_id}: {new_status}")

        # Émettre un signal d'appel si nécessaire
        if message_type in ["audio_call_signal", "video_call_signal"] and recipient.is_online:
            socketio.emit(
                'call_signal',
                message_data,
                namespace="/expert",
                room=f"user_{recipient_id}"
            )
            logger.debug(f"Signal d'appel {new_message.id} émis à user_{recipient_id}: {message_type}")

        logger.debug(f"Message {new_message.id} traité dans session {session_id} - status: {new_status}")
    except ValueError as e:
        logger.warning(f"Erreur validation message session {session_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur envoi message session {session_id}: {e}\n{traceback.format_exc()}")
        raise

def send_session_ended(session_id, expert_id, farmer_id):
    """Notifie les utilisateurs que la session est terminée."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} non trouvée")
            raise ValueError("Session non trouvée")

        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": "Session terminée par l'expert."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": "Session terminée par l'expert."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} terminée et notifiée à user_{farmer_id} et user_{expert_id}")
    except ValueError as e:
        logger.warning(f"Erreur validation fin session {session_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur notification fin session {session_id}: {e}\n{traceback.format_exc()}")
        raise

def notify_session_deleted(session_id, farmer_id, expert_id, deleted_by_id):
    """Notifie les utilisateurs que la session a été supprimée."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} non trouvée")
            raise ValueError("Session non trouvée")

        deleted_by = User.query.get(deleted_by_id)
        if not deleted_by:
            logger.error(f"Utilisateur {deleted_by_id} non trouvé")
            raise ValueError("Utilisateur non trouvé")

        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": f"Session supprimée par {deleted_by.username}."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": f"Session supprimée par {deleted_by.username}."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} supprimée et notifiée à user_{farmer_id} et user_{expert_id}")
    except ValueError as e:
        logger.warning(f"Erreur validation suppression session {session_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur notification suppression session {session_id}: {e}\n{traceback.format_exc()}")
        raise

def mark_message_as_read(session_id, message_id, reader_id):
    """Marque un message comme lu et notifie les participants."""
    try:
        message = SessionMessage.query.get(message_id)
        if not message:
            logger.error(f"Message {message_id} non trouvé")
            raise ValueError("Message non trouvé")

        if message.session_id != session_id:
            logger.error(f"Message {message_id} n'appartient pas à la session {session_id}")
            raise ValueError("Session incorrecte")

        if message.status != "read":
            message.status = "read"
            db.session.commit()
            # Notifier uniquement l'expéditeur
            sender_id = message.sender_id
            socketio.emit(
                'message_status_update',
                {'message_id': message_id, 'status': 'read'},
                namespace="/expert",
                room=f"user_{sender_id}"
            )
            logger.debug(f"Message {message_id} marqué comme lu et notifié à user_{sender_id}")
    except ValueError as e:
        logger.warning(f"Erreur validation marquage message {message_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur marquage message {message_id}: {e}\n{traceback.format_exc()}")
        raise
>>>>>>> Stashed changes
