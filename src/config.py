import os

# Define the base directory for the database file (the project root)
BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASEDIR, 'app.db')

class Config:
    """Base configuration class."""
    # Defaulting to a file-based SQLite database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DB_PATH
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Secret Key is required by Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-and-hard-to-guess-string'

class TestingConfig(Config):
    """Configuration used specifically for running Pytest."""
    TESTING = True
    # Crucial: Use an in-memory SQLite database for fast, isolated testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disabling logging during tests for cleaner output
    SQLALCHEMY_ECHO = False