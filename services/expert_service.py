from app import socketio, db
from models.public_request import PublicRequest
from models.expert_session import ExpertSession, SessionMessage
from models.user import User
import logging
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_public_request(user_id, request_type, content):
    """Crée une demande publique (utilisée dans expert.py)."""
    try:
        request = PublicRequest(user_id=user_id, request_type=request_type, content=content)
        db.session.add(request)
        db.session.commit()
        logger.debug(f"Demande publique créée: {request.id}")
        return request
    except Exception as e:
        logger.error(f"Erreur lors de la création de la demande publique: {e}")
        db.session.rollback()
        raise

def notify_all_experts(request):
    """Notifie tous les experts en ligne via WebSocket d'une nouvelle demande publique."""
    try:
        experts = User.query.filter_by(role="expert", is_online=True).all()
        for expert in experts:
            try:
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
                    room=f"user_{expert.id}"
                )
                logger.debug(f"Demande publique {request.id} diffusée à l'expert {expert.id}")
            except Exception as e:
                logger.error(f"Erreur lors de la diffusion à l'expert {expert.id}: {e}")
        logger.debug(f"Demande publique {request.id} diffusée à {len(experts)} experts")
    except Exception as e:
        logger.error(f"Erreur lors de la notification des experts: {e}")
        raise

def respond_to_request(request_id, expert_id, response_content, response_type="text"):
    """Notifie l'agriculteur via WebSocket lorsqu'un expert répond à une demande publique."""
    try:
        request = PublicRequest.query.get_or_404(request_id)
        if request.responded:
            logger.error(f"Demande {request_id} déjà répondue")
            return {"message": "Cette demande a déjà été prise en charge."}, 400

        session = ExpertSession.query.filter_by(public_request_id=request_id).first()
        if not session:
            logger.error(f"Session introuvable pour request_id: {request_id}")
            return {"message": "Session introuvable après création."}, 500

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
        logger.debug(f"Session privée {session.id} notifiée à user {request.user_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la notification de la réponse à la demande {request_id}: {e}")
        raise

def send_private_message(session_id, sender_id, message_type, content):
    """Notifie les participants d'une session privée via WebSocket d'un nouveau message."""
    try:
        session = ExpertSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} non trouvée")
            return {"message": "Session non trouvée."}, 404

        message = SessionMessage.query.filter_by(session_id=session_id).order_by(SessionMessage.id.desc()).first()
        recipient_id = session.user_id if sender_id == session.expert_id else session.expert_id
        recipient = User.query.get(recipient_id)
        
        # Mettre à jour le statut en fonction de l'état en ligne du destinataire
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
            'status': new_status
        }

        # Émettre à la room de la session
        socketio.emit(
            'new_private_message',
            message_data,
            namespace="/expert",
            room=f"session_{session_id}"
        )
        
        # Notifier l'expéditeur du statut initial
        socketio.emit(
            'message_status_update',
            {'message_id': message.id, 'status': new_status},
            namespace="/expert",
            room=f"user_{sender_id}"
        )
        
        logger.debug(f"Message envoyé via WebSocket dans la session {session_id} avec status: {new_status}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message dans la session {session_id}: {e}")
        raise

def send_session_ended(session_id, expert_id, farmer_id):
    """Notifie les deux utilisateurs que la session est terminée via WebSocket."""
    try:
        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "message": "La session a été terminée par l'expert."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_ended",
            {
                "session_id": session_id,
                "message": "Vous avez terminé la session."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} terminée et notifiée à farmer {farmer_id} et expert {expert_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la notification de fin de session {session_id}: {e}")
        raise

def notify_session_deleted(session_id, farmer_id, expert_id, deleted_by_id):
    """Notifie les deux utilisateurs que la session a été supprimée via WebSocket."""
    try:
        deleted_by = User.query.get(deleted_by_id).username
        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "message": f"La session a été supprimée par {deleted_by}."
            },
            namespace="/expert",
            room=f"user_{farmer_id}"
        )
        socketio.emit(
            "session_deleted",
            {
                "session_id": session_id,
                "message": f"Vous avez supprimé la session." if deleted_by_id == expert_id else f"La session a été supprimée par {deleted_by}."
            },
            namespace="/expert",
            room=f"user_{expert_id}"
        )
        logger.debug(f"Session {session_id} supprimée et notifiée à farmer {farmer_id} et expert {expert_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la notification de suppression de session {session_id}: {e}")
        raise

def mark_message_as_read(session_id, message_id, reader_id):
    """Marque un message comme lu et notifie les participants."""
    try:
        message = SessionMessage.query.get(message_id)
        if message and message.session_id == session_id and message.status != "read":
            message.status = "read"
            db.session.commit()
            socketio.emit(
                'message_status_update',
                {'message_id': message_id, 'status': 'read'},
                namespace="/expert",
                room=f"session_{session_id}"  # Émettre à la room de la session
            )
            logger.debug(f"Message {message_id} marqué comme lu dans la session {session_id}")
    except Exception as e:
        logger.error(f"Erreur lors du marquage du message {message_id} comme lu: {e}")
        raise