from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config, TestingConfig

# Initialize SQLAlchemy outside the create_app function
db = SQLAlchemy()

def create_app(config_class=Config, config_name=None):
    # map friendly names to classes
    if config_name:
        if config_name == 'testing':
            config_class = TestingConfig
        else:
            config_class = config_name   # allow import path string fallback
    
    # 1. Application Setup
    app = Flask(__name__)
    # Load configuration from the specified class (defaulting to Config)
    app.config.from_object(config_class)

    # 2. Database Initialization
    db.init_app(app)

    # 3. Register Blueprints (Routes)
    from .routes import register_blueprints
    register_blueprints(app)

    # 4. Import Models (Required to create the database tables)
    # This line ensures SQLAlchemy knows about all your classes (Property, Unit, etc.)
    from . import models 

    # 5. Database Table Creation (Inside application context)
    # This is useful for initial setup and testing (using SQLite)
    with app.app_context():
        # Only create tables if the database doesn't exist
        db.create_all()

    return app