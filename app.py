import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, request
from flask_restx import Api
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from config import Config
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from flask_socketio import join_room, leave_room
import os
import atexit
from extensions import db

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialisation globale des extensions
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO(async_mode='eventlet', cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.debug("Application Flask créée avec succès")

    if not app.config.get('JWT_SECRET_KEY'):
        logger.error("JWT_SECRET_KEY non défini dans la configuration !")
        raise ValueError("JWT_SECRET_KEY doit être défini dans Config")

    socketio.init_app(app)
    logger.debug("SocketIO initialisé avec l'application")

    try:
        db.init_app(app)
        logger.debug("SQLAlchemy initialisé")
        migrate.init_app(app, db)
        logger.debug("Migrate initialisé")
        jwt.init_app(app)
        logger.debug("JWTManager initialisé")
        mail = Mail(app) if app.config.get('MAIL_SERVER') else None
        logger.debug("Mail initialisé" if mail else "Mail non configuré")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des extensions : {e}")
        return None

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

    scheduler = BackgroundScheduler()

    from models.user import User
    from models.plant_disease import PlantDisease
    from models.chat_message import ChatMessage
    from models.live_comment import LiveComment
    from models.expert_session import ExpertSession, SessionMessage
    from models.public_request import PublicRequest

    CORS(app, resources={r"/*": {
        "origins": ["http://localhost:8100"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "max_age": 86400
    }})
    logger.debug("CORS configuré pour les requêtes HTTP")

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
                admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
                admin_username = os.getenv("ADMIN_USERNAME", "admin")
                admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
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
                else:
                    logger.debug("Utilisateur admin existe déjà, aucune création nécessaire.")
            create_admin_user()

            import requests
            try:
                response = requests.get("http://localhost:11434/", timeout=2)
                if response.status_code == 200:
                    logger.debug("Ollama est en marche et accessible localement.")
                else:
                    logger.warning(f"Ollama renvoie un statut inattendu : {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Ollama n'est pas accessible, continuation sans : {e}")
        except Exception as e:
            logger.error(f"Erreur dans le contexte d'application : {e}")
            return None

    @app.route('/live_comments')
    def live_comments():
        return send_from_directory('static', 'live_comments.html')

    @app.route('/expert_chat')
    def expert_chat():
        return send_from_directory('static', 'expert_chat.html')

    @socketio.on('connect', namespace='/live')
    def handle_live_connect(auth=None):
        logger.debug("Client connecté au namespace /live")

    @socketio.on('disconnect', namespace='/live')
    def handle_live_disconnect():
        logger.debug("Client déconnecté du namespace /live")

    @socketio.on('connect', namespace='/expert')
    def handle_expert_connect(auth=None):
        user_id = request.args.get('user_id')
        logger.debug(f"Connexion WebSocket /expert - user_id: {user_id}")
        if not user_id or user_id == "undefined" or not user_id.isdigit():
            logger.warning(f"Connexion refusée - user_id invalide: {user_id}")
            return False
        user = db.session.get(User, int(user_id))
        if user:
            user.set_online(True)
            join_room(f"user_{user_id}")
            logger.debug(f"Utilisateur {user_id} connecté - room: user_{user_id}")
        else:
            logger.warning(f"Utilisateur non trouvé - user_id: {user_id}")
            return False

    @socketio.on('join_session', namespace='/expert')
    def handle_join_session(data):
        user_id = request.args.get('user_id')
        session_id = data.get('session_id')
        if not user_id or not user_id.isdigit() or not session_id:
            logger.warning(f"Join session refusé - user_id: {user_id}, session_id: {session_id}")
            return
        user = db.session.get(User, int(user_id))
        if user:
            session = ExpertSession.query.get(session_id)
            if session and user_id in [str(session.user_id), str(session.expert_id)]:
                join_room(f"session_{session_id}")
                logger.debug(f"Utilisateur {user_id} a rejoint la room session_{session_id}")
            else:
                logger.warning(f"Session {session_id} invalide ou accès refusé pour user_id: {user_id}")

    @socketio.on('disconnect', namespace='/expert')
    def handle_expert_disconnect():
        user_id = request.args.get('user_id')
        if user_id and user_id.isdigit():
            user = db.session.get(User, int(user_id))
            if user:
                user.set_online(False)
                leave_room(f"user_{user_id}")
                logger.debug(f"Utilisateur {user_id} déconnecté du namespace /expert et marqué hors ligne.")
            else:
                logger.warning(f"Tentative de déconnexion avec un user_id invalide : {user_id}")

    @socketio.on('mark_message_read', namespace='/expert')
    def handle_mark_message_read(data):
        user_id = request.args.get('user_id')
        if not user_id or not user_id.isdigit():
            logger.warning(f"Marquage de message refusé - user_id invalide: {user_id}")
            return
        try:
            from services.expert_service import mark_message_as_read
            mark_message_as_read(data['session_id'], data['message_id'], int(user_id))
            logger.debug(f"Événement mark_message_read traité - session_id: {data['session_id']}, message_id: {data['message_id']}, user_id: {user_id}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de mark_message_read: {e}")

    def clean_old_comments():
        with app.app_context():
            two_hours_ago = datetime.utcnow() - timedelta(hours=2)
            old_comments = LiveComment.query.filter(LiveComment.created_at < two_hours_ago).all()
            for comment in old_comments:
                db.session.delete(comment)
            db.session.commit()
            logger.debug(f"Supprimé {len(old_comments)} commentaires de plus de 2 heures.")

    try:
        scheduler.add_job(clean_old_comments, 'interval', minutes=10)
        scheduler.start()
        logger.debug("Scheduler démarré avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du scheduler : {e}")
        return None

    def shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown()
            logger.debug("Scheduler arrêté avec succès.")
    atexit.register(shutdown_scheduler)

    # Ajouter les namespaces après toute l'initialisation
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
    logger.debug("create_app terminé avec succès")
    return app

app = create_app()
if app is None:
    logger.error("Échec de la création de l'application Flask")
    exit(1)

if __name__ == "__main__":
    logger.debug("Démarrage du serveur avec SocketIO")
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Erreur au démarrage du serveur : {e}")
        raise