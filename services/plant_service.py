import os
from datetime import datetime
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.preprocessing import image
import numpy as np
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Charger le modèle MobileNetV2 (à fine-tuner pour les maladies des plantes)
model = MobileNetV2(weights='imagenet')  # Remplacez par un modèle fine-tuné si disponible

def detect_plant_disease(image_file, user_id):
    """
    Détecte une maladie des plantes à partir d'un fichier image uploadé et renvoie la maladie, la recommandation et le chemin de l'image.
    """
    try:
        # Générer un chemin pour sauvegarder l'image
        image_path = f"uploads/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(image_file.filename)[1]}"
        os.makedirs("uploads", exist_ok=True)

        # Sauvegarder le fichier uploadé
        image_file.save(image_path)

        # Prétraiter l'image pour MobileNetV2
        img = image.load_img(image_path, target_size=(224, 224))  # MobileNetV2 attend 224x224
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # Faire une prédiction
        predictions = model.predict(img_array)

        # Simuler une détection (à remplacer par un modèle fine-tuné)
        disease = "Mildiou"  # Exemple (remplacez par une logique basée sur predictions)
        recommendation = "Utiliser un fongicide à base de cuivre."

        # Enregistrer dans la base de données
        from models.plant_disease import PlantDisease
        from app import db
        plant = PlantDisease(user_id=user_id, image_path=image_path, disease=disease, recommendation=recommendation)
        db.session.add(plant)
        db.session.commit()

        logger.debug(f"Maladie détectée : {disease}, Recommandation : {recommendation}, Chemin : {image_path}")
        return {
            "disease": disease,
            "recommendation": recommendation,
            "image_path": image_path
        }

    except Exception as e:
        logger.error(f"Erreur lors de la détection de la maladie : {e}")
        raise