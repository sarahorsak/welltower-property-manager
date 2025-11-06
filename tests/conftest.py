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
    duration of the test. Restores the original Flask-SQLAlchemy session
    on teardown to avoid leaving db.session pointing at a closed connection.
    """
    with app.app_context():
        # Keep the original session so we can restore it later
        original_session = db.session

        # 1) Acquire a connection and begin a transaction on it.
        connection = db.engine.connect()
        transaction = connection.begin()

        # 2) Create a session factory bound to this connection and a scoped_session.
        session_factory = sessionmaker(bind=connection)
        Session = scoped_session(session_factory)

        # 3) Create all tables on the same connection (important for in-memory sqlite).
        db.metadata.create_all(bind=connection)

        # 4) Patch Flask-SQLAlchemy to use our scoped session for the duration of the test.
        db.session = Session
        setattr(db, "session_factory", session_factory)

        try:
            yield Session()
        finally:
            # 5) Teardown: remove scoped session, rollback transaction, close connection,
            #    and restore original Flask-SQLAlchemy session so other tests using client work.
            Session.remove()
            transaction.rollback()
            connection.close()

            # restore the original session object the extension provided
            db.session = original_session
            # remove any test-added attribute to avoid surprising globals
            if hasattr(db, "session_factory"):
                delattr(db, "session_factory")

@pytest.fixture(scope='function')
def client(app):
    """A Flask test client to make HTTP requests during integration tests."""
    return app.test_client()