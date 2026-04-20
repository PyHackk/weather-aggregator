# app/services/weather_service.py
"""
Core weather service - orchestrates caching and API calls.
"""
from datetime import datetime, timedelta
from app.models import db, Location, WeatherHistory
from app.services.cache_service import CacheService
from app.services.api_clients import OpenWeatherClient, WeatherAPIClient


class WeatherService:
    """Main weather business logic."""
    
    @staticmethod
    def get_weather(city: str, source: str = 'openweather') -> dict:
        """
        Get weather with caching.
        Checks cache first, falls back to API if needed.
        """
        cache_key = f"weather:{source}:{city.lower()}"
        
        # Try cache first
        cached = CacheService.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return cached
        
        # Fetch from API
        client = OpenWeatherClient if source == 'openweather' else WeatherAPIClient
        weather_data = client.get_weather(city)
        
        # Cache it
        CacheService.set(cache_key, weather_data)
        
        # Save to history
        WeatherService._save_to_history(weather_data)
        
        weather_data['from_cache'] = False
        return weather_data
    
    @staticmethod
    def compare_sources(city: str) -> dict:
        """Get weather from both sources for comparison."""
        try:
            openweather = WeatherService.get_weather(city, 'openweather')
        except Exception as e:
            openweather = {'error': str(e)}
        
        try:
            weatherapi = WeatherService.get_weather(city, 'weatherapi')
        except Exception as e:
            weatherapi = {'error': str(e)}
        
        return {
            'city': city,
            'openweather': openweather,
            'weatherapi': weatherapi
        }
    
    @staticmethod
    def _save_to_history(weather_data: dict):
        """Save weather snapshot to database."""
        # Find or create location
        location = Location.query.filter_by(
            city=weather_data['city'],
            country=weather_data['country']
        ).first()
        
        if not location:
            location = Location(
                city=weather_data['city'],
                country=weather_data['country'],
                latitude=weather_data['latitude'],
                longitude=weather_data['longitude']
            )
            db.session.add(location)
            db.session.flush()
        
        # Create history entry
        history = WeatherHistory(
            location_id=location.id,
            temperature=weather_data['temperature'],
            feels_like=weather_data['feels_like'],
            humidity=weather_data['humidity'],
            pressure=weather_data['pressure'],
            wind_speed=weather_data['wind_speed'],
            description=weather_data['description'],
            icon=weather_data['icon'],
            source=weather_data['source']
        )
        db.session.add(history)
        db.session.commit()
    
    @staticmethod
    def get_history(city: str, days: int = 7) -> list:
        """Get historical weather data."""
        location = Location.query.filter_by(city=city).first()
        if not location:
            return []
        
        since = datetime.utcnow() - timedelta(days=days)
        history = location.history.filter(
            WeatherHistory.recorded_at >= since
        ).order_by(WeatherHistory.recorded_at.desc()).all()
        
        return [h.to_dict() for h in history]