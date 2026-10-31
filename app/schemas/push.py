from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID


class PushPublicKeyResponse(BaseModel):
    public_key: str


class PushSubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    endpoint: str = Field(..., min_length=1)
    p256dh: str = Field(..., min_length=1)
    auth: str = Field(..., min_length=1)
    user_agent: Optional[str] = None

    @field_validator("endpoint")
    @classmethod
    def validate_https_endpoint(cls, v: str) -> str:
        v_str = v.strip()
        if not v_str.startswith("https://"):
            raise ValueError("endpoint deve ser uma URL HTTPS válida")
        return v_str

    @field_validator("p256dh", "auth")
    @classmethod
    def validate_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obrigatório e não pode ser vazio")
        return v.strip()


class PushSubscriptionResponse(BaseModel):
    id: UUID
