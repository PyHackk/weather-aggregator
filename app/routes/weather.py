# app/routes/weather.py
"""
Weather API endpoints.
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.weather_service import WeatherService
from app.utils.rate_limiter import rate_limit
from app.models import db, Location

weather_ns = Namespace('weather', description='Weather operations')

# API Models for Swagger
weather_model = weather_ns.model('Weather', {
    'city': fields.String,
    'country': fields.String,
    'temperature': fields.Float,
    'humidity': fields.Integer,
    'description': fields.String
})


@weather_ns.route('/weather/<string:city>')
class WeatherResource(Resource):
    """Get current weather for a city."""
    
    @rate_limit
    @weather_ns.doc('get_weather')
    def get(self, city):
        """Fetch current weather (cached for 10 mins)."""
        try:
            source = request.args.get('source', 'openweather')
            weather = WeatherService.get_weather(city, source)
            return weather, 200
        except Exception as e:
            return {'error': str(e)}, 400


@weather_ns.route('/weather/compare/<string:city>')
class WeatherCompareResource(Resource):
    """Compare weather from multiple sources."""
    
    @rate_limit
    @weather_ns.doc('compare_weather')
    def get(self, city):
        """Compare OpenWeather vs WeatherAPI."""
        result = WeatherService.compare_sources(city)
        return result, 200


@weather_ns.route('/history/<string:city>')
class WeatherHistoryResource(Resource):
    """Get historical weather data."""
    
    @weather_ns.doc('get_history')
    def get(self, city):
        """Get last 7 days of weather history."""
        days = request.args.get('days', 7, type=int)
        history = WeatherService.get_history(city, days)
        return {'city': city, 'history': history}, 200


@weather_ns.route('/locations')
class LocationsResource(Resource):
    """Manage saved locations."""
    
    @weather_ns.doc('list_locations')
    def get(self):
        """Get all saved locations."""
        locations = Location.query.all()
        return [loc.to_dict() for loc in locations], 200
    
    @weather_ns.doc('create_location')
    def post(self):
        """Save a new location."""
        data = request.get_json()
        
        location = Location(
            city=data['city'],
            country=data['country'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        db.session.add(location)
        db.session.commit()
        
        return location.to_dict(), 201