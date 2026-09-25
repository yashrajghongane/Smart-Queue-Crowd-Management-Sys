"""
tests/test_auth.py

Test suite for Staff/Admin authentication, password hashing, JWT tokens, and RBAC.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

client = TestClient(app)


def test_password_hashing():
    plain = "my-secure-password-123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_token_lifecycle():
    token = create_access_token(subject="user-123", role="ADMIN")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "ADMIN"
    assert "exp" in payload

    # Tampered token fails
    tampered = token[:-4] + "abcd"
    assert decode_access_token(tampered) is None


def test_staff_login_success():
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "smartqueue-admin-2026"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "ADMIN"
    assert data["expires_in"] > 0


def test_staff_login_invalid_password():
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrong-password"
    })
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_staff_login_unknown_user():
    res = client.post("/api/v1/auth/login", json={
        "username": "nonexistent_user",
        "password": "somepassword"
    })
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_get_current_user_me():
    # Login as doctor
    login_res = client.post("/api/v1/auth/login", json={
        "username": "doctor",
        "password": "doctor123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Call /me with Bearer token
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "doctor"
    assert data["role"] == "DEPARTMENT_STAFF"
    assert data["active"] is True


def test_get_current_user_invalid_token():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401
