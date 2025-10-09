"""Tests for agent mode executor functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.interfaces.langchain.agent_state import StepResult
from drug_discovery_agent.interfaces.langchain.executor import execute_step


class TestExecutor:
    """Test suite for step execution."""

    @pytest.fixture
    def mock_tools(self) -> list[MagicMock]:
        """Mock LangChain tools for testing."""
        tool1 = MagicMock()
        tool1.name = "get_protein_fasta"
        tool1.description = "Get FASTA sequence"

        tool2 = MagicMock()
        tool2.name = "get_protein_details"
        tool2.description = "Get protein details"

        return [tool1, tool2]

    @pytest.mark.asyncio
    async def test_execute_step_success(self, mock_tools: list[MagicMock]) -> None:
        """Test successful step execution."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            # Mock LLM
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            # Mock executor
            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "Successfully retrieved FASTA sequence",
                "intermediate_steps": [
                    (
                        MagicMock(
                            tool="get_protein_fasta",
                            tool_input="P0DTC2",
                            log="Getting FASTA",
                        ),
                        ">sp|P0DTC2|SPIKE...",
                    )
                ],
            }
            mock_executor_class.return_value = mock_executor

            # Execute step
            result = await execute_step(
                step="Retrieve FASTA sequence for UniProt ID P0DTC2",
                tools=mock_tools,
                api_key="test-api-key",
            )

            # Verify result
            assert isinstance(result, StepResult)
            assert result.success is True
            assert result.result == ">sp|P0DTC2|SPIKE..."
            assert "get_protein_fasta" in result.tool_calls
            assert result.duration > 0
            assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_step_with_context(self, mock_tools: list[MagicMock]) -> None:
        """Test step execution with context from previous steps."""
        context = "Step 1: Found disease ID EFO_0000249\nResult: Alzheimer's disease"

        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "Found targets",
                "intermediate_steps": [],
            }
            mock_executor_class.return_value = mock_executor

            await execute_step(
                step="Get targets for the disease",
                tools=mock_tools,
                api_key="test",
                context=context,
            )

            # Verify context was passed
            call_args = mock_executor.ainvoke.call_args[0][0]
            assert call_args["context"] == context

    @pytest.mark.asyncio
    async def test_execute_step_error_handling(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test error handling when tool execution fails."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.side_effect = Exception("Tool execution failed")
            mock_executor_class.return_value = mock_executor

            result = await execute_step(
                step="Test step", tools=mock_tools, api_key="test"
            )

            # Verify error is captured
            assert result.success is False
            assert result.error == "Tool execution failed"
            assert result.result == ""
            assert result.duration > 0

    @pytest.mark.asyncio
    async def test_execute_step_uses_gpt4o_mini(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test that executor uses GPT-4o-mini model."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "result",
                "intermediate_steps": [],
            }
            mock_executor_class.return_value = mock_executor

            await execute_step(step="Test", tools=mock_tools, api_key="test-key")

            # Verify GPT-4o-mini and temperature=0
            mock_llm_class.assert_called_once()
            call_kwargs = mock_llm_class.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0

    @pytest.mark.asyncio
    async def test_execute_step_tracks_tool_calls(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test that tool calls are tracked in result."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            # Multiple tool calls in one step
            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "Complete",
                "intermediate_steps": [
                    (
                        MagicMock(tool="get_protein_details", tool_input="P0DTC2"),
                        "Details result",
                    ),
                    (MagicMock(tool="get_protein_fasta", tool_input="P0DTC2"), "FASTA"),
                ],
            }
            mock_executor_class.return_value = mock_executor

            result = await execute_step(step="Test", tools=mock_tools, api_key="test")

            # Verify both tools tracked
            assert len(result.tool_calls) == 2
            assert "get_protein_details" in result.tool_calls
            assert "get_protein_fasta" in result.tool_calls

    @pytest.mark.asyncio
    async def test_execute_step_uses_last_tool_output(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test that the last tool output is used as step result."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "Agent final answer",
                "intermediate_steps": [
                    (MagicMock(tool="tool1"), "First output"),
                    (MagicMock(tool="tool2"), "Last output"),
                ],
            }
            mock_executor_class.return_value = mock_executor

            result = await execute_step(step="Test", tools=mock_tools, api_key="test")

            # Should use last tool output
            assert result.result == "Last output"

    @pytest.mark.asyncio
    async def test_execute_step_fallback_to_agent_output(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test fallback to agent output when no tool outputs exist."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "Agent reasoning output",
                "intermediate_steps": [],  # No tool calls
            }
            mock_executor_class.return_value = mock_executor

            result = await execute_step(step="Test", tools=mock_tools, api_key="test")

            # Should use agent output
            assert result.result == "Agent reasoning output"

    @pytest.mark.asyncio
    async def test_execute_step_duration_tracking(
        self, mock_tools: list[MagicMock]
    ) -> None:
        """Test that execution duration is tracked."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.time.time"
            ) as mock_time,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            # Mock time to simulate 2.5 second execution
            mock_time.side_effect = [100.0, 102.5]

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "result",
                "intermediate_steps": [],
            }
            mock_executor_class.return_value = mock_executor

            result = await execute_step(step="Test", tools=mock_tools, api_key="test")

            # Verify duration
            assert result.duration == 2.5

    @pytest.mark.asyncio
    async def test_executor_max_iterations(self, mock_tools: list[MagicMock]) -> None:
        """Test that executor has max_iterations limit."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
        ):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            mock_executor = AsyncMock()
            mock_executor.ainvoke.return_value = {
                "output": "result",
                "intermediate_steps": [],
            }
            mock_executor_class.return_value = mock_executor

            await execute_step(step="Test", tools=mock_tools, api_key="test")

            # Verify max_iterations is set
            executor_call = mock_executor_class.call_args
            assert executor_call.kwargs["max_iterations"] == 5
            assert executor_call.kwargs["handle_parsing_errors"] is True
            assert executor_call.kwargs["return_intermediate_steps"] is True
