import pytest
from src import create_app, db
from src.config import TestingConfig
from src.models import *  # register models so metadata is available
from sqlalchemy.orm import sessionmaker, scoped_session

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app(config_class=TestingConfig)
    yield app

@pytest.fixture(scope='function')
def db_session(app):
    """
    Create a transactional-scoped session for each test function.

    Uses an explicit connection/transaction and a scoped_session bound
    to that connection so sqlite:///:memory: tables persist for the
    duration of the test.
    """
    with app.app_context():
        # Acquire a connection and begin a transaction on it.
        connection = db.engine.connect()
        transaction = connection.begin()

        # Create a session factory bound to the connection and a scoped_session.
        session_factory = sessionmaker(bind=connection)
        Session = scoped_session(session_factory)

        # Create all tables on the same connection (important for in-memory sqlite).
        db.metadata.create_all(bind=connection)

        # Patch Flask-SQLAlchemy to use our scoped session for the test.
        db.session = Session
        # Provide session_factory attribute in case code expects it.
        setattr(db, "session_factory", session_factory)

        try:
            yield Session()
        finally:
            # Teardown: remove scoped session, rollback outer transaction, close connection.
            Session.remove()
            transaction.rollback()
            connection.close()

@pytest.fixture(scope='function')
def client(app):
    """A Flask test client to make HTTP requests during integration tests."""
    return app.test_client()