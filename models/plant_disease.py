from extensions import db

class PlantDisease(db.Model):
    __tablename__ = 'plant_disease'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # Changé de "user.id" à "users.id"
    image_path = db.Column(db.String(255), nullable=False)
    disease = db.Column(db.String(100))
    recommendation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<PlantDisease {self.id}, Disease: {self.disease}, User: {self.user_id}>"