
import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, request
from flask_restx import Api
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config
from extensions import db, jwt, mail, socketio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
from flask_socketio import join_room, leave_room
import os

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialisation du scheduler
scheduler = BackgroundScheduler()

# Initialisation de db et migrate au niveau global
db = db
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configurer CORS pour les requêtes HTTP
    CORS(app, resources={r"/*": {
        "origins": ["http://localhost:8100"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "max_age": 86400
    }}, debug=True)
    logger.debug("CORS configuré pour les requêtes HTTP")

    # Initialisation des extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")
    migrate.init_app(app, db)
    logger.debug("SocketIO et Migrate initialisés avec l'application Flask")

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

    # Imports des modèles déplacés ici pour éviter les imports circulaires
    with app.app_context():
        from models.user import User
        from models.plant_disease import PlantDisease
        from models.chat_message import ChatMessage
        from models.live_comment import LiveComment
        from models.expert_session import ExpertSession
        from models.public_request import PublicRequest

        db.create_all()
        logger.debug("Tables créées avec succès dans la base de données.")

        # Création de l'utilisateur admin s'il n'existe pas
        def create_admin_user():
            admin_email = os.getenv("ADMIN_EMAIL")
            admin_username = os.getenv("ADMIN_USERNAME")
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not User.query.filter_by(email=admin_email).first():
                admin_user = User(
                    username=admin_username,
                    email=admin_email,
                    role="expert",  # Ou "farmer" selon vos besoins
                    is_admin=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                logger.info(f"Utilisateur admin créé avec succès : {admin_username}")
            else:
                logger.debug("Utilisateur admin existe déjà, aucune création nécessaire.")

        try:
            create_admin_user()
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur admin : {str(e)}")
            db.session.rollback()

        # Vérification de la disponibilité d'Ollama
        try:
            import requests
            response = requests.get("http://localhost:11434/")
            if response.status_code == 200:
                logger.debug("Ollama est en marche et accessible localement.")
            else:
                logger.error(f"Ollama renvoie un statut inattendu : {response.status_code}")
                raise Exception("Ollama n'est pas accessible.")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'Ollama : {e}")
            raise

    # Imports des namespaces après l'initialisation de l'application
    from api import auth, plant, chat, live, expert, weather, admin
    api.add_namespace(auth.ns, path="/auth")
    api.add_namespace(plant.ns, path="/plant")
    api.add_namespace(chat.ns, path="/chat")
    api.add_namespace(live.ns, path="/live")
    api.add_namespace(expert.ns, path="/expert")
    api.add_namespace(weather.ns, path="/weather")
    api.add_namespace(admin.ns, path="/admin")

    # Routes statiques
    @app.route('/live_comments')
    def live_comments():
        return send_from_directory('static', 'live_comments.html')

    @app.route('/expert_chat')
    def expert_chat():
        return send_from_directory('static', 'expert_chat.html')

    # Gestion des événements WebSocket pour /live
    @socketio.on('connect', namespace='/live')
    def handle_live_connect():
        logger.debug("Client connecté au namespace /live")

    @socketio.on('disconnect', namespace='/live')
    def handle_live_disconnect():
        logger.debug("Client déconnecté du namespace /live")

    # Gestion des événements WebSocket pour /expert
    @socketio.on('connect', namespace='/expert')
    def handle_expert_connect():
        user_id = request.args.get('user_id')
        if user_id:
            from models.user import User
            user = User.query.get(user_id)
            if user:
                user.set_online(True)
                join_room(f"user_{user_id}")
                logger.debug(f"Utilisateur {user_id} connecté au namespace /expert et marqué en ligne.")
            else:
                logger.warning(f"Tentative de connexion avec un user_id invalide : {user_id}")

    @socketio.on('disconnect', namespace='/expert')
    def handle_expert_disconnect():
        user_id = request.args.get('user_id')
        if user_id:
            from models.user import User
            user = User.query.get(user_id)
            if user:
                user.set_online(False)
                leave_room(f"user_{user_id}")
                logger.debug(f"Utilisateur {user_id} déconnecté du namespace /expert et marqué hors ligne.")
            else:
                logger.warning(f"Tentative de déconnexion avec un user_id invalide : {user_id}")

    # Nettoyage des anciens commentaires
    def clean_old_comments():
        with app.app_context():
            from models.live_comment import LiveComment
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
        raise

    import atexit
    def shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown()
            logger.debug("Scheduler arrêté avec succès.")
    atexit.register(shutdown_scheduler)

    return app

# Créer l'application pour la CLI Flask et le démarrage
app = create_app()

if __name__ == "__main__":
    logger.debug("Démarrage du serveur avec SocketIO")
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Erreur au démarrage du serveur : {e}")
        raise