# src/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import config

# Initialize extensions, but don't tie them to an app yet
db = SQLAlchemy()

def create_app(config_name='default'):
    """
    Application factory function.
    """
    app = Flask(__name__)
    
    # Load configuration from config.py
    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    
    # Enable CORS for the frontend
    CORS(app) 

    # Register API blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app