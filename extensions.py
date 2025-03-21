from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_socketio import SocketIO

# Initialiser les extensions
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO()