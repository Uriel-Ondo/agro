import os
from datetime import datetime
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Chemin vers le modèle fine-tuné
MODEL_PATH = "models/mobilenetv2_color.h5"

# Charger le modèle fine-tuné
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.debug(f"Modèle fine-tuné chargé avec succès depuis {MODEL_PATH}")
except Exception as e:
    logger.error(f"Erreur lors du chargement du modèle : {e}")
    raise

# Liste des classes fournies
CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy"
]

# Dictionnaire de recommandations pour chaque classe
RECOMMENDATIONS = {
    "Apple___Apple_scab": "Appliquez un fongicide comme le captane et taillez les branches infectées.",
    "Apple___Black_rot": "Retirez les fruits et feuilles infectés, utilisez un fongicide à base de soufre.",
    "Apple___Cedar_apple_rust": "Utilisez un fongicide comme le myclobutanil et éliminez les genévriers proches.",
    "Apple___healthy": "Aucune action nécessaire, continuez les bonnes pratiques agricoles.",
    "Blueberry___healthy": "Aucune action nécessaire, surveillez régulièrement les plants.",
    "Cherry_(including_sour)___Powdery_mildew": "Appliquez un fongicide comme le soufre et améliorez la circulation d'air.",
    "Cherry_(including_sour)___healthy": "Continuez les soins habituels, pas de traitement requis.",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Utilisez un fongicide comme l'azoxystrobine et espacez les plants.",
    "Corn_(maize)___Common_rust": "Appliquez un fongicide comme le propiconazole dès les premiers signes.",
    "Corn_(maize)___Northern_Leaf_Blight": "Utilisez un fongicide comme le mancozèbe et pratiquez la rotation des cultures.",
    "Corn_(maize)___healthy": "Aucune intervention nécessaire, surveillez l'humidité.",
    "Grape___Black_rot": "Retirez les baies infectées et appliquez un fongicide comme le captane.",
    "Grape___Esca_(Black_Measles)": "Taillez les parties infectées et surveillez l'état général des vignes.",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Utilisez un fongicide et améliorez la ventilation des vignes.",
    "Grape___healthy": "Aucune action nécessaire, maintenez une bonne gestion des vignes.",
    "Orange___Haunglongbing_(Citrus_greening)": "Éliminez les arbres infectés et contrôlez les psylles avec un insecticide.",
    "Peach___Bacterial_spot": "Appliquez un traitement à base de cuivre et évitez l'excès d'humidité.",
    "Peach___healthy": "Continuez les soins réguliers, pas de traitement requis.",
    "Pepper,_bell___Bacterial_spot": "Utilisez un bactéricide à base de cuivre et retirez les feuilles infectées.",
    "Pepper,_bell___healthy": "Aucune action nécessaire, surveillez les conditions climatiques.",
    "Potato___Early_blight": "Appliquez un fongicide comme le chlorothalonil et pratiquez la rotation des cultures.",
    "Potato___Late_blight": "Utilisez un fongicide à base de cuivre et détruisez les plants infectés.",
    "Potato___healthy": "Aucune intervention nécessaire, continuez les bonnes pratiques.",
    "Raspberry___healthy": "Aucune action nécessaire, maintenez une bonne hygiène des plants.",
    "Soybean___healthy": "Aucune action nécessaire, surveillez les ravageurs.",
    "Squash___Powdery_mildew": "Appliquez un fongicide comme le soufre et espacez les plants.",
    "Strawberry___Leaf_scorch": "Retirez les feuilles infectées et appliquez un fongicide si nécessaire.",
    "Strawberry___healthy": "Aucune action nécessaire, continuez les soins habituels.",
    "Tomato___Bacterial_spot": "Utilisez un bactéricide à base de cuivre et évitez les éclaboussures d'eau.",
    "Tomato___Early_blight": "Appliquez un fongicide comme le mancozèbe et retirez les feuilles infectées.",
    "Tomato___Late_blight": "Utilisez un fongicide systémique et détruisez les plants infectés.",
    "Tomato___Leaf_Mold": "Améliorez la ventilation et appliquez un fongicide comme le chlorothalonil.",
    "Tomato___Septoria_leaf_spot": "Retirez les feuilles infectées et utilisez un fongicide.",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Utilisez un acaricide et augmentez l'humidité.",
    "Tomato___Target_Spot": "Appliquez un fongicide et améliorez la circulation d'air.",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Utilisez des pièges collants et éliminez les plants infectés.",
    "Tomato___Tomato_mosaic_virus": "Détruisez les plants infectés et désinfectez les outils.",
    "Tomato___healthy": "Aucune action nécessaire, continuez les bonnes pratiques."
}

def detect_plant_disease(image_file, user_id):
    """
    Détecte une maladie des plantes à partir d'un fichier image uploadé avec le modèle fine-tuné.
    """
    try:
        # Générer un chemin pour sauvegarder l'image
        image_path = f"uploads/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(image_file.filename)[1]}"
        os.makedirs("uploads", exist_ok=True)

        # Sauvegarder le fichier uploadé
        image_file.save(image_path)

        # Prétraiter l'image pour le modèle (MobileNetV2 attend 224x224)
        img = image.load_img(image_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

        # Faire une prédiction avec le modèle fine-tuné
        predictions = model.predict(img_array)
        predicted_class_idx = np.argmax(predictions[0])  # Indice de la classe avec la plus haute probabilité
        confidence = predictions[0][predicted_class_idx]  # Score de confiance

        # Récupérer la maladie prédite
        disease = CLASSES[predicted_class_idx] if predicted_class_idx < len(CLASSES) else "Inconnue"
        recommendation = RECOMMENDATIONS.get(disease, "Aucune recommandation disponible.")

        # Enregistrer dans la base de données
        from models.plant_disease import PlantDisease
        from extensions import db
        plant = PlantDisease(
            user_id=user_id,
            image_path=image_path,
            disease=disease,
            recommendation=recommendation
        )
        db.session.add(plant)
        db.session.commit()

        logger.debug(f"Maladie détectée : {disease} (confiance: {confidence:.2f}), Recommandation : {recommendation}, Chemin : {image_path}")
        return {
            "disease": disease,
            "recommendation": recommendation,
            "image_path": image_path,
            "confidence": float(confidence)  # Optionnel : renvoyer la confiance
        }

    except Exception as e:
        logger.error(f"Erreur lors de la détection de la maladie : {e}")
        raise