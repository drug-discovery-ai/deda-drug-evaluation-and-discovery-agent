"""Pydantic models for chat server requests and responses."""

from typing import Literal

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""

    verbose: bool = False


class CreateSessionResponse(BaseModel):
    """Response containing new session ID."""

    session_id: str


class ChatRequest(BaseModel):
    """Request to send a message in an existing session."""

    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response containing chat reply."""

    session_id: str
    response: str


class SessionInfoResponse(BaseModel):
    """Response containing session information."""

    session_id: str
    created_at: str
    last_accessed: str
    message_count: int
    is_active: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    active_sessions: int = 0


# Agent Mode Models


class AgentChatRequest(BaseModel):
    """Request to create a plan in agent mode."""

    session_id: str
    message: str
    agent_mode: bool = True  # Always true for agent endpoints


class PlanResponse(BaseModel):
    """Plan returned for user approval."""

    plan_id: str
    session_id: str
    steps: list[str]
    tool_calls: list[str]
    requires_approval: bool = True
    created_at: str


class ApprovalRequest(BaseModel):
    """User's response to plan approval."""

    session_id: str
    plan_id: str
    approved: bool
    modifications: str | None = None


class ExecutionStatus(BaseModel):
    """Current execution state."""

    plan_id: str
    session_id: str
    current_step: int
    total_steps: int
    completed: list[dict]  # [{step, result, success, duration}, ...]
    status: Literal["planning", "awaiting_approval", "executing", "completed", "failed"]
    error: str | None = None
    final_response: str | None = None


class StreamEvent(BaseModel):
    """Event streamed during execution."""

    type: Literal["step_start", "tool_call", "tool_result", "step_complete", "error"]
    plan_id: str
    step_index: int
    data: dict
    timestamp: str
