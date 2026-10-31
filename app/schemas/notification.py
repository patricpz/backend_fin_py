import re
import zoneinfo
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime


VALID_NOTIFICATION_TYPES = ["overspending", "spending_spike", "installment_due", "tip", "summary"]
VALID_ACTIONS = ["opened", "dismissed", "helpful", "not_helpful", "executed"]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: UUID
    type: str
    title: str
    body: str
    status: str
    created_at: datetime
    payload: Optional[Dict[str, Any]] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    next_cursor: Optional[str] = None
    unread_count: int


class NotificationFeedbackRequest(BaseModel):
    action: Literal["opened", "dismissed", "helpful", "not_helpful", "executed"]


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    enabled_types: List[str]
    channel_in_app: bool
    channel_push: bool
    sensitivity: str
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str
    daily_limit: int


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled_types: List[str]
    channel_in_app: bool
    channel_push: bool
    sensitivity: Literal["low", "medium", "high"]
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str
    daily_limit: int = Field(..., ge=0, le=20)

    @field_validator("enabled_types")
    @classmethod
    def validate_enabled_types(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("enabled_types não pode conter duplicatas")
        for item in v:
            if item not in VALID_NOTIFICATION_TYPES:
                raise ValueError(f"Tipo inválido: {item}. Permitidos: {VALID_NOTIFICATION_TYPES}")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"Timezone IANA inválido: '{v}'")
        return v

    @model_validator(mode="after")
    def validate_quiet_hours(self):
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        if (start is None and end is not None) or (start is not None and end is None):
            raise ValueError("quiet_hours_start e quiet_hours_end devem ser ambos nulos ou ambos preenchidos")
        time_regex = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        if start is not None:
            if not time_regex.match(start):
                raise ValueError("quiet_hours_start deve estar no formato HH:MM (00:00 a 23:59)")
        if end is not None:
            if not time_regex.match(end):
                raise ValueError("quiet_hours_end deve estar no formato HH:MM (00:00 a 23:59)")
        return self
