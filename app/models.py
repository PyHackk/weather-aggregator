# app/models.py
"""
Database models for weather tracking.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Location(db.Model):
    """
    User's saved locations for quick weather access.
    """
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    country = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    history = db.relationship('WeatherHistory', backref='location', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'city': self.city,
            'country': self.country,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at.isoformat()
        }


class WeatherHistory(db.Model):
    """
    Historical weather snapshots.
    Stores daily snapshots for trend analysis.
    """
    __tablename__ = 'weather_history'
    
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    
    # Weather data
    temperature = db.Column(db.Float, nullable=False)
    feels_like = db.Column(db.Float)
    humidity = db.Column(db.Integer)
    pressure = db.Column(db.Integer)
    wind_speed = db.Column(db.Float)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(10))
    
    # Metadata
    source = db.Column(db.String(50))  # 'openweather' or 'weatherapi'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'feels_like': self.feels_like,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'wind_speed': self.wind_speed,
            'description': self.description,
            'icon': self.icon,
            'source': self.source,
            'recorded_at': self.recorded_at.isoformat()
        }