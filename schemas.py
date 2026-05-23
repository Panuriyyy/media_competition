import json
from urllib.parse import urlparse
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List


def _check_domain(url, allowed, field_name, required):
    if not url:
        return None
    try:
        host = (urlparse(url).hostname or '').lower()
        if host.startswith('www.'):
            host = host[4:]
        if host not in allowed:
            raise ValueError(
                "{}: допустимые домены — {}".format(field_name, ', '.join(allowed))
            )
    except ValueError:
        raise
    except Exception:
        raise ValueError("{}: некорректная ссылка".format(field_name))
    return url

INSTITUTES_LIST = [
    "ГИ",
    "ИКНК",
    "ИПМЭиТ",
    "ИСИ",
    "ИБСиБ",
    "ИЭиТ",
    "Физмех",
    "ИЭ",
    "ИММИТ",
    "ИСПО",
]


class UserBase(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    institute: str
    vk_link: Optional[str] = None
    tg_link: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    institute: str
    vk_link: str
    tg_link: Optional[str] = None

    @field_validator("institute")
    @classmethod
    def validate_institute(cls, v):
        if v not in INSTITUTES_LIST:
            raise ValueError("Выберите институт из предложенного списка")
        return v

    @field_validator("vk_link")
    @classmethod
    def validate_vk_link(cls, v):
        return _check_domain(v, ["vk.com", "vk.ru"], "Ссылка ВКонтакте", required=True)

    @field_validator("tg_link")
    @classmethod
    def validate_tg_link(cls, v):
        return _check_domain(v, ["t.me", "telegram.me"], "Ссылка Telegram", required=False)


class UserOut(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    task_type: str  # auto / manual
    auto_type: Optional[str] = None
    points_at_stake: float = Field(..., ge=0)
    deadline: datetime
    posts_urls: Optional[List[str]] = None
    format_type: Optional[str] = None

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v):
        if v not in ["auto", "manual"]:
            raise ValueError("task_type must be 'auto' or 'manual'")
        return v


class TaskOut(TaskCreate):
    id: int
    is_active: bool

    @field_validator("posts_urls", mode="before")
    @classmethod
    def parse_posts_urls(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        return v

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    submission_url: Optional[str] = None


class VKAuth(BaseModel):
    access_token: str
    user_id: int


class ResetPasswordVK(BaseModel):
    access_token: str
    new_password: str = Field(..., min_length=6)
