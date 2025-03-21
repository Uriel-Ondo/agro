from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.plant_service import detect_plant_disease
from flask import request
import os 

ns = Namespace("plant", description="Détection des maladies des plantes")

# Modèle pour la réponse
response_model = ns.model("PlantDetectionResponse", {
    "disease": fields.String(description="Maladie détectée"),
    "recommendation": fields.String(description="Recommandation pour traiter la maladie"),
    "image_path": fields.String(description="Chemin de l'image enregistrée sur le serveur")
})

# Parser pour gérer le fichier uploadé
parser = ns.parser()
parser.add_argument('image', type='file', location='files', required=True, help="Fichier image (jpg, png, etc.)")

@ns.route("/detect")
class PlantDetect(Resource):
    @jwt_required()
    @ns.expect(parser)  # Attendre un fichier uploadé via multipart/form-data
    @ns.marshal_with(response_model, code=200)  # Formater la réponse
    def post(self):
        """
        Soumet une image (uploadée ou prise en photo) pour détecter une maladie des plantes.
        """
        user_id = get_jwt_identity()

        # Vérifier si un fichier image est présent dans la requête
        if 'image' not in request.files:
            ns.abort(400, "Aucun fichier image n'a été soumis.")
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            ns.abort(400, "Aucun fichier sélectionné.")

        # Vérifier que le fichier est une image valide
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        if not '.' in image_file.filename or os.path.splitext(image_file.filename)[1].lower() not in allowed_extensions:
            ns.abort(400, "Format d'image invalide. Utilisez JPG ou PNG.")

        # Passer le fichier brut à la fonction de détection
        result = detect_plant_disease(image_file, user_id)
        return result, 200