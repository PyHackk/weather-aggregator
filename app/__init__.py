# app/__init__.py
"""
Flask application factory.
Creates and configures the Flask app with all extensions.
"""
from flask import Flask
from flask_restx import Api
from flask_migrate import Migrate
import redis

from app.config import config
from app.models import db


# Global extensions
migrate = Migrate()
redis_client = None


def create_app(config_name='default'):
    """
    Application factory pattern.
    
    Args:
        config_name: Configuration to use (development/production/testing)
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Redis
    global redis_client
    redis_client = redis.from_url(
        app.config['REDIS_URL'],
        decode_responses=True
    )
    
    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='1.0',
        title='Weather Aggregator API',
        description='Multi-source weather data with intelligent caching',
        doc='/docs'
    )
    
    # Register blueprints/namespaces
    from app.routes.weather import weather_ns
    api.add_namespace(weather_ns, path='/api')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'redis': redis_client.ping()}, 200
    
    return app