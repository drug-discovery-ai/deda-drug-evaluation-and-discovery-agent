"""Pydantic models for chat server requests and responses."""

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
