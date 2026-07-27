import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


def _signup_path(activity_name: str) -> str:
    return f"/activities/{quote(activity_name, safe='')}/signup"


def _unregister_path(activity_name: str, email: str) -> str:
    return f"/activities/{quote(activity_name, safe='')}/participants/{quote(email, safe='')}"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def restore_activities_state():
    original_activities = copy.deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def test_get_activities_returns_seeded_data(client: TestClient):
    # Arrange
    expected_activity = "Chess Club"

    # Act
    response = client.get("/activities")
    body = response.json()

    # Assert
    assert response.status_code == 200
    assert expected_activity in body
    assert {"description", "schedule", "max_participants", "participants"}.issubset(body[expected_activity])


def test_signup_adds_new_participant(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    assert email not in app_module.activities[activity_name]["participants"]

    # Act
    response = client.post(_signup_path(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_duplicate_participant_returns_400(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    existing_email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.post(_signup_path(activity_name), params={"email": existing_email})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student is already signed up for this activity"}


def test_signup_unknown_activity_returns_404(client: TestClient):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(_signup_path(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_existing_participant_succeeds(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    existing_email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.delete(_unregister_path(activity_name, existing_email))

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {existing_email} from {activity_name}"}
    assert existing_email not in app_module.activities[activity_name]["participants"]


def test_unregister_non_member_returns_404(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = "not.signed.up@mergington.edu"

    # Act
    response = client.delete(_unregister_path(activity_name, email))

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}


def test_unregister_unknown_activity_returns_404(client: TestClient):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(_unregister_path(activity_name, email))

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_root_redirects_to_static_index(client: TestClient):
    # Arrange
    path = "/"

    # Act
    response = client.get(path, follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"
