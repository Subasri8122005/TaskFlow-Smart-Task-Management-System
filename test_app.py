
import sqlite3
import pytest
import app as taskflow


@pytest.fixture
def client(tmp_path):
    # Create a separate temporary database for testing
    test_db = tmp_path / "test_tasks.db"
    original_db = taskflow.DATABASE
    taskflow.DATABASE = str(test_db)

    connection = sqlite3.connect(test_db)

    connection.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            category TEXT NOT NULL DEFAULT 'work',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()

    taskflow.app.config.update(TESTING=True)

    with taskflow.app.test_client() as test_client:
        yield test_client

    taskflow.DATABASE = original_db


@pytest.fixture
def logged_in_client(client):
    client.post("/api/register", json={
        "username": "testuser",
        "password": "password123"
    })

    client.post("/api/login", json={
        "username": "testuser",
        "password": "password123"
    })

    return client


def test_user_registration(client):
    response = client.post("/api/register", json={
        "username": "testuser",
        "password": "password123"
    })

    assert response.status_code == 201


def test_duplicate_registration(client):
    data = {
        "username": "testuser",
        "password": "password123"
    }

    client.post("/api/register", json=data)
    response = client.post("/api/register", json=data)

    assert response.status_code == 409


def test_user_login(client):
    client.post("/api/register", json={
        "username": "testuser",
        "password": "password123"
    })

    response = client.post("/api/login", json={
        "username": "testuser",
        "password": "password123"
    })

    assert response.status_code == 200


def test_tasks_require_login(client):
    response = client.get("/api/tasks")

    assert response.status_code == 401


def test_add_task(logged_in_client):
    response = logged_in_client.post("/api/tasks", json={
        "title": "Learn Python Testing",
        "priority": "high",
        "category": "study",
        "due_date": "2026-12-01"
    })

    assert response.status_code == 201
    assert response.json["title"] == "Learn Python Testing"
    assert response.json["category"] == "study"


def test_update_task(logged_in_client):
    create_response = logged_in_client.post("/api/tasks", json={
        "title": "Original Task"
    })

    task_id = create_response.json["id"]

    response = logged_in_client.put(
        f"/api/tasks/{task_id}",
        json={
            "title": "Updated Task",
            "status": "done"
        }
    )

    assert response.status_code == 200

    tasks = logged_in_client.get("/api/tasks").json

    assert tasks[0]["title"] == "Updated Task"
    assert tasks[0]["status"] == "done"


def test_delete_task(logged_in_client):
    create_response = logged_in_client.post("/api/tasks", json={
        "title": "Task to Delete"
    })

    task_id = create_response.json["id"]

    response = logged_in_client.delete(
        f"/api/tasks/{task_id}"
    )

    assert response.status_code == 200

    tasks = logged_in_client.get("/api/tasks").json

    assert len(tasks) == 0


def test_dashboard_statistics(logged_in_client):
    logged_in_client.post("/api/tasks", json={
        "title": "Pending Task"
    })

    second_task = logged_in_client.post("/api/tasks", json={
        "title": "Completed Task"
    })

    task_id = second_task.json["id"]

    logged_in_client.put(
        f"/api/tasks/{task_id}",
        json={"status": "done"}
    )

    response = logged_in_client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json["total"] == 2
    assert response.json["pending"] == 1
    assert response.json["done"] == 1
    assert response.json["progress"] == 50


def test_csv_export(logged_in_client):
    logged_in_client.post("/api/tasks", json={
        "title": "CSV Export Test",
        "category": "work",
        "priority": "medium"
    })

    response = logged_in_client.get("/api/tasks/export")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "CSV Export Test" in response.data.decode("utf-8-sig")
