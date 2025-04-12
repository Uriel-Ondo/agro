import requests
from config import Config
import logging
from datetime import datetime
import socket  # Ajout pour tester la résolution DNS

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_dns_resolution(hostname):
    try:
        ip = socket.gethostbyname(hostname)
        logger.debug(f"Résolution DNS réussie pour {hostname} : {ip}")
        return True
    except socket.gaierror as e:
        logger.error(f"Échec de la résolution DNS pour {hostname} : {e}")
        return False

def get_local_weather(city=None, lat=None, lon=None):
    # Test de résolution DNS avant la requête
    if not test_dns_resolution("api.openweathermap.org"):
        return {"error": "Échec de la résolution DNS pour api.openweathermap.org"}

    api_key = Config.WEATHER_API_KEY
    if not api_key:
        logger.error("Clé d'API météo non configurée dans Config.")
        return {"error": "Clé d'API météo non configurée"}

    if lat and lon:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    elif city:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    else:
        logger.warning("Aucune ville ou coordonnées fournies pour la requête météo.")
        return {"error": "Ville ou coordonnées requises"}

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather_data = {
                "city": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "sunrise": datetime.utcfromtimestamp(data["sys"]["sunrise"]).strftime('%H:%M'),
                "sunset": datetime.utcfromtimestamp(data["sys"]["sunset"]).strftime('%H:%M')
            }
            logger.debug(f"Données météo récupérées avec succès : {weather_data}")
            return weather_data
        else:
            logger.error(f"Erreur API OpenWeatherMap : {response.status_code} - {response.text}")
            return {"error": f"Erreur API : {response.status_code} - {response.text}"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion à l'API météo : {e}")
        return {"error": "Impossible de se connecter à l'API météo (problème réseau ou DNS)"}
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des données météo : {e}")
        return {"error": "Erreur serveur lors de la récupération des données météo"}

def get_hourly_forecast(city=None, lat=None, lon=None):
    """
    Récupère les prévisions météorologiques horaires pour une ville ou des coordonnées.
    Args:
        city (str, optional): Nom de la ville (ex: "Paris").
        lat (float, optional): Latitude.
        lon (float, optional): Longitude.
    Returns:
        list: Liste des prévisions horaires ou un dictionnaire avec une erreur.
    """
    api_key = Config.WEATHER_API_KEY
    if not api_key:
        logger.error("Clé d'API météo non configurée dans Config.")
        return {"error": "Clé d'API météo non configurée"}

    if lat and lon:
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    elif city:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    else:
        logger.warning("Aucune ville ou coordonnées fournies pour la requête de prévisions météo.")
        return {"error": "Ville ou coordonnées requises"}

    try:
        response = requests.get(url)  # Sans timeout
        if response.status_code == 200:
            data = response.json()
            hourly_forecast = []
            for forecast in data["list"][:6]:  # 6 prochaines prévisions (3h intervalle)
                hourly_forecast.append({
                    "time": datetime.fromtimestamp(forecast["dt"]).strftime('%H:%M'),
                    "temperature": forecast["main"]["temp"],
                    "description": forecast["weather"][0]["description"]
                })
            logger.debug(f"Prévisions horaires récupérées avec succès : {hourly_forecast}")
            return hourly_forecast
        else:
            logger.error(f"Erreur API OpenWeatherMap : {response.status_code} - {response.text}")
            return {"error": f"Erreur API : {response.status_code} - {response.text}"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion à l'API météo : {e}")
        return {"error": "Impossible de se connecter à l'API météo (problème réseau ou DNS)"}
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des prévisions météo : {e}")
        return {"error": "Erreur serveur lors de la récupération des prévisions météo"}