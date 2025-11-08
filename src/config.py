import os
# Define the base directory for the database file (the project root)
BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASEDIR, 'app.db')


class ValidationConfig:
    # Name format regexes and max lengths
    RESIDENT_NAME_REGEX = os.environ.get('RESIDENT_NAME_REGEX', r'^[A-Za-z\-\' ]+$')
    RESIDENT_NAME_MAX_LENGTH = int(os.environ.get('RESIDENT_NAME_MAX_LENGTH', 50))
    UNIT_NUMBER_REGEX = os.environ.get('UNIT_NUMBER_REGEX', r'^\d{1,4}$')
    UNIT_NUMBER_MAX_LENGTH = int(os.environ.get('UNIT_NUMBER_MAX_LENGTH', 6))
    PROPERTY_NAME_REGEX = os.environ.get('PROPERTY_NAME_REGEX', r'^[A-Za-z0-9 .\-]+$')
    PROPERTY_NAME_MAX_LENGTH = int(os.environ.get('PROPERTY_NAME_MAX_LENGTH', 100))
    ENFORCE_UNIQUE_RESIDENT_NAME_CASE_INSENSITIVE = os.environ.get('ENFORCE_UNIQUE_RESIDENT_NAME_CASE_INSENSITIVE', '1') == '1'
    ENFORCE_UNIQUE_PROPERTY_NAME_CASE_INSENSITIVE = os.environ.get('ENFORCE_UNIQUE_PROPERTY_NAME_CASE_INSENSITIVE', '1') == '1'
    # Configurable validation settings
    UNIT_NUMBER_MIN = int(os.environ.get('UNIT_NUMBER_MIN', 1))
    UNIT_NUMBER_MAX = int(os.environ.get('UNIT_NUMBER_MAX', 1000))
    ENFORCE_UNIQUE_RESIDENT_NAME = os.environ.get('ENFORCE_UNIQUE_RESIDENT_NAME', '1') == '1'
    ENFORCE_UNIQUE_PROPERTY_NAME = os.environ.get('ENFORCE_UNIQUE_PROPERTY_NAME', '1') == '1'

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