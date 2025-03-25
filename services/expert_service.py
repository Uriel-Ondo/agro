from models.public_request import PublicRequest
from models.expert_session import ExpertSession
from models.user import User
from extensions import db, socketio
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_public_request(user_id, request_type, content):
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