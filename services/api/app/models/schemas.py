from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    transcript: str
    screenshot_b64: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)
    conversation_id: str | None = None


class SupervisorRequest(BaseModel):
    transcript: str
    screenshot_b64: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)


class SupervisorResponse(BaseModel):
    route: Literal["instant", "browser", "research", "file", "email", "clarify"]
    reasoning: str = ""
    clarify_question: str | None = None
    task: str | None = None


class AgentDispatchRequest(BaseModel):
    task: str
    route: Literal["browser", "research", "file", "email"] | None = None
    screenshot_b64: str | None = None
    transcript: str | None = None


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


class BillingCheckoutRequest(BaseModel):
    plan: Literal["pro", "team"] = "pro"
    success_url: str
    cancel_url: str


class BillingCheckoutResponse(BaseModel):
    url: str
