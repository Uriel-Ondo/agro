1-Creer le .env et y ajouter le contenu suivant

SECRET_KEY=Votre_cle_secrete
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=mysql+mysqlconnector://user:password@localhost/agri
WEATHER_API_KEY=cle_api_meteo
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=Ton_mail
MAIL_PASSWORD=mot_de_passe
MAIL_DEFAULT_SENDER=mail_par_defauf

2- creer la base de donnees
create database agri;

-Alternative avec Flask-Migrate (Recommandé) Si tu veux gérer les migrations proprement, utilise Flask-Migrate :

flask db init 
flask db migrate -m "Initial migration" flask db upgrade

3- creer l'environement virtuel et installer les dependances

py.exe -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

-installer ollama et gemma:2b

4- Lancer le serveur
-ouvrir un terminal
ollama run

-ouvrir un autre terminal
ollama run gemma:2b

-lancer le serveur
py.exe app.py