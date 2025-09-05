"""Session management for stateful chat server."""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from drug_discovery_agent.chat import BioinformaticsChatClient


class ChatSession:
    """Represents a single chat session with metadata."""

    def __init__(self, session_id: str, verbose: bool = False):
        self.session_id = session_id
        self.client = BioinformaticsChatClient(verbose=verbose)
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.message_count = 0

    def update_access(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()

    async def chat(self, message: str) -> str:
        """Send a message and get response, updating session metadata."""
        self.update_access()
        self.message_count += 1
        return await self.client.chat(message)

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.client.clear_conversation()
        self.message_count = 0

    @property
    def is_expired(self) -> bool:
        """Check if session has expired (default: 1 hour TTL)."""
        return datetime.now() - self.last_accessed > timedelta(hours=1)


class SessionManager:
    """Manages chat sessions with automatic cleanup."""

    def __init__(self, cleanup_interval: int = 300):  # 5 minutes
        self.sessions: dict[str, ChatSession] = {}
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_started = False

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task if there's a running event loop."""
        if self._cleanup_started:
            return

        try:
            # Only start cleanup task if there's an active event loop
            if asyncio.get_running_loop() is not None:
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(
                        self._cleanup_expired_sessions()
                    )
                    self._cleanup_started = True
        except RuntimeError:
            # No event loop running, skip cleanup task creation
            pass

    async def _cleanup_expired_sessions(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                expired_sessions = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if session.is_expired
                ]

                for session_id in expired_sessions:
                    self.delete_session(session_id)

                if expired_sessions:
                    print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error in session cleanup: {e}")

    def create_session(self, verbose: bool = False) -> str:
        """Create a new chat session."""
        self._start_cleanup_task()  # Try to start cleanup task if not already running
        session_id = str(uuid4())
        session = ChatSession(session_id, verbose=verbose)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> ChatSession | None:
        """Get an existing session by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.update_access()
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def clear_session_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        session = self.get_session(session_id)
        if session:
            session.clear_conversation()
            return True
        return False

    async def chat(self, session_id: str, message: str) -> str:
        """Send a message to a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return await session.chat(message)

    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session information."""
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "message_count": session.message_count,
            "is_active": True,
        }

    async def shutdown(self) -> None:
        """Clean shutdown of the session manager."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self.sessions.clear()
