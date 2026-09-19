"""Tests for registration, login, and basic access control."""


def register(client, username="student1", email="student1@test.com", password="password123"):
    return client.post("/register", data={
        "first_name": "Test", "last_name": "Student", "username": username, "email": email,
        "phone_number": "08000000000", "password": password, "confirm_password": password,
    }, follow_redirects=False)


def login(client, identifier, password):
    return client.post("/login", data={"identifier": identifier, "password": password}, follow_redirects=False)


def test_register_creates_account_and_logs_in(client):
    response = register(client)
    assert response.status_code == 303
    assert "um_session" in response.cookies


def test_register_rejects_mismatched_passwords(client):
    response = client.post("/register", data={
        "first_name": "A", "last_name": "B", "username": "mismatch1", "email": "mismatch1@test.com",
        "password": "password123", "confirm_password": "differentpass",
    })
    assert response.status_code == 400


def test_register_rejects_duplicate_username(client):
    register(client, username="dupeuser", email="a@test.com")
    response = register(client, username="dupeuser", email="b@test.com")
    assert response.status_code == 400


def test_login_with_wrong_password_fails(client):
    register(client, username="loginuser", email="loginuser@test.com", password="correctpass123")
    response = login(client, "loginuser", "wrongpassword")
    assert response.status_code == 400


def test_login_with_correct_password_succeeds(client):
    register(client, username="loginuser2", email="loginuser2@test.com", password="correctpass123")
    response = login(client, "loginuser2", "correctpass123")
    assert response.status_code == 303
    assert "um_session" in response.cookies


def test_guest_cannot_reach_cart(client):
    response = client.get("/cart", follow_redirects=False)
    assert response.status_code == 303


def test_guest_can_browse_shop(client):
    response = client.get("/shop")
    assert response.status_code == 200
