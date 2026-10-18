# EdTech Gradebook & Analytics REST API

A scalable backend microservice built with **FastAPI**, **SQLAlchemy ORM**, and **SQLite/PostgreSQL**. Designed for educational institutions to manage students, academic performance, and calculate grade-point analytics.

## Features
- **RESTful Endpoints:** Full CRUD for Users (Teachers & Students), Subjects, and Grades.
- **Data Validation & Typing:** Enforced using Pydantic schemas.
- **Relational Data Modeling:** Foreign keys, relationships, and constraints with SQLAlchemy ORM.
- **Academic Analytics:** Automated GPA (Grade Point Average) calculation per student.
- **Interactive Documentation:** Auto-generated OpenAPI 3.1 Swagger UI.

## Tech Stack
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Database:** SQLite (dev) / PostgreSQL ready

## Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/edtech-gradebook-api.git
   cd edtech-gradebook-api
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

5. **API Documentation:**
   Open your browser and navigate to `http://127.0.0.1:8000/docs`.
