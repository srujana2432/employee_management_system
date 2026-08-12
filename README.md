# AR Brands Employee Management API

A production-style REST API for managing employees and departments. Built with Python, FastAPI, SQLAlchemy, PostgreSQL, JWT authentication, and role-based authorization.

## Features

- Secure login with Argon2 password hashing and JWT access tokens
- Admin-only employee registration, updates, deletion, and department administration
- Employee profile access and self-service profile updates
- Department assignment and employee listing with pagination
- SQLAlchemy ORM models with PostgreSQL-ready configuration
- Automated API tests and interactive OpenAPI documentation

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
docker compose up -d db
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI. On first startup the API creates the database tables and a development administrator from the values below:

```text
email: admin@arbrands.local
password: Admin@12345
```

Change this default password before deploying. Run tests with `pytest`.

## API overview

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /api/v1/auth/login` |
| Employees | `GET/POST /api/v1/employees`, `GET/PATCH/DELETE /api/v1/employees/{id}` |
| My profile | `GET/PATCH /api/v1/employees/me` |
| Departments | `GET/POST /api/v1/departments`, `PATCH/DELETE /api/v1/departments/{id}` |

## Repository setup

Create a repository named `ar-brands-employee-management-api` on GitHub, then connect and push this local project:

```bash
git branch -M main
git remote add origin https://github.com/srujana2432/ar-brands-employee-management-api.git
git add .
git commit -m "Initial Employee Management API"
git push -u origin main
```

