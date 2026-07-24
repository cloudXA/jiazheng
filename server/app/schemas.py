from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


DataT = TypeVar("DataT")


class ApiResponse(CamelModel, Generic[DataT]):
    code: int = 0
    data: DataT
    message: str = "ok"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskFieldStatus(StrEnum):
    CONFIRMED = "confirmed"
    MISSING = "missing"
    INFO = "info"


class RiskCaseStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"


class RiskField(CamelModel):
    key: str
    label: str
    value: str
    status: RiskFieldStatus


class RiskAnalyzeRequest(CamelModel):
    source_text: str = Field(min_length=8, max_length=6000)


class RiskAnalysis(CamelModel):
    id: str
    created_at: int
    source_text: str
    title: str
    risk_level: RiskLevel
    risk_label: str
    summary: str
    fields: list[RiskField]
    reasons: list[str]
    missing_evidence: list[str]
    before_dispatch: list[str]
    confirmation_message: str
    internal_note: str
    refusal_action: str


class RiskCaseRead(RiskAnalysis):
    status: RiskCaseStatus
    version: int


class RiskCaseStatusUpdate(CamelModel):
    status: RiskCaseStatus
    version: int | None = Field(default=None, ge=1)


class ExtractedFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: str | None = None
    service_type: str | None = None
    trial_days: int | None = Field(default=None, ge=0, le=365)
    worker_source: str | None = None
    charge_method: str | None = None
    charge_value: str | None = None
    written_confirmed: bool = False
    decision_maker_confirmed: bool = False
    no_bypass_confirmed: bool = False
    refund_explained: bool = False
    care_safety_confirmed: bool = False
    has_fee_dispute: bool = False
    has_safety_event: bool = False


class LoginRequest(CamelModel):
    code: str = Field(min_length=1, max_length=256)
    phone_code: str = Field(min_length=1, max_length=256)
    avatar_url: str | None = Field(default=None, max_length=2000)
    nick_name: str | None = Field(default=None, max_length=80)


class UserInfo(CamelModel):
    avatar_url: str
    nick_name: str
    phone: str


class LoginResult(CamelModel):
    token: str
    user_info: UserInfo


class TranscriptionResult(CamelModel):
    text: str
    simulated: bool
