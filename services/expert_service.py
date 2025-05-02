import traceback
from extensions import socketio, db
from models.public_request import PublicRequest
from models.expert_session import ExpertSession, SessionMessage
from models.user import User
import logging
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_public_request(user_id, request_type, content):
    """Crée une demande publique."""
    try:
        request = PublicRequest(user_id=user_id, request_type=request_type, content=content)
        db.session.add(request)
        db.session.commit()
        logger.debug(f"Demande publique créée: request_id={request.id}")
        return request
    except Exception as e:
        logger.error(f"Erreur création demande publique user_id={user_id}: {e}\n{traceback.format_exc()}")
        db.session.rollback()
        raise

def notify_all_experts(request):
    """Notifie tous les experts en ligne via WebSocket d'une nouvelle demande publique."""
    try:
        experts = User.query.filter_by(role="expert", is_online=True).all()
        request_data = {
            "request_id": request.id,
            "user_id": request.user_id,
            "username": User.query.get(request.user_id).username,
            "request_type": request.request_type,
            "content": request.content,
            "created_at": request.created_at.isoformat()
        }
        for expert in experts:
            try:
                socketio.emit(
                    "new_public_request",
                    request_data,
                    namespace="/expert",
                    room=f"user_{expert.id}"
                )
                logger.debug(f"Demande publique {request.id} diffusée à expert_id={expert.id}")
            except Exception as e:
                logger.error(f"Erreur diffusion à expert_id={expert.id}: {e}\n{traceback.format_exc()}")
        logger.debug(f"Demande publique {request.id} diffusée à {len(experts)} experts")
    except Exception as e:
        logger.error(f"Erreur notification experts pour request_id={request.id}: {e}\n{traceback.format_exc()}")
        raise

def respond_to_request(request_id, expert_id, response_content, response_type="text"):
    """Notifie l'agriculteur via WebSocket lorsqu'un expert répond à une demande publique."""
    try:
        request = PublicRequest.query.get(request_id)
        if not request:
            logger.error(f"Demande introuvable: request_id={request_id}")
            raise ValueError("Demande introuvable")
        if request.responded:
            logger.error(f"Demande déjà répondue: request_id={request_id}")
            return {"message": "Cette demande a déjà été prise en charge."}, 400

        session = ExpertSession.query.filter_by(public_request_id=request_id).first()
        if not session:
            logger.error(f"Session introuvable pour request_id={request_id}")
            raise ValueError("Session introuvable après création.")

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
        logger.debug(f"Session privée {session.id} notifiée à user_id={request.user_id}")
    except Exception as e:
        logger.error(f"Erreur notification réponse request_id={request_id}: {e}\n{traceback.format_exc()}")
        raise

def send_private_message(session_id, sender_id, message_type, content):
    """Notifie les participants d'une session privée via WebSocket d'un nouveau message."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session introuvable: session_id={session_id}")
            raise ValueError("Session non trouvée.")

        message = SessionMessage.query.filter_by(session_id=session_id).order_by(SessionMessage.id.desc()).first()
        if not message:
            logger.error(f"Aucun message trouvé pour session_id={session_id}")
            raise ValueError("Message non trouvé.")

        recipient_id = session.user_id if sender_id == session.expert_id else session.expert_id
        recipient = User.query.get(recipient_id)
        if not recipient:
            logger.error(f"Destinataire introuvable: recipient_id={recipient_id}")
            raise ValueError("Destinataire non trouvé.")

        new_status = "received" if recipient.is_online else "sent"
        message.status = new_status
        db.session.commit()

        message_data = {
            'id': message.id,
            'session_id': session_id,
            'sender_username': User.query.get(sender_id).username,
            'message_type': message_type,
            'content': content,
            'created_at': message.created_at.isoformat(),
            'status': new_status,
            'request_id': session.public_request_id
        }

        socketio.emit(
            'new_private_message',
            message_data,
            namespace="/expert",
            room=f"session_{session_id}"
        )

        socketio.emit(
            'message_status_update',
            {'message_id': message.id, 'status': new_status},
            namespace="/expert",
            room=f"user_{sender_id}"
        )

        logger.debug(f"Message envoyé via WebSocket dans session_id={session_id}, status={new_status}")
    except Exception as e:
        logger.error(f"Erreur envoi message session_id={session_id}: {e}\n{traceback.format_exc()}")
        raise

def send_session_ended(session_id, expert_id, farmer_id):
    """Notifie les deux utilisateurs que la session est terminée via WebSocket."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session introuvable: session_id={session_id}")
            raise ValueError("Session non trouvée.")

        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": "La session a été terminée par l'expert."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": "Vous avez terminé la session."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} terminée et notifiée à farmer_id={farmer_id}, expert_id={expert_id}")
    except Exception as e:
        logger.error(f"Erreur notification fin session_id={session_id}: {e}\n{traceback.format_exc()}")
        raise

def notify_session_deleted(session_id, farmer_id, expert_id, deleted_by_id):
    """Notifie les deux utilisateurs que la session a été supprimée via WebSocket."""
    try:
        deleted_by = User.query.get(deleted_by_id)
        if not deleted_by:
            logger.error(f"Utilisateur introuvable: deleted_by_id={deleted_by_id}")
            raise ValueError("Utilisateur non trouvé.")

        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session introuvable: session_id={session_id}")
            raise ValueError("Session non trouvée.")

        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": f"La session a été supprimée par {deleted_by.username}."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "request_id": session.public_request_id,
                "message": f"Vous avez supprimé la session." if deleted_by_id == expert_id else f"La session a été supprimée par {deleted_by.username}."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} supprimée et notifiée à farmer_id={farmer_id}, expert_id={expert_id}")
    except Exception as e:
        logger.error(f"Erreur notification suppression session_id={session_id}: {e}\n{traceback.format_exc()}")
        raise

def mark_message_as_read(session_id, message_id, reader_id):
    """Marque un message comme lu et notifie les participants."""
    try:
        message = SessionMessage.query.get(message_id)
        if not message:
            logger.error(f"Message introuvable: message_id={message_id}")
            raise ValueError("Message non trouvé.")

        if message.session_id != session_id:
            logger.error(f"Message session_id mismatch: message_id={message_id}, session_id={session_id}")
            raise ValueError("Session ID mismatch.")

        if message.status != "read":
            message.status = "read"
            db.session.commit()
            socketio.emit(
                'message_status_update',
                {'message_id': message_id, 'status': 'read'},
                namespace="/expert",
                room=f"session_{session_id}"
            )
            logger.debug(f"Message {message_id} marqué comme lu dans session_id={session_id}")
    except Exception as e:
        logger.error(f"Erreur marquage message_id={message_id} comme lu: {e}\n{traceback.format_exc()}")
        raise