from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    full_name: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TaskBase(BaseModel):
    title: str
    description: str
    task_type: str  # 'auto' или 'manual'
    auto_type: Optional[str] = None  # 'likes' или 'comments'
    file_format: Optional[str] = None
    deadline: datetime
    is_active: Optional[bool] = True


class TaskCreate(TaskBase):
    posts: Optional[List[str]] = None
    pass


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    created_by: int
    is_active: bool
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
