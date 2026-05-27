from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_SCREENSHOT_B64_LENGTH = 1_200_000


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ScreenshotMetadata(BaseModel):
    source: Literal["selectedMonitor", "focusedWindow", "cursorMonitor"]
    monitor_id: int | None = None
    monitor_name: str | None = None
    width: int = Field(gt=0, le=7680)
    height: int = Field(gt=0, le=4320)
    original_width: int = Field(gt=0, le=16384)
    original_height: int = Field(gt=0, le=16384)
    quality: int = Field(ge=1, le=100)
    byte_size: int = Field(gt=0, le=1_000_000)


class ScreenshotRequestMixin(BaseModel):
    screenshot_b64: str | None = Field(
        default=None,
        max_length=MAX_SCREENSHOT_B64_LENGTH,
    )
    screenshot_media_type: Literal["image/jpeg"] | None = None
    screenshot_metadata: ScreenshotMetadata | None = None

    @field_validator("screenshot_b64")
    @classmethod
    def normalize_screenshot(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None


class ChatRequest(ScreenshotRequestMixin):
    transcript: str = Field(min_length=1, max_length=20_000)
    history: list[ChatTurn] = Field(default_factory=list)
    conversation_id: str | None = None


class SupervisorRequest(ScreenshotRequestMixin):
    transcript: str = Field(min_length=1, max_length=20_000)
    history: list[ChatTurn] = Field(default_factory=list)


class SupervisorResponse(BaseModel):
    route: Literal["instant", "browser", "research", "file", "email", "clarify"]
    reasoning: str = ""
    clarify_question: str | None = None
    task: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: Literal["rules", "claude", "fallback"] = "fallback"


class AgentDispatchRequest(ScreenshotRequestMixin):
    task: str = Field(min_length=1, max_length=20_000)
    route: Literal["browser", "research", "file", "email"] | None = None
    transcript: str | None = Field(default=None, max_length=20_000)


class AgentDispatchResponse(BaseModel):
    task_id: str
    route: str
    status: str = "pending"


class AgentStatusResponse(BaseModel):
    task_id: str
    status: str
    route: str | None = None
    steps_total: int | None = None
    steps_done: int | None = None
    result: str | None = None
    error: str | None = None
    cancelled: bool = False


class CancelTaskResponse(BaseModel):
    task_id: str
    status: Literal["cancelled"]


class AuthTokenRequest(BaseModel):
    clerk_token: str


class AuthTokenResponse(BaseModel):
    access_token: str
    expires_in: int = 900


class UserMeResponse(BaseModel):
    clerk_id: str
    email: str | None
    plan: str
    messages_today: int = 0
    agent_tasks_today: int = 0


class UserUsageResponse(BaseModel):
    plan: str
    chat_limit_per_minute: int
    agent_limit_per_minute: int
    messages_today: int = 0
    agent_tasks_today: int = 0


class BillingCheckoutRequest(BaseModel):
    plan: Literal["pro", "team"] = "pro"
    success_url: str
    cancel_url: str


class BillingCheckoutResponse(BaseModel):
    url: str
