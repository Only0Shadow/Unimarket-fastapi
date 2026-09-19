"""
Shared pytest fixtures.

Tests run against a throwaway SQLite file (not the dev database), rebuilt
fresh for every test function so tests never leak state into each other.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_university_marketplace.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.database import Base, get_db
from app.config import get_settings

get_settings.cache_clear()

TEST_DB_PATH = "./test_university_marketplace.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


main_module.app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_database():
    """Recreate all tables before every test function."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    with TestClient(main_module.app) as c:
        yield c


@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
