from __future__ import annotations

from app.models import User


def test_user_registration_and_login(app, client):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "confirm": "password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful" in response.data

    response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"CryptoKnight" in response.data

    with app.app_context():
        assert User.query.filter_by(username="newuser").count() == 1
