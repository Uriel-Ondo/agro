import requests
from config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_local_weather(city=None, lat=None, lon=None):
    api_key = Config.WEATHER_API_KEY
    if not api_key:
        return {"error": "Clé d'API météo non configurée"}, 500

    logger.debug(f"Paramètres reçus - city: {city}, lat: {lat}, lon: {lon}")

    if lat and lon:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    elif city:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    else:
        return {"error": "Ville ou coordonnées requises"}, 400

    logger.debug(f"URL de l’API appelée : {url}")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"Réponse API : {data}")
        return {
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"]
        }
    return {"error": "Impossible de récupérer la météo", "status_code": response.status_code}, 502