# api/weather.py
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.weather_service import get_local_weather, get_hourly_forecast
from models.user import User
from extensions import db
import logging

ns = Namespace("weather", description="Météo locale et gestion des villes favorites")

# Configuration de la journalisation
logger = logging.getLogger(__name__)

weather_model = ns.model("Weather", {
    "city": fields.String(description="Nom de la ville"),
    "country": fields.String(description="Code du pays"),
    "temperature": fields.Float(description="Température en °C"),
    "description": fields.String(description="Description de la météo"),
    "humidity": fields.Integer(description="Humidité en %"),
    "wind_speed": fields.Float(description="Vitesse du vent en m/s"),
    "sunrise": fields.String(description="Heure du lever du soleil"),
    "sunset": fields.String(description="Heure du coucher du soleil"),
    "error": fields.String(description="Message d'erreur, si applicable")
})

forecast_model = ns.model("Forecast", {
    "time": fields.String(description="Heure de la prévision"),
    "temperature": fields.Float(description="Température en °C"),
    "description": fields.String(description="Description de la météo")
})

favorite_city_model = ns.model("FavoriteCity", {
    "city": fields.String(required=True, description="Nom de la ville à ajouter ou supprimer")
})

@ns.route("/local")
class Weather(Resource):
    @ns.doc("Récupérer la météo locale", params={
        "city": "Nom de la ville (ex: Paris)",
        "lat": "Latitude (ex: 48.8566)",
        "lon": "Longitude (ex: 2.3522)"
    })
    @ns.marshal_with(weather_model)
    def get(self):
        city = request.args.get('city')
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        try:
            weather = get_local_weather(city=city, lat=lat, lon=lon)
            return weather, 200 if "temperature" in weather else weather.get("status_code", 500)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la météo locale : {str(e)}")
            return {"error": "Erreur serveur lors de la récupération de la météo"}, 500

@ns.route("/forecast")
class Forecast(Resource):
    @ns.doc("Récupérer les prévisions horaires", params={
        "city": "Nom de la ville (ex: Paris)",
        "lat": "Latitude (ex: 48.8566)",
        "lon": "Longitude (ex: 2.3522)"
    })
    @ns.marshal_list_with(forecast_model)
    def get(self):
        city = request.args.get('city')
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        try:
            forecast = get_hourly_forecast(city=city, lat=lat, lon=lon)
            return forecast, 200 if isinstance(forecast, list) else forecast.get("status_code", 500)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prévisions : {str(e)}")
            return {"error": "Erreur serveur lors de la récupération des prévisions"}, 500
@ns.route("/favorites")
class FavoriteCities(Resource):
    @ns.doc("Récupérer les villes favorites de l'utilisateur")
    @jwt_required()
    @ns.marshal_with(favorite_city_model, as_list=True)
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Tentative de récupération des favoris pour un utilisateur non trouvé : {user_id}")
            return {"message": "Utilisateur non trouvé"}, 404
        try:
            favorite_cities = user.get_favorite_cities() or []
            return {"favorite_cities": favorite_cities}, 200
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des villes favorites pour l'utilisateur {user_id} : {str(e)}")
            return {"message": "Erreur serveur lors de la récupération des favoris"}, 500

    @ns.doc("Ajouter une ville favorite")
    @ns.expect(favorite_city_model)
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Tentative d'ajout d'une ville favorite pour un utilisateur non trouvé : {user_id}")
            return {"message": "Utilisateur non trouvé"}, 404
        
        data = request.get_json()
        city = data.get("city")
        if not city:
            logger.warning(f"Tentative d'ajout d'une ville favorite sans nom de ville pour l'utilisateur {user_id}")
            return {"message": "Le nom de la ville est requis"}, 400
        
        try:
            favorite_cities = user.get_favorite_cities() or []
            if city not in favorite_cities:
                favorite_cities.append(city)
                user.set_favorite_cities(favorite_cities)
                db.session.commit()  # N'oubliez pas de valider les changements
                logger.info(f"Ville {city} ajoutée aux favoris de l'utilisateur {user_id}")
                return {"message": f"{city} ajouté aux favoris"}, 201
            logger.debug(f"Ville {city} déjà dans les favoris de l'utilisateur {user_id}")
            return {"message": f"{city} est déjà dans les favoris"}, 200
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la ville {city} aux favoris de l'utilisateur {user_id} : {str(e)}")
            db.session.rollback()
            return {"message": "Erreur serveur lors de l'ajout de la ville"}, 500

@ns.route("/favorites/<string:city>")
class FavoriteCity(Resource):
    @ns.doc("Supprimer une ville favorite")
    @jwt_required()
    def delete(self, city):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Tentative de suppression d'une ville favorite pour un utilisateur non trouvé : {user_id}")
            return {"message": "Utilisateur non trouvé"}, 404
        
        try:
            favorite_cities = user.get_favorite_cities()
            if city in favorite_cities:
                favorite_cities.remove(city)
                user.set_favorite_cities(favorite_cities)
                logger.info(f"Ville {city} supprimée des favoris de l'utilisateur {user_id}")
                return {"message": f"{city} supprimé des favoris"}, 200
            logger.debug(f"Ville {city} non trouvée dans les favoris de l'utilisateur {user_id}")
            return {"message": f"{city} n'est pas dans les favoris"}, 404
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la ville {city} des favoris de l'utilisateur {user_id} : {str(e)}")
            db.session.rollback()  # Annuler les changements en cas d'erreur
            return {"message": "Erreur serveur lors de la suppression de la ville"}, 500