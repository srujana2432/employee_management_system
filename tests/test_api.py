import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_employee_management.db"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def setup_module():
    Base.metadata.drop_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    Path("test_employee_management.db").unlink(missing_ok=True)


def test_employee_management_flow():
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "admin@arbrands.com", "password": "Admin@12345"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        department = client.post("/api/v1/departments", json={"name": "Engineering"}, headers=headers)
        assert department.status_code == 201
        employee = client.post("/api/v1/employees", json={"first_name": "Asha", "last_name": "Patel", "email": "asha@example.com", "password": "Employee@123", "department_id": department.json()["id"]}, headers=headers)
        assert employee.status_code == 201
        assert client.get("/api/v1/employees", headers=headers).json()[1]["email"] == "asha@example.com"
