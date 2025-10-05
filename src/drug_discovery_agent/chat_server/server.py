"""Stateful HTTP chat server for bioinformatics queries with session management."""

import argparse
import asyncio
import json
import signal
from collections.abc import AsyncIterator
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from drug_discovery_agent.chat_server.models import (
    AgentChatRequest,
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    ExecutionStatus,
    HealthResponse,
    PlanResponse,
    SessionInfoResponse,
)
from drug_discovery_agent.chat_server.session_manager import SessionManager
from drug_discovery_agent.interfaces.langchain.agent_state import Plan
from drug_discovery_agent.key_storage.key_manager import APIKeyManager, StorageMethod
from drug_discovery_agent.settings.api_key.settings import create_api_key_routes

# Load environment variables from .env file
from drug_discovery_agent.utils.env import load_env_for_bundle


class ChatServer:
    """Stateful HTTP chat server using SessionManager and BioinformaticsChatClient."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session_manager = SessionManager()

    # Session management endpoints
    async def create_session_endpoint(self, request: Request) -> JSONResponse:
        """Create a new chat session."""
        try:
            body = await request.json()
            create_request = CreateSessionRequest(**body)

            session_id = self.session_manager.create_session(
                verbose=create_request.verbose
            )
            response = CreateSessionResponse(session_id=session_id)

            return JSONResponse(response.model_dump())
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def delete_session_endpoint(self, request: Request) -> JSONResponse:
        """Delete a chat session."""
        try:
            session_id = request.path_params["session_id"]

            deleted = self.session_manager.delete_session(session_id)
            if not deleted:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            return JSONResponse({"message": f"Session {session_id} deleted"})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def clear_session_endpoint(self, request: Request) -> JSONResponse:
        """Clear conversation history for a session."""
        try:
            session_id = request.path_params["session_id"]

            cleared = self.session_manager.clear_session_conversation(session_id)
            if not cleared:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            return JSONResponse(
                {"message": f"Session {session_id} conversation cleared"}
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def get_session_info_endpoint(self, request: Request) -> JSONResponse:
        """Get session information."""
        try:
            session_id = request.path_params["session_id"]

            session_info = self.session_manager.get_session_info(session_id)
            if not session_info:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            response = SessionInfoResponse(**session_info)
            return JSONResponse(response.model_dump())
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    # Chat endpoints
    async def chat_endpoint(self, request: Request) -> JSONResponse:
        """Stateful chat endpoint using existing session."""
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse({"error": f"Invalid JSON: {str(e)}"}, status_code=400)

        try:
            chat_request = ChatRequest(**body)
        except Exception as e:
            return JSONResponse(
                {"error": f"Invalid request format: {str(e)}"}, status_code=400
            )

        try:
            # Use existing session
            response_text = await self.session_manager.chat(
                chat_request.session_id, chat_request.message
            )

            response = ChatResponse(
                session_id=chat_request.session_id, response=response_text
            )

            return JSONResponse(response.model_dump())
        except ValueError as e:  # Session not found
            return JSONResponse({"error": str(e)}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def chat_stream_endpoint(
        self, request: Request
    ) -> StreamingResponse | JSONResponse:
        """Stateful streaming chat endpoint using Server-Sent Events."""
        try:
            body = await request.json()
            chat_request = ChatRequest(**body)

            async def generate_response() -> AsyncIterator[str]:
                try:
                    # Send initial processing signal
                    yield f"data: {json.dumps({'type': 'processing', 'data': 'Processing your query...'})}\n\n"

                    # Get response from existing session
                    response = await self.session_manager.chat(
                        chat_request.session_id, chat_request.message
                    )

                    # Send the full response as content
                    yield f"data: {json.dumps({'type': 'content', 'data': response})}\n\n"

                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'done', 'data': 'completed'})}\n\n"

                except ValueError as e:  # Session not found
                    error_msg = f"Session error: {str(e)}"
                    yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"

            return StreamingResponse(
                generate_response(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                },
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def health_check(self, request: Request) -> JSONResponse:
        """Health check endpoint with session metrics."""
        response = HealthResponse(
            status="healthy",
            service="bioinformatics-chat-server",
            version="1.0.0",
            active_sessions=self.session_manager.get_session_count(),
        )
        return JSONResponse(response.model_dump())

    # Agent Mode endpoints

    async def create_agent_plan_endpoint(self, request: Request) -> JSONResponse:
        """Create execution plan for user task.

        Plan requires approval before execution.
        """
        try:
            body = await request.json()
            agent_request = AgentChatRequest(**body)

            plan = await self.session_manager.create_agent_plan(
                agent_request.session_id, agent_request.message
            )

            response = PlanResponse(
                plan_id=plan.id,
                session_id=agent_request.session_id,
                steps=plan.steps,
                tool_calls=plan.tool_calls,
                created_at=plan.created_at,
            )

            return JSONResponse(response.model_dump())

        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def approve_plan_endpoint(self, request: Request) -> JSONResponse:
        """Approve or reject plan.

        If approved: starts execution
        If rejected with modifications: creates new plan
        """
        try:
            body = await request.json()
            approval_request = ApprovalRequest(**body)

            result = await self.session_manager.approve_plan(
                approval_request.session_id,
                approval_request.plan_id,
                approval_request.approved,
                approval_request.modifications,
            )

            if not approval_request.approved and isinstance(result, Plan):
                # Return new plan for approval
                response = PlanResponse(
                    plan_id=result.id,
                    session_id=approval_request.session_id,
                    steps=result.steps,
                    tool_calls=result.tool_calls,
                    created_at=result.created_at,
                )
                return JSONResponse(response.model_dump())

            return JSONResponse({"status": "approved", "message": "Execution started"})

        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_plan_endpoint(self, request: Request) -> JSONResponse:
        """Retrieve plan details by ID."""
        try:
            plan_id = request.path_params["plan_id"]
            session_id = request.query_params.get("session_id")

            if not session_id:
                return JSONResponse(
                    {"error": "session_id query parameter required"}, status_code=400
                )

            session = self.session_manager.get_session(session_id)
            if not session:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            if (
                not session.current_plan or session.current_plan.id != plan_id  # type: ignore
            ):
                return JSONResponse({"error": "Plan not found"}, status_code=404)

            plan = session.current_plan
            response = PlanResponse(
                plan_id=plan.id,  # type: ignore
                session_id=session_id,
                steps=plan.steps,  # type: ignore
                tool_calls=plan.tool_calls,  # type: ignore
                created_at=plan.created_at,  # type: ignore
            )

            return JSONResponse(response.model_dump())

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_execution_status_endpoint(self, request: Request) -> JSONResponse:
        """Get current execution status."""
        try:
            plan_id = request.path_params["plan_id"]
            session_id = request.query_params.get("session_id")

            if not session_id:
                return JSONResponse(
                    {"error": "session_id query parameter required"}, status_code=400
                )

            status = await self.session_manager.get_execution_status(
                session_id, plan_id
            )
            response = ExecutionStatus(**status)

            return JSONResponse(response.model_dump())

        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def cancel_execution_endpoint(self, request: Request) -> JSONResponse:
        """Cancel ongoing execution."""
        try:
            body = await request.json()
            session_id = body.get("session_id")
            plan_id = body.get("plan_id")

            if not session_id or not plan_id:
                return JSONResponse(
                    {"error": "session_id and plan_id required"}, status_code=400
                )

            await self.session_manager.cancel_agent_execution(session_id, plan_id)
            return JSONResponse({"status": "cancelled"})

        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    def create_app(self) -> Starlette:
        """Create the Starlette application with routes and middleware."""

        # Define routes
        routes = [
            # Session management
            Route("/sessions", self.create_session_endpoint, methods=["POST"]),
            Route(
                "/sessions/{session_id}",
                self.delete_session_endpoint,
                methods=["DELETE"],
            ),
            Route(
                "/sessions/{session_id}/clear",
                self.clear_session_endpoint,
                methods=["POST"],
            ),
            Route(
                "/sessions/{session_id}/info",
                self.get_session_info_endpoint,
                methods=["GET"],
            ),
            # Chat endpoints
            Route("/chat", self.chat_endpoint, methods=["POST"]),
            Route("/chat/stream", self.chat_stream_endpoint, methods=["POST"]),
            # Agent mode endpoints
            Route("/chat/agent", self.create_agent_plan_endpoint, methods=["POST"]),
            Route("/chat/agent/approve", self.approve_plan_endpoint, methods=["POST"]),
            Route(
                "/chat/agent/plan/{plan_id}",
                self.get_plan_endpoint,
                methods=["GET"],
            ),
            Route(
                "/chat/agent/status/{plan_id}",
                self.get_execution_status_endpoint,
                methods=["GET"],
            ),
            Route(
                "/chat/agent/cancel", self.cancel_execution_endpoint, methods=["POST"]
            ),
            # Health check
            Route("/health", self.health_check, methods=["GET"]),
        ]

        routes.extend(create_api_key_routes())

        app = Starlette(debug=True, routes=routes)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "app://electron-app",
                "http://127.0.0.1:3000",
            ],
            allow_methods=["GET", "POST", "DELETE", "PUT"],
            allow_headers=["*"],
        )

        return app

    async def shutdown(self) -> None:
        """Clean shutdown of the chat server."""
        await self.session_manager.shutdown()


def display_api_key_status() -> None:
    """Display API key status information at startup."""
    has_key, message, source = check_api_key_availability()

    if has_key:
        print(f"🔑 {message}")
        if source == StorageMethod.ENVIRONMENT:
            print("   Source: Environment variable")
        elif source == StorageMethod.KEYCHAIN:
            print("   Source: OS keychain (secure)")
        elif source == StorageMethod.ENCRYPTED_FILE:
            print("   Source: Encrypted file storage")
    else:
        print(f"⚠️  {message}")
        print("   API keys can be configured through:")
        print("   • Frontend settings page")
        print("   • Environment variable (API_KEY)")
        print("   • API endpoints (/api/key)")
        print("   Note: Some features may require an API key to function properly")


def check_api_key_availability() -> tuple[bool, str, StorageMethod]:
    """Check if API key is available at startup.

    Returns:
        Tuple of (has_key, status_message, source)
    """
    key_manager = APIKeyManager()
    api_key, source = key_manager.get_api_key()

    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        return True, f"API key found from {source.value} ({masked_key})", source
    else:
        return (
            False,
            "No API key found in any storage location",
            StorageMethod.NOT_FOUND,
        )


def main() -> None:
    """Main entry point for the chat server."""
    load_env_for_bundle()
    from ..config import BACKEND_HOST, BACKEND_PORT

    parser = argparse.ArgumentParser(
        description="Stateful Bioinformatics Chat Server - HTTP API for Electron frontend"
    )
    parser.add_argument("--host", default=BACKEND_HOST, help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=BACKEND_PORT, help="Port to listen on"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output showing tool selection and execution details",
    )
    parser.add_argument(
        "--skip-key-check",
        action="store_true",
        help="Skip API key availability check at startup",
    )

    args = parser.parse_args()

    # Check API key availability at startup
    if not args.skip_key_check:
        display_api_key_status()
        print()  # Add spacing

    # Create chat server
    chat_server = ChatServer(verbose=args.verbose)
    app = chat_server.create_app()

    print(
        f"Stateful Bioinformatics Chat Server starting on http://{args.host}:{args.port}"
    )
    print("Endpoints:")
    print("   Session Management:")
    print("     POST /sessions - Create new session")
    print("     DELETE /sessions/{id} - Delete session")
    print("     POST /sessions/{id}/clear - Clear conversation")
    print("   Chat:")
    print("     POST /chat - Send message (requires session_id)")
    print("     POST /chat/stream - Streaming chat (requires session_id)")
    print("   API Key Management:")
    print("     POST /api/key - Store API key")
    print("     GET /api/key/status - Get key status")
    print("     PUT /api/key - Update API key")
    print("     DELETE /api/key - Delete API key")
    print("     POST /api/key/validate - Validate key format")
    print("   Health:")
    print("     GET /health - Health check with session metrics")
    print("Ready for stateful Electron frontend connections!")

    def signal_handler(sig: int, frame: Any) -> None:
        print("\n🛑 Shutting down server...")
        asyncio.create_task(chat_server.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
