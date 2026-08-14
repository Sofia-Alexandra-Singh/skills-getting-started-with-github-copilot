from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


def test_root_redirects_to_static_index():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_activity_data():
    # Arrange
    expected_participants = [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert "Chess Club" in payload
    assert payload["Chess Club"]["participants"] == expected_participants
    assert payload["Chess Club"]["max_participants"] == 12


def test_signup_adds_new_participant():
    # Arrange
    email = "new.student@mergington.edu"

    # Act
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert email in activities["Chess Club"]["participants"]


def test_signup_rejects_duplicate_participant():
    # Arrange
    email = "michael@mergington.edu"

    # Act
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert activities["Chess Club"]["participants"].count(email) == 1


def test_signup_rejects_unknown_activity():
    # Arrange
    email = "new.student@mergington.edu"

    # Act
    response = client.post(
        "/activities/Unknown Club/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_full_activity():
    # Arrange
    activity = activities["Chess Club"]
    activity["participants"] = [f"student{number}@mergington.edu" for number in range(12)]
    email = "new.student@mergington.edu"

    # Act
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"
    assert email not in activity["participants"]


def test_unregister_removes_participant():
    # Arrange
    email = "michael@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/Chess Club/participants/{email}"
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == (
        f"Unregistered {email} from Chess Club"
    )
    assert email not in activities["Chess Club"]["participants"]


def test_unregister_rejects_unknown_activity():
    # Arrange
    email = "student@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/Unknown Club/participants/{email}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_unknown_participant():
    # Arrange
    email = "unknown@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/Chess Club/participants/{email}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_signup_then_unregister_cycle():
    # Arrange
    email = "cycle.student@mergington.edu"

    # Act
    signup_response = client.post(
        "/activities/Soccer Club/signup",
        params={"email": email},
    )
    unregister_response = client.delete(
        f"/activities/Soccer Club/participants/{email}"
    )

    # Assert
    assert signup_response.status_code == 200
    assert unregister_response.status_code == 200
    assert email not in activities["Soccer Club"]["participants"]
