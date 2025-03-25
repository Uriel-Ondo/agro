# models/plant_disease.py
from extensions import db  # Changé de "from app import db" à "from extensions import db"

class PlantDisease(db.Model):
    __tablename__ = 'plant_disease'  # Ajouté pour définir explicitement le nom de la table
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    disease = db.Column(db.String(100))
    recommendation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        """Représentation de l'objet pour le débogage."""
        return f"<PlantDisease {self.id}, Disease: {self.disease}, User: {self.user_id}>"