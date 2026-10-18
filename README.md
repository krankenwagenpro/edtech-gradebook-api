# EdTech Gradebook API

REST API for a school gradebook, built with **FastAPI**, **SQLAlchemy 2.0** and **SQLite**.
Teachers manage subjects and grades; students can only see their own grades and GPA.

## Features
- Registration and login with **JWT** access tokens; passwords are hashed with **bcrypt**
- Role-based access control (`TEACHER` / `STUDENT`)
- Relational model: users, subjects, grades (foreign keys, unique constraints)
- Request validation with Pydantic v2 (e.g. grade must be 1.0-5.0)
- GPA calculation per student (aggregated in SQL)
- Automated tests with pytest (in-memory database)
- Interactive Swagger UI at `/docs`

## Endpoints
| Method | Path | Access |
|--------|------|--------|
| POST | `/users/` | public (teacher role requires an invite code) |
| POST | `/auth/login` | public |
| GET | `/users/me` | any user |
| GET | `/students/` | teacher |
| POST / GET | `/subjects/` | teacher / any user |
| POST | `/grades/` | teacher |
| GET | `/grades/` | teacher: all (filter `?student_id=`), student: own only |
| DELETE | `/grades/{id}` | teacher |
| GET | `/analytics/student/{id}/gpa` | teacher: any student, student: own only |

## Quickstart
```bash
git clone https://github.com/krankenwagenpro/edtech-gradebook-api.git
cd edtech-gradebook-api
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs. To register a teacher, pass the `invite_code` from the
`TEACHER_INVITE_CODE` environment variable (dev default: `dev-teacher-code`).

## Configuration
| Variable | Purpose | Default (dev only) |
|----------|---------|--------------------|
| `SECRET_KEY` | JWT signing key | `dev-only-secret-key-change-me-in-production-0000` |
| `TEACHER_INVITE_CODE` | code required to register a teacher | `dev-teacher-code` |

## Tests
```bash
pytest
```

## Project structure
- `main.py` - routes and access-control dependencies
- `schemas.py` - Pydantic request/response models
- `models.py` - SQLAlchemy models
- `security.py` - password hashing and JWT helpers
- `database.py` - engine and session setup
- `tests/test_api.py` - API tests

## Possible next steps
Alembic migrations, PostgreSQL, Docker, pagination, grade update endpoint.
