# app/config.py
"""
Application configuration.
Loads settings from environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://weather_user:weather_pass@localhost:5432/weather_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # External APIs
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    WEATHERAPI_KEY = os.getenv('WEATHERAPI_KEY')
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', 100))
    
    # Cache
    CACHE_TTL = int(os.getenv('CACHE_TTL', 600))  # 10 minutes
    
    # API URLs
    OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'
    WEATHERAPI_BASE_URL = 'https://api.weatherapi.com/v1'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    REDIS_URL = 'redis://localhost:6379/1'  # Different DB for tests


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}