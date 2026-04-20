# app/services/api_clients.py
"""
External weather API clients.
"""
import requests
from flask import current_app


class OpenWeatherClient:
    """OpenWeatherMap API client."""
    
    @staticmethod
    def get_weather(city: str) -> dict:
        """Fetch current weather from OpenWeather."""
        url = f"{current_app.config['OPENWEATHER_BASE_URL']}/weather"
        params = {
            'q': city,
            'appid': current_app.config['OPENWEATHER_API_KEY'],
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'source': 'openweather',
            'city': data['name'],
            'country': data['sys']['country'],
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'],
            'description': data['weather'][0]['description'],
            'icon': data['weather'][0]['icon'],
            'latitude': data['coord']['lat'],
            'longitude': data['coord']['lon']
        }


class WeatherAPIClient:
    """WeatherAPI.com client."""
    
    @staticmethod
    def get_weather(city: str) -> dict:
        """Fetch current weather from WeatherAPI."""
        url = f"{current_app.config['WEATHERAPI_BASE_URL']}/current.json"
        params = {
            'key': current_app.config['WEATHERAPI_KEY'],
            'q': city
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'source': 'weatherapi',
            'city': data['location']['name'],
            'country': data['location']['country'],
            'temperature': data['current']['temp_c'],
            'feels_like': data['current']['feelslike_c'],
            'humidity': data['current']['humidity'],
            'pressure': data['current']['pressure_mb'],
            'wind_speed': data['current']['wind_kph'] / 3.6,  # Convert to m/s
            'description': data['current']['condition']['text'],
            'icon': data['current']['condition']['icon'].split('/')[-1].replace('.png', ''),
            'latitude': data['location']['lat'],
            'longitude': data['location']['lon']
        }