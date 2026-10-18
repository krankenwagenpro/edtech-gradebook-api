import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import security
from database import Base, get_db
from main import app


@pytest.fixture()
def env():
    """Fresh in-memory database for every test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestingSession
    app.dependency_overrides.clear()


def register(client, username, role="STUDENT", invite_code=None):
    payload = {"username": username, "password": "password123", "role": role}
    if invite_code:
        payload["invite_code"] = invite_code
    return client.post("/users/", json=payload)


def auth_header(client, username):
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_teacher(client, username="teacher"):
    register(client, username, "TEACHER", security.TEACHER_INVITE_CODE)
    return auth_header(client, username)


def test_register_hashes_password(env):
    client, Session = env
    response = register(client, "alice")
    assert response.status_code == 201
    assert "password" not in response.json()
    with Session() as db:
        user = db.scalar(select(models.User).where(models.User.username == "alice"))
        assert user.hashed_password != "password123"
        assert security.verify_password("password123", user.hashed_password)


def test_duplicate_username_rejected(env):
    client, _ = env
    register(client, "alice")
    assert register(client, "alice").status_code == 400


def test_teacher_registration_needs_invite_code(env):
    client, _ = env
    assert register(client, "sneaky", "TEACHER").status_code == 403


def test_login_wrong_password(env):
    client, _ = env
    register(client, "alice")
    response = client.post("/auth/login", data={"username": "alice", "password": "wrong-pass"})
    assert response.status_code == 401


def test_protected_endpoint_requires_token(env):
    client, _ = env
    assert client.get("/subjects/").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_student_cannot_create_subject(env):
    client, _ = env
    register(client, "alice")
    response = client.post("/subjects/", json={"title": "Math"}, headers=auth_header(client, "alice"))
    assert response.status_code == 403


def test_teacher_adds_grades_and_gpa_is_calculated(env):
    client, _ = env
    teacher = make_teacher(client)
    student_id = register(client, "alice").json()["id"]
    subject_id = client.post("/subjects/", json={"title": "Math"}, headers=teacher).json()["id"]

    for value in (4, 5):
        response = client.post(
            "/grades/",
            json={"value": value, "student_id": student_id, "subject_id": subject_id},
            headers=teacher,
        )
        assert response.status_code == 201

    gpa = client.get(f"/analytics/student/{student_id}/gpa", headers=teacher).json()
    assert gpa == {"student_id": student_id, "grades_count": 2, "gpa": 4.5}


def test_grade_out_of_range_rejected(env):
    client, _ = env
    teacher = make_teacher(client)
    student_id = register(client, "alice").json()["id"]
    subject_id = client.post("/subjects/", json={"title": "Math"}, headers=teacher).json()["id"]
    response = client.post(
        "/grades/",
        json={"value": 7, "student_id": student_id, "subject_id": subject_id},
        headers=teacher,
    )
    assert response.status_code == 422


def test_student_sees_only_own_data(env):
    client, _ = env
    teacher = make_teacher(client)
    alice_id = register(client, "alice").json()["id"]
    bob_id = register(client, "bob").json()["id"]
    subject_id = client.post("/subjects/", json={"title": "Math"}, headers=teacher).json()["id"]
    for student_id in (alice_id, bob_id):
        client.post(
            "/grades/",
            json={"value": 5, "student_id": student_id, "subject_id": subject_id},
            headers=teacher,
        )

    alice = auth_header(client, "alice")
    grades = client.get("/grades/", headers=alice).json()
    assert [g["student_id"] for g in grades] == [alice_id]
    assert client.get(f"/analytics/student/{bob_id}/gpa", headers=alice).status_code == 403
    assert client.get(f"/analytics/student/{alice_id}/gpa", headers=alice).status_code == 200
