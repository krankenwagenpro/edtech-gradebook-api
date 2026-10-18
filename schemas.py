from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import RoleEnum


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    role: RoleEnum = RoleEnum.STUDENT
    invite_code: str | None = Field(
        default=None, description="Required only when registering as TEACHER"
    )

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt only accepts passwords up to 72 bytes
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SubjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class GradeCreate(BaseModel):
    value: float = Field(ge=1.0, le=5.0, description="Grade from 1.0 to 5.0")
    student_id: int
    subject_id: int


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    value: float
    student_id: int
    subject_id: int


class GpaResponse(BaseModel):
    student_id: int
    grades_count: int
    gpa: float
