from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EdTech Gradebook API",
    description="REST API для управления успеваемостью студентов и аналитики оценок",
    version="1.0.0"
)

# --- Схемы данных (Pydantic) ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: models.RoleEnum

class UserResponse(BaseModel):
    id: int
    username: str
    role: models.RoleEnum

    class Config:
        from_attributes = True

class SubjectCreate(BaseModel):
    title: str

class SubjectResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

class GradeCreate(BaseModel):
    value: float = Field(..., ge=1.0, le=5.0, description="Оценка от 1.0 до 5.0")
    student_id: int
    subject_id: int

class GradeResponse(BaseModel):
    id: int
    value: float
    student_id: int
    subject_id: int

    class Config:
        from_attributes = True

# --- Эндпоинты ---
@app.get("/")
def read_root():
    return {"message": "Gradebook API is running. Go to /docs for Swagger UI."}

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Для простоты первого шага сохраняем пароль, на следующем шаге прикрутим хеширование и JWT
    db_user = models.User(username=user.username, hashed_password=user.password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/subjects/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(subject: SubjectCreate, db: Session = Depends(get_db)):
    db_subject = models.Subject(title=subject.title)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject

@app.post("/grades/", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def add_grade(grade: GradeCreate, db: Session = Depends(get_db)):
    # Проверка существования студента и предмета
    student = db.query(models.User).filter(models.User.id == grade.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    subject = db.query(models.Subject).filter(models.Subject.id == grade.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    new_grade = models.Grade(value=grade.value, student_id=grade.student_id, subject_id=grade.subject_id)
    db.add(new_grade)
    db.commit()
    db.refresh(new_grade)
    return new_grade

@app.get("/analytics/student/{student_id}/gpa")
def get_student_gpa(student_id: int, db: Session = Depends(get_db)):
    """Расчет среднего балла (GPA) студента"""
    grades = db.query(models.Grade).filter(models.Grade.student_id == student_id).all()
    if not grades:
        raise HTTPException(status_code=404, detail="No grades found for this student")
    
    avg_score = sum(g.value for g in grades) / len(grades)
    return {
        "student_id": student_id,
        "grades_count": len(grades),
        "gpa": round(avg_score, 2)
    }