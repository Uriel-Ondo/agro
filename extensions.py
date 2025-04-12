from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_socketio import SocketIO

# Initialiser les extensions
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO(
    async_mode='eventlet',  # Utiliser eventlet comme dans app.py
    cors_allowed_origins=["http://192.168.1.90:8100"],  # Autoriser les origines CORS spécifiques
    logger=True,  # Activer les logs pour le débogage
    engineio_logger=True  # Activer les logs pour engineio
)