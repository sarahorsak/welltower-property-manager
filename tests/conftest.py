# tests/conftest.py
import pytest
from src import create_app, db
from src.config import TestingConfig
from src.models import * # Import all models to ensure db.create_all() works

@pytest.fixture(scope='session')
def app():
    """Create and configure a clean Flask application instance for testing."""
    # Use the TestingConfig to set up the in-memory database
    app = create_app(config_class=TestingConfig) 

    with app.app_context():
        # 1. Create all tables in the in-memory database before the session starts
        db.create_all()

    # The 'yield' keyword makes this a generator fixture. The code after 'yield' runs on teardown.
    yield app

    with app.app_context():
        # 2. Drop all tables after the entire test session finishes
        db.drop_all()

@pytest.fixture(scope='function')
def db_session(app):
    """
    Provides a transaction-safe database session for each test function.
    
    This uses a nested transaction that is rolled back at the end of the test,
    ensuring a pristine database state for the next test.
    """
    # 1. Start a nested transaction
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Bind the session to the connection/transaction
    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)
    
    db.session = session
    
    # Use the session for the test function
    yield session
    
    # 2. Teardown (Rollback and Close)
    session.remove()
    transaction.rollback()
    connection.close()
    
@pytest.fixture(scope='function')
def client(app):
    """A Flask test client to make HTTP requests during integration tests."""
    return app.test_client()