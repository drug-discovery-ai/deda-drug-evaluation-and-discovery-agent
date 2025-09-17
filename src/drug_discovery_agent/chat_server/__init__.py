"""Stateful chat server package for bioinformatics queries."""

from drug_discovery_agent.chat_server.models import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    HealthResponse,
    SessionInfoResponse,
)
from drug_discovery_agent.chat_server.server import ChatServer, main
from drug_discovery_agent.chat_server.session_manager import ChatSession, SessionManager

__all__ = [
    # Server
    "ChatServer",
    "main",
    # Session Management
    "SessionManager",
    "ChatSession",
    # Models
    "CreateSessionRequest",
    "CreateSessionResponse",
    "ChatRequest",
    "ChatResponse",
    "SessionInfoResponse",
    "HealthResponse",
]
