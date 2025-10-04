"""Data models for agent state management."""

from typing import TypedDict

from pydantic import BaseModel


class StepResult(BaseModel):
    """Result of executing a single step."""

    step: str
    result: str
    success: bool
    error: str | None = None
    tool_calls: list[str] = []  # Tools invoked during this step
    duration: float = 0.0  # Execution time in seconds


class Plan(BaseModel):
    """Execution plan with steps and metadata."""

    id: str
    steps: list[str]
    tool_calls: list[str]  # Tool names for each step
    created_at: str
    estimated_duration: float | None = None  # Optional time estimate


class AgentState(TypedDict):
    """State managed by LangGraph during plan-execute workflow."""

    input: str  # User task
    plan: Plan | None  # Full plan object
    current_step_index: int  # Current step (0-indexed)
    past_steps: list[StepResult]  # Completed steps with results
    final_response: str  # Final compiled answer
    approved: bool  # User approval flag
    needs_approval: bool  # Waiting for approval
    error: str | None  # Any error during execution
    modification_request: str | None  # Optional modification request for replanning
