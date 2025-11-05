# tests/conftest.py
import pytest
from src import create_app, db

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    # Use the 'testing' configuration
    app = create_app(config_name='testing')
    
    # Establish an application context
    with app.app_context():
        # Create the database tables
        db.create_all()
        
        yield app  # This is what the test function will use
        
        # Teardown:
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """
    Creates a new database session for a test.
    This uses a 'function' scope to ensure a clean state for each test.
    It rolls back any changes after the test.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        
        db.session = session

        yield session  # Test runs with this session

        # Rollback and clean up
        session.remove()
        transaction.rollback()
        connection.close()