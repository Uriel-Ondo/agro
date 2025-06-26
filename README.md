```markdown
# Configuration et Lancement du Projet

## Étape 1 : Créer un fichier `.env`
Créer un fichier `.env` dans le répertoire racine et y ajouter le contenu suivant :

```
SECRET_KEY=Votre_cle_secrete
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=mysql+mysqlconnector://user:password@localhost/agri
WEATHER_API_KEY=cle_api_meteo
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=Ton_mail
MAIL_PASSWORD=mot_de_passe
MAIL_DEFAULT_SENDER=mail_par_defaut
```

## Étape 2 : Créer la base de données
Dans votre terminal, exécutez la commande suivante pour créer la base de données :

```sql
create database agri;
```

### Alternative avec Flask-Migrate (Recommandé)
Pour gérer les migrations proprement, utilisez Flask-Migrate. Exécutez les commandes suivantes :

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Étape 3 : Créer l'environnement virtuel et installer les dépendances
1. Créez un environnement virtuel :
   ```bash
   py.exe -m venv venv
   ```

2. Activez l'environnement virtuel :
   ```bash
   venv\Scripts\activate
   ```

3. Installez les dépendances listées dans le fichier `requirements.txt` :
   ```bash
   pip install -r requirements.txt
   ```

4. Installez **ollama** et **gemma:2b**.

## Étape 4 : Lancer le serveur
1. **Ouvrir un premier terminal** et exécuter :
   ```bash
   ollama run
   ```

2. **Ouvrir un deuxième terminal** et exécuter :
   ```bash
   ollama run gemma:2b
   ```

3. **Lancer le serveur principal** en exécutant :
   ```bash
   py.exe app.py
   ```

Le serveur est maintenant lancé et prêt à être utilisé !
```