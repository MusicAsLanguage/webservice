import pytest

from tests.base_case import BaseCase


@pytest.fixture
def case():
    test = BaseCase()
    test.setUp()
    try:
        yield test
    finally:
        test.clean_database()


@pytest.fixture
def app(case):
    return case.flask_app


@pytest.fixture
def client(case):
    return case.app


@pytest.fixture
def login(client):
    def create_user(email="jane@example.test"):
        payload = {"name": "Jane", "email": email, "password": "test-password"}
        signup = client.post("/api/auth/signup", json=payload)
        assert signup.status_code == 200, signup.json
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 200, response.json
        return {"Authorization": "Bearer " + response.json["token"]}, response.json, signup.json["id"]
    return create_user
