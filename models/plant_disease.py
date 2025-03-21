from app import db

class PlantDisease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    disease = db.Column(db.String(100))
    recommendation = db.Column(db.Text)  
    created_at = db.Column(db.DateTime, default=db.func.now())