from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    nome: str
    email: str
    ativo: bool
    criado_em: datetime