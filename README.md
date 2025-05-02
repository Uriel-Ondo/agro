1-Creer le .env et y ajouter le contenu suivant

# Sécurité
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key

# Base de données
DATABASE_URL=mysql+mysqlconnector://user:password@localhost/agri_database

# API météo (exemple : OpenWeatherMap)
WEATHER_API_KEY=your-weather-api-key

# Configuration de l'envoi d'email
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=no-reply@example.com

# Admin par défaut
ADMIN_EMAIL=admin@example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=adminpass123

# Api cohere
COHERE_API_KEY=your-api-key


2- creer la base de donnees
create database agri;

-Alternative avec Flask-Migrate (Recommandé) Si tu veux gérer les migrations proprement, utilise Flask-Migrate :

flask db init 
flask db migrate -m "Initial migration" flask db upgrade

3- creer l'environement virtuel et installer les dependances

py.exe -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

-lancer le serveur
<<<<<<< Updated upstream
py.exe app.py
=======
py.exe app.py



>>>>>>> Stashed changes
