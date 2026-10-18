from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models
import schemas
import security
from database import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EdTech Gradebook API",
    description="REST API for a school gradebook: users with roles, subjects, grades and GPA.",
    version="1.1.0",
    lifespan=lifespan,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


# --- Dependencies ---
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> models.User:
    username = security.decode_access_token(token)
    user = None
    if username:
        user = db.scalar(select(models.User).where(models.User.username == username))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_teacher(user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
    if user.role != models.RoleEnum.TEACHER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teachers only")
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
TeacherUser = Annotated[models.User, Depends(require_teacher)]


# --- Auth ---
@app.get("/")
def read_root():
    return {"message": "Gradebook API is running. Go to /docs for Swagger UI."}


@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: DbSession):
    if db.scalar(select(models.User).where(models.User.username == user.username)):
        raise HTTPException(status_code=400, detail="Username already registered")

    if user.role == models.RoleEnum.TEACHER and user.invite_code != security.TEACHER_INVITE_CODE:
        raise HTTPException(status_code=403, detail="Invalid invite code for teacher registration")

    db_user = models.User(
        username=user.username,
        hashed_password=security.hash_password(user.password),
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=schemas.Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = db.scalar(select(models.User).where(models.User.username == form.username))
    if user is None or not security.verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=security.create_access_token(user.username))


@app.get("/users/me", response_model=schemas.UserResponse)
def read_me(current_user: CurrentUser):
    return current_user


@app.get("/students/", response_model=list[schemas.UserResponse])
def list_students(db: DbSession, _: TeacherUser):
    query = select(models.User).where(models.User.role == models.RoleEnum.STUDENT)
    return db.scalars(query.order_by(models.User.id)).all()


# --- Subjects ---
@app.post("/subjects/", response_model=schemas.SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(subject: schemas.SubjectCreate, db: DbSession, _: TeacherUser):
    if db.scalar(select(models.Subject).where(models.Subject.title == subject.title)):
        raise HTTPException(status_code=409, detail="Subject already exists")
    db_subject = models.Subject(title=subject.title)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


@app.get("/subjects/", response_model=list[schemas.SubjectResponse])
def list_subjects(db: DbSession, _: CurrentUser):
    return db.scalars(select(models.Subject).order_by(models.Subject.id)).all()


# --- Grades ---
@app.post("/grades/", response_model=schemas.GradeResponse, status_code=status.HTTP_201_CREATED)
def add_grade(grade: schemas.GradeCreate, db: DbSession, _: TeacherUser):
    student = db.get(models.User, grade.student_id)
    if student is None or student.role != models.RoleEnum.STUDENT:
        raise HTTPException(status_code=404, detail="Student not found")
    if db.get(models.Subject, grade.subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    new_grade = models.Grade(**grade.model_dump())
    db.add(new_grade)
    db.commit()
    db.refresh(new_grade)
    return new_grade


@app.get("/grades/", response_model=list[schemas.GradeResponse])
def list_grades(db: DbSession, current_user: CurrentUser, student_id: int | None = None):
    """Teachers see all grades (optionally filtered by student); students see only their own."""
    query = select(models.Grade)
    if current_user.role == models.RoleEnum.STUDENT:
        query = query.where(models.Grade.student_id == current_user.id)
    elif student_id is not None:
        query = query.where(models.Grade.student_id == student_id)
    return db.scalars(query.order_by(models.Grade.id)).all()


@app.delete("/grades/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(grade_id: int, db: DbSession, _: TeacherUser):
    grade = db.get(models.Grade, grade_id)
    if grade is None:
        raise HTTPException(status_code=404, detail="Grade not found")
    db.delete(grade)
    db.commit()


# --- Analytics ---
@app.get("/analytics/student/{student_id}/gpa", response_model=schemas.GpaResponse)
def get_student_gpa(student_id: int, db: DbSession, current_user: CurrentUser):
    """Average grade of a student. Students can only see their own."""
    if current_user.role == models.RoleEnum.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="You can only view your own GPA")

    avg_value, count = db.execute(
        select(func.avg(models.Grade.value), func.count(models.Grade.id)).where(
            models.Grade.student_id == student_id
        )
    ).one()
    if count == 0:
        raise HTTPException(status_code=404, detail="No grades found for this student")
    return schemas.GpaResponse(student_id=student_id, grades_count=count, gpa=round(avg_value, 2))
