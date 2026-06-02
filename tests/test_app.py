import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to a known state before each test."""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu"]
        }
    })
    yield
    activities.clear()


def get_participants(client, activity_name):
    response = client.get("/activities")
    response.raise_for_status()
    return response.json()[activity_name]["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client):
        # Arrange

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 2

    def test_get_activities_includes_participants(self, client):
        # Arrange

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["Chess Club"]["participants"] == ["michael@mergington.edu"]
        assert data["Programming Class"]["participants"] == ["emma@mergington.edu"]

    def test_get_activities_includes_all_fields(self, client):
        # Arrange

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        activity = response.json()["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity


class TestRootRedirect:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_static(self, client):
        # Arrange

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"

        # Act
        response = client.post(request_url)

        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "newstudent@mergington.edu" in get_participants(client, "Chess Club")

    def test_signup_duplicate_email_rejected(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/signup?email=michael@mergington.edu"

        # Act
        response = client.post(request_url)

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_case_insensitive_duplicate_rejected(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/signup?email=MICHAEL@MERGINGTON.EDU"

        # Act
        response = client.post(request_url)

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_activity_not_found(self, client):
        # Arrange
        request_url = "/activities/Nonexistent%20Club/signup?email=student@mergington.edu"

        # Act
        response = client.post(request_url)

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_multiple_students_same_activity(self, client):
        # Arrange
        first_signup = "/activities/Chess%20Club/signup?email=alice@mergington.edu"
        second_signup = "/activities/Chess%20Club/signup?email=bob@mergington.edu"

        # Act
        response1 = client.post(first_signup)
        response2 = client.post(second_signup)

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        participants = get_participants(client, "Chess Club")
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" in participants

    def test_signup_same_student_different_activities(self, client):
        # Arrange
        chess_signup = "/activities/Chess%20Club/signup?email=alice@mergington.edu"
        programming_signup = "/activities/Programming%20Class/signup?email=alice@mergington.edu"

        # Act
        response1 = client.post(chess_signup)
        response2 = client.post(programming_signup)

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert "alice@mergington.edu" in get_participants(client, "Chess Club")
        assert "alice@mergington.edu" in get_participants(client, "Programming Class")


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_success(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/unregister?email=michael@mergington.edu"

        # Act
        response = client.delete(request_url)

        # Assert
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        assert "michael@mergington.edu" not in get_participants(client, "Chess Club")

    def test_unregister_not_registered(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/unregister?email=unknown@mergington.edu"

        # Act
        response = client.delete(request_url)

        # Assert
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"]

    def test_unregister_activity_not_found(self, client):
        # Arrange
        request_url = "/activities/Nonexistent%20Club/unregister?email=michael@mergington.edu"

        # Act
        response = client.delete(request_url)

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_case_insensitive(self, client):
        # Arrange
        request_url = "/activities/Chess%20Club/unregister?email=MICHAEL@MERGINGTON.EDU"

        # Act
        response = client.delete(request_url)

        # Assert
        assert response.status_code == 200
        assert "michael@mergington.edu" not in get_participants(client, "Chess Club")

    def test_unregister_preserves_original_email_casing_on_deletion(self, client):
        # Arrange
        signup_url = "/activities/Chess%20Club/signup?email=Alice.Smith@mergington.edu"
        client.post(signup_url)
        request_url = "/activities/Chess%20Club/unregister?email=ALICE.SMITH@MERGINGTON.EDU"

        # Act
        response = client.delete(request_url)

        # Assert
        assert response.status_code == 200
        assert "Alice.Smith@mergington.edu" not in get_participants(client, "Chess Club")


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_signup_and_unregister_workflow(self, client):
        # Arrange
        email = "test@mergington.edu"
        activity_path = "Chess%20Club"
        signup_url = f"/activities/{activity_path}/signup?email={email}"
        unregister_url = f"/activities/{activity_path}/unregister?email={email}"

        # Act
        signup_response = client.post(signup_url)
        unregister_response = client.delete(unregister_url)

        # Assert
        assert signup_response.status_code == 200
        assert unregister_response.status_code == 200
        assert email not in get_participants(client, "Chess Club")

    def test_multiple_participants_lifecycle(self, client):
        # Arrange
        activity_path = "Programming%20Class"
        participants = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu"
        ]

        # Act
        for email in participants:
            response = client.post(f"/activities/{activity_path}/signup?email={email}")
            assert response.status_code == 200

        delete_response = client.delete(
            f"/activities/{activity_path}/unregister?email={participants[1]}"
        )

        # Assert
        assert delete_response.status_code == 200
        enrolled = get_participants(client, "Programming Class")
        assert participants[0] in enrolled
        assert participants[1] not in enrolled
        assert participants[2] in enrolled
