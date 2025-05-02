import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, request
from flask_restx import Api
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import decode_token
from config import Config
from flask_socketio import SocketIO, join_room, leave_room, emit
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import os
import atexit
from extensions import db, jwt, mail, socketio

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.debug("Application Flask créée avec succès")

    if not app.config.get('JWT_SECRET_KEY'):
        logger.error("JWT_SECRET_KEY non défini dans la configuration !")
        raise ValueError("JWT_SECRET_KEY doit être défini dans Config")

    # Liste des origines autorisées
    ALLOWED_ORIGINS = [
        "http://192.168.1.90:8100",
        "http://192.168.1.90:5000",
        "http://localhost:8100",
        "http://localhost:5000",
        "http://127.0.0.1:8100",
    ]
    if os.getenv("ALLOWED_CORS_ORIGINS"):
        ALLOWED_ORIGINS.extend(os.getenv("ALLOWED_CORS_ORIGINS").split(","))

    # Initialisation des extensions
    socketio.init_app(app, cors_allowed_origins=ALLOWED_ORIGINS, logger=True, engineio_logger=True)
    logger.debug(f"SocketIO initialisé avec origines autorisées : {ALLOWED_ORIGINS}")
    db.init_app(app)
    logger.debug("SQLAlchemy initialisé")
    migrate.init_app(app, db)
    logger.debug("Migrate initialisé")
    jwt.init_app(app)
    logger.debug("JWTManager initialisé")
    mail.init_app(app) if app.config.get('MAIL_SERVER') else None
    logger.debug("Mail initialisé" if app.config.get('MAIL_SERVER') else "Mail non configuré")

    # Gestion des erreurs JWT
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logger.error(f"Token invalide : {error}")
        return {"msg": "Signature verification failed"}, 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        logger.error(f"Accès non autorisé : {error}")
        return {"msg": "Missing or invalid Authorization header"}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logger.error("Token expiré")
        return {"msg": "Token has expired"}, 401

    # Configuration CORS
    CORS(app, resources={r"/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "max_age": 86400
    }})
    logger.debug(f"CORS configuré pour les requêtes HTTP avec origines : {ALLOWED_ORIGINS}")

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', ALLOWED_ORIGINS[0])
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response

    @app.after_request
    def log_response(response):
        origin = request.headers.get('Origin')
        response.headers['Access-Control-Allow-Origin'] = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        logger.debug(f"Response Headers: {response.headers}")
        return response

    scheduler = BackgroundScheduler()

    # Importation des modèles
    from models.user import User
    from models.plant_disease import PlantDisease
    from models.chat_message import ChatMessage
    from models.live_comment import LiveComment
    from models.live_session import LiveSession
    from models.expert_session import ExpertSession, SessionMessage
    from models.public_request import PublicRequest

    api = Api(
        title="Agri Assist API",
        description="API pour l'application d'assistance agricole",
        security="Bearer Auth",
        authorizations={
            "Bearer Auth": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization"
            }
        }
    )
    api.init_app(app)
    logger.debug("API Flask-RESTX initialisée")

    with app.app_context():
        try:
            db.create_all()
            logger.debug("Tables créées avec succès dans la base de données.")

            def create_admin_user():
                admin_email = os.getenv("ADMIN_EMAIL")
                admin_username = os.getenv("ADMIN_USERNAME")
                admin_password = os.getenv("ADMIN_PASSWORD")
                if not User.query.filter_by(email=admin_email).first():
                    admin_user = User(
                        username=admin_username,
                        email=admin_email,
                        role="expert",
                        is_admin=True
                    )
                    admin_user.set_password(admin_password)
                    db.session.add(admin_user)
                    db.session.commit()
                    logger.info(f"Utilisateur admin créé avec succès : {admin_username}")
            create_admin_user()

        except Exception as e:
            logger.error(f"Erreur dans le contexte d'application : {e}")
            return None

    # Routes statiques
    @app.route('/live_comments')
    def live_comments():
        return send_from_directory('static', 'live_comments.html')

    @app.route('/expert_chat')
    def expert_chat():
        return send_from_directory('static', 'expert_chat.html')

    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        return send_from_directory('uploads', filename)

    # Gestion des WebSockets
    @socketio.on('connect', namespace='/live')
    def handle_live_connect(auth=None):
        logger.debug(f"Client connecté à /live depuis {request.headers.get('Origin')}")
        join_room("live_room")
        if auth and auth.get('token'):
            try:
                decoded_token = decode_token(auth['token'])
                logger.debug(f"Utilisateur authentifié connecté : {decoded_token['sub']}")
            except Exception as e:
                logger.warning(f"Token invalide fourni : {e}")
        else:
            logger.debug("Connexion anonyme à /live")

    @socketio.on('disconnect', namespace='/live')
    def handle_live_disconnect():
        logger.debug("Client déconnecté de /live")
        leave_room("live_room")

    @socketio.on('new_comment', namespace='/live')
    def handle_new_comment(data):
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        if not user_id or not data.get('comment'):
            logger.warning("Commentaire refusé : données invalides")
            emit('error', {'message': 'Authentification requise'}, room=request.sid)
            return
        user = db.session.get(User, user_id)
        comment = LiveComment(
            user_id=user_id,
            username=user.username,
            comment=data['comment'],
            created_at=datetime.utcnow()
        )
        db.session.add(comment)
        db.session.commit()
        comment_data = {
            'id': comment.id,
            'username': comment.username,
            'comment': comment.comment,
            'created_at': comment.created_at.isoformat()
        }
        emit('new_comment', comment_data, namespace='/live', room="live_room")
        logger.debug(f"Commentaire ajouté par {user.username}: {comment.comment}")

    @socketio.on('start_live', namespace='/expert')
    def handle_start_live(data):
        user_id = request.args.get('user_id')
        if not user_id or not user_id.isdigit():
            logger.error(f"Start live refusé - user_id: {user_id}")
            socketio.emit('error', {'message': 'User ID invalide'}, namespace='/expert', room=request.sid)
            return

        user = db.session.get(User, int(user_id))
        if not user or user.role != 'expert':
            logger.error(f"Start live refusé - expert: {user_id}")
            socketio.emit('error', {'message': 'Accès refusé'}, namespace='/expert', room=request.sid)
            return

        stream_url = data.get('stream_url')
        if not stream_url:
            logger.error(f"Stream URL manquant pour {user.username}")
            socketio.emit('error', {'message': 'Stream URL requis'}, namespace='/expert', room=request.sid)
            return

        live_session = LiveSession(
            expert_id=user_id,
            stream_url=stream_url,
            stream_type='hls',
            title=data.get('title', f'Live - {user.username}'),
            status='active',
            started_at=datetime.utcnow()
        )
        db.session.add(live_session)
        db.session.commit()

        live_data = {
            'session_id': live_session.id,
            'expert_id': user_id,
            'expert_username': user.username,
            'stream_url': live_session.stream_url,
            'stream_type': live_session.stream_type,
            'title': live_session.title,
            'started_at': live_session.started_at.isoformat()
        }
        socketio.emit('live_started', live_data, namespace='/live', room="live_room")
        logger.info(f"Live démarré par {user.username} - ID: {live_session.id}")

    @socketio.on('end_live', namespace='/expert')
    def handle_end_live(data):
        user_id = request.args.get('user_id')
        session_id = data.get('session_id')
        live_session = LiveSession.query.get(session_id)

        if not live_session or live_session.expert_id != int(user_id):
            logger.error(f"End live refusé - session: {session_id}")
            socketio.emit('error', {'message': 'Session invalide'}, namespace='/expert', room=request.sid)
            return

        live_session.status = 'ended'
        live_session.ended_at = datetime.utcnow()
        db.session.commit()

        socketio.emit('live_ended', {
            'session_id': session_id,
            'expert_username': User.query.get(live_session.expert_id).username
        }, namespace='/live', room="live_room")
        logger.info(f"Live terminé - ID: {session_id}")

    @socketio.on('connect', namespace='/expert')
    def handle_expert_connect(auth=None):
        user_id = request.args.get('user_id')
        token = auth.get('token') if auth else None
        logger.debug(f"Connexion /expert - user_id: {user_id}, token: {token}, SID: {request.sid}")

        if not token:
            logger.warning(f"Connexion refusée - token manquant, SID: {request.sid}")
            return False

        try:
            decoded_token = decode_token(token)
            token_user_id = decoded_token['sub']
            logger.debug(f"Token décodé - token_user_id: {token_user_id}, exp: {decoded_token.get('exp')}")
            if not user_id or user_id != str(token_user_id):
                logger.warning(f"Connexion refusée - user_id: {user_id}, token_user_id: {token_user_id}, SID: {request.sid}")
                return False
        except Exception as e:
            logger.warning(f"Connexion refusée - token invalide: {e}, SID: {request.sid}")
            return False

        if not user_id or user_id == "undefined" or not user_id.isdigit():
            logger.warning(f"Connexion refusée - user_id invalide: {user_id}, SID: {request.sid}")
            return False

        user = db.session.get(User, int(user_id))
        if user:
            user.set_online(True)
            join_room(f"user_{user_id}")
            sessions = ExpertSession.query.filter(
                ExpertSession.status == 'active',
                (ExpertSession.user_id == user_id) | (ExpertSession.expert_id == user_id)
            ).all()
            for session in sessions:
                if f"session_{session.id}" not in socketio.server.rooms(request.sid, namespace='/expert'):
                    join_room(f"session_{session.id}")
                    logger.debug(f"Utilisateur {user_id} a rejoint session_{session.id}, SID: {request.sid}")
            
            pending_signals = SessionMessage.query.filter(
                SessionMessage.message_type.in_(["audio_call_signal", "video_call_signal"]),
                SessionMessage.status == "pending",
                ExpertSession.user_id == user_id
            ).join(ExpertSession).all()
            for signal in pending_signals:
                socketio.emit(
                    'pending_signal',
                    {
                        'id': signal.id,
                        'session_id': signal.session_id,
                        'sender_username': User.query.get(signal.sender_id).username,
                        'message_type': signal.message_type,
                        'content': signal.content,
                        'created_at': signal.created_at.isoformat(),
                        'status': signal.status
                    },
                    namespace="/expert",
                    room=f"user_{user_id}"
                )
                signal.status = "sent"
            db.session.commit()
            logger.debug(f"Signaux en attente envoyés à user {user_id}: {len(pending_signals)}, SID: {request.sid}")
        else:
            logger.warning(f"Utilisateur non trouvé - user_id: {user_id}, SID: {request.sid}")
            return False

    @socketio.on('join_session', namespace='/expert')
    def handle_join_session(data, callback=None):
        user_id = request.args.get('user_id')
        session_id = data.get('session_id')
        logger.debug(f"join_session - user_id: {user_id}, session_id: {session_id}, SID: {request.sid}")

        if not user_id or not user_id.isdigit() or not session_id:
            logger.warning(f"Join session refusé - user_id: {user_id}, session_id: {session_id}, SID: {request.sid}")
            if callback:
                callback({'status': 'error', 'message': 'Paramètres invalides'})
            return

        user = db.session.get(User, int(user_id))
        session = ExpertSession.query.get(session_id)
        if not user or not session:
            logger.warning(f"Ressource non trouvée - user_id: {user_id}, session_id: {session_id}, SID: {request.sid}")
            if callback:
                callback({'status': 'error', 'message': 'Utilisateur ou session introuvable'})
            return

        if user_id not in [str(session.user_id), str(session.expert_id)]:
            logger.warning(f"Accès refusé - user_id: {user_id}, session: {session_id}, SID: {request.sid}")
            if callback:
                callback({'status': 'error', 'message': 'Accès refusé'})
            return

        if f"session_{session_id}" not in socketio.server.rooms(request.sid, namespace='/expert'):
            join_room(f"session_{session_id}")
            logger.debug(f"Utilisateur {user_id} a rejoint session_{session_id}, SID: {request.sid}")

        if callback:
            callback({'status': 'success', 'session_id': session_id})
        else:
            emit('join_session_response', {'status': 'success', 'session_id': session_id}, namespace='/expert')
            
    @socketio.on('disconnect', namespace='/expert')
    def handle_expert_disconnect():
        user_id = request.args.get('user_id')
        if user_id and user_id.isdigit():
            user = db.session.get(User, int(user_id))
            if user:
                user.set_online(False)
                leave_room(f"user_{user_id}")
                logger.debug(f"Utilisateur {user_id} déconnecté de /expert")
            else:
                logger.warning(f"Déconnexion - user_id invalide: {user_id}")

    @socketio.on('mark_message_read', namespace='/expert')
    def handle_mark_message_read(data):
        user_id = request.args.get('user_id')
        session_id = data.get('session_id')
        message_id = data.get('message_id')
        logger.debug(f"mark_message_read - user_id: {user_id}, session_id: {session_id}, message_id: {message_id}")

        if not user_id or not user_id.isdigit() or not session_id or not message_id:
            logger.warning(f"Marquage refusé - user_id: {user_id}, session_id: {session_id}, message_id: {message_id}")
            emit('error', {'message': 'Paramètres invalides'}, namespace='/expert')
            return

        try:
            from services.expert_service import mark_message_as_read
            mark_message_as_read(session_id, message_id, int(user_id))
            logger.debug(f"Message {message_id} marqué comme lu")
        except Exception as e:
            logger.error(f"Erreur marquage message: {e}")
            emit('error', {'message': 'Erreur serveur'}, namespace='/expert')

    @socketio.on('get_active_sessions', namespace='/expert')
    def handle_get_active_sessions(data):
        user_id = data.get('user_id')
        if not user_id or not user_id.isdigit():
            logger.error(f"get_active_sessions refusé - user_id: {user_id}")
            emit('error', {'message': 'User ID invalide'}, namespace='/expert')
            return

        sessions = ExpertSession.query.filter(
            ExpertSession.status == 'active',
            (ExpertSession.user_id == user_id) | (ExpertSession.expert_id == user_id)
        ).all()
        session_data = [{
            'session_id': s.id,
            'farmer_username': User.query.get(s.user_id).username,
            'expert_username': User.query.get(s.expert_id).username,
            'request_id': s.public_request_id
        } for s in sessions]
        emit('active_sessions', {'sessions': session_data}, namespace='/expert')
        logger.debug(f"Sessions actives envoyées à user {user_id}: {len(sessions)}")

    # Scheduler pour nettoyer les commentaires et sessions
    def clean_old_comments():
        with app.app_context():
            two_hours_ago = datetime.utcnow() - timedelta(hours=2)
            old_comments = LiveComment.query.filter(LiveComment.created_at < two_hours_ago).all()
            for comment in old_comments:
                db.session.delete(comment)
            db.session.commit()
            logger.debug(f"Supprimé {len(old_comments)} commentaires anciens.")

    def clean_old_sessions():
        with app.app_context():
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            old_sessions = ExpertSession.query.filter(
                ExpertSession.status == 'completed',
                ExpertSession.created_at < one_day_ago
            ).all()
            for session in old_sessions:
                db.session.delete(session)
            db.session.commit()
            logger.debug(f"Supprimé {len(old_sessions)} sessions anciennes.")

    try:
        scheduler.add_job(clean_old_comments, 'interval', minutes=10)
        scheduler.add_job(clean_old_sessions, 'interval', hours=1)
        scheduler.start()
        logger.debug("Scheduler démarré.")
    except Exception as e:
        logger.error(f"Erreur scheduler : {e}")
        return None

    def shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown()
            logger.debug("Scheduler arrêté.")
    atexit.register(shutdown_scheduler)

    # Enregistrement des namespaces API
    def register_namespaces():
        from api.auth import ns as auth_ns
        from api.plant import ns as plant_ns
        from api.chat import ns as chat_ns
        from api.live import ns as live_ns
        from api.expert import ns as expert_ns
        from api.weather import ns as weather_ns
        from api.admin import ns as admin_ns

        api.add_namespace(auth_ns, path="/auth")
        api.add_namespace(plant_ns, path="/plant")
        api.add_namespace(chat_ns, path="/chat")
        api.add_namespace(live_ns, path="/live")
        api.add_namespace(expert_ns, path="/expert")
        api.add_namespace(weather_ns, path="/weather")
        api.add_namespace(admin_ns, path="/admin")

    register_namespaces()
    logger.debug("create_app terminé.")
    return app

app = create_app()
if app is None:
    logger.error("Échec création application Flask")
    exit(1)

if __name__ == "__main__":
    logger.debug("Démarrage serveur SocketIO")
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Erreur démarrage serveur : {e}")
        raise