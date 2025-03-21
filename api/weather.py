from flask_restx import Namespace, Resource, fields
from services.weather_service import get_local_weather
from flask import request

ns = Namespace("weather", description="Météo locale")

weather_model = ns.model("Weather", {
    "temperature": fields.Float(description="Température en °C"),
    "description": fields.String(description="Description de la météo"),
    "humidity": fields.Integer(description="Humidité en %"),
    "wind_speed": fields.Float(description="Vitesse du vent en m/s"),
    "error": fields.String(description="Message d'erreur, si applicable")
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
        weather = get_local_weather(city=city, lat=lat, lon=lon)
        return weather, 200 if "temperature" in weather else weather.get("status_code", 500)