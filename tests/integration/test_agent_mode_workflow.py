"""Integration tests for agent mode end-to-end workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.interfaces.langchain.agent_mode_chat_client import (
    AgentModeChatClient,
)
from drug_discovery_agent.interfaces.langchain.agent_state import Plan
from drug_discovery_agent.interfaces.langchain.planner import PlanOutput


class TestAgentModeWorkflow:
    """Integration tests for complete agent mode workflows."""

    @pytest.fixture
    def mock_api_key(self) -> str:
        """Mock API key for testing."""
        return "test-api-key-12345"

    @pytest.fixture
    def sample_plan_output(self) -> PlanOutput:
        """Sample plan for integration testing."""
        return PlanOutput(
            steps=[
                "Search for diabetes in disease ontology",
                "For disease ID EFO_0000400, retrieve therapeutic targets",
                "Get detailed protein information for top target",
            ],
            tool_calls=[
                "get_disease_list",
                "get_disease_targets",
                "get_protein_details",
            ],
        )

    @pytest.mark.asyncio
    async def test_full_workflow_plan_approve_execute(
        self, mock_api_key: str, sample_plan_output: PlanOutput
    ) -> None:
        """Test complete workflow: create plan → approve → execute → get result."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_mode_chat_client.APIKeyManager"
            ) as mock_key_manager,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_planner_prompt,
            patch("drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"),
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
            patch("langchain_openai.ChatOpenAI") as mock_finish_llm,
            patch("langchain.prompts.ChatPromptTemplate") as mock_finish_prompt,
        ):
            # Setup API key
            mock_km = MagicMock()
            mock_km.get_api_key.return_value = (mock_api_key, "test")
            mock_key_manager.return_value = mock_km

            # Setup planner
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=sample_plan_output)
            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_planner_prompt.from_messages.return_value = mock_prompt

            # Setup executor
            step_results = [
                {
                    "output": "Found disease: Type 2 Diabetes (EFO_0000400)",
                    "intermediate_steps": [
                        (
                            MagicMock(tool="get_disease_list"),
                            "Disease ID: EFO_0000400",
                        )
                    ],
                },
                {
                    "output": "Found 10 therapeutic targets",
                    "intermediate_steps": [
                        (
                            MagicMock(tool="get_disease_targets"),
                            "Targets: INS, GCG, ...",
                        )
                    ],
                },
                {
                    "output": "Protein details: Insulin receptor",
                    "intermediate_steps": [
                        (MagicMock(tool="get_protein_details"), "Details of protein")
                    ],
                },
            ]

            mock_executor = AsyncMock()
            mock_executor.ainvoke.side_effect = step_results
            mock_executor_class.return_value = mock_executor

            # Mock finish node LLM
            mock_finish_chain = AsyncMock()
            mock_finish_chain.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Final synthesized answer about diabetes targets"
                )
            )
            mock_finish_prompt_inst = MagicMock()
            mock_finish_prompt_inst.__or__ = MagicMock(return_value=mock_finish_chain)
            mock_finish_prompt.from_messages.return_value = mock_finish_prompt_inst
            mock_finish_llm.return_value = MagicMock()

            # Create client and execute workflow
            client = AgentModeChatClient()

            # Step 1: Create plan
            plan = await client.create_plan("Find targets for diabetes")

            # Verify plan
            assert isinstance(plan, Plan)
            assert len(plan.steps) == 3
            assert "diabetes" in plan.steps[0].lower()

            # Step 2: Approve and execute
            result = await client.approve_and_execute(approved=True)

            # Verify final result
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_plan_modification_workflow(
        self, mock_api_key: str, sample_plan_output: PlanOutput
    ) -> None:
        """Test that client can create multiple plans."""
        modified_plan_output = PlanOutput(
            steps=[
                "Search for diabetes in disease ontology",
                "For disease ID EFO_0000400, retrieve therapeutic targets",
                "Analyze sequence properties of top target",
                "Get AlphaFold structure prediction",
            ],
            tool_calls=[
                "get_disease_list",
                "get_disease_targets",
                "analyze_sequence_properties",
                "get_alphafold_prediction",
            ],
        )

        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_mode_chat_client.APIKeyManager"
            ) as mock_key_manager,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_planner_prompt,
        ):
            # Setup API key
            mock_km = MagicMock()
            mock_km.get_api_key.return_value = (mock_api_key, "test")
            mock_key_manager.return_value = mock_km

            # Setup planner prompt - return different plans
            chains = []
            for plan_out in [sample_plan_output, modified_plan_output]:
                mock_chain = AsyncMock()
                mock_chain.ainvoke = AsyncMock(return_value=plan_out)
                chains.append(mock_chain)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(side_effect=chains)
            mock_planner_prompt.from_messages.return_value = mock_prompt

            client = AgentModeChatClient()

            # Create first plan
            plan1 = await client.create_plan("Find targets for diabetes")
            assert len(plan1.steps) == 3
            assert plan1.tool_calls == [
                "get_disease_list",
                "get_disease_targets",
                "get_protein_details",
            ]

            # Create second plan with different query
            plan2 = await client.create_plan("Find targets and analyze sequences")
            assert len(plan2.steps) == 4
            assert plan2.id != plan1.id
            assert "analyze_sequence_properties" in plan2.tool_calls

    @pytest.mark.asyncio
    async def test_error_recovery_during_execution(
        self, mock_api_key: str, sample_plan_output: PlanOutput
    ) -> None:
        """Test that workflow continues when individual steps fail."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_mode_chat_client.APIKeyManager"
            ) as mock_key_manager,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_planner_prompt,
            patch("drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"),
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
            patch("langchain_openai.ChatOpenAI") as mock_finish_llm,
            patch("langchain.prompts.ChatPromptTemplate") as mock_finish_prompt,
        ):
            # Setup API key
            mock_km = MagicMock()
            mock_km.get_api_key.return_value = (mock_api_key, "test")
            mock_key_manager.return_value = mock_km

            # Setup planner
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=sample_plan_output)
            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_planner_prompt.from_messages.return_value = mock_prompt

            # Setup executor - second step fails
            step_results = [
                {
                    "output": "Success",
                    "intermediate_steps": [(MagicMock(tool="tool1"), "Result 1")],
                },
                Exception("API rate limit exceeded"),  # Step 2 fails
                {
                    "output": "Success",
                    "intermediate_steps": [(MagicMock(tool="tool3"), "Result 3")],
                },
            ]

            mock_executor = AsyncMock()
            mock_executor.ainvoke.side_effect = step_results
            mock_executor_class.return_value = mock_executor

            # Mock finish node
            mock_finish_chain = AsyncMock()
            mock_finish_chain.ainvoke = AsyncMock(
                return_value=MagicMock(content="Partial results with some failures")
            )
            mock_finish_prompt_inst = MagicMock()
            mock_finish_prompt_inst.__or__ = MagicMock(return_value=mock_finish_chain)
            mock_finish_prompt.from_messages.return_value = mock_finish_prompt_inst
            mock_finish_llm.return_value = MagicMock()

            client = AgentModeChatClient()

            # Execute workflow
            await client.create_plan("Test query")
            result = await client.approve_and_execute(approved=True)

            # Workflow should complete despite step 2 failure
            assert isinstance(result, str)

            # Check state to verify failure was recorded
            state = client.get_state()
            past_steps = state["past_steps"]

            # Should have 3 steps recorded
            assert len(past_steps) == 3

            # Step 2 should have failed
            assert past_steps[1].success is False
            assert past_steps[1].error is not None
            assert "rate limit" in past_steps[1].error.lower()

            # Steps 1 and 3 should have succeeded
            assert past_steps[0].success is True
            assert past_steps[2].success is True

    @pytest.mark.asyncio
    async def test_multi_step_context_propagation(
        self, mock_api_key: str, sample_plan_output: PlanOutput
    ) -> None:
        """Test that context is properly passed between steps."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_mode_chat_client.APIKeyManager"
            ) as mock_key_manager,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_planner_prompt,
            patch("drug_discovery_agent.interfaces.langchain.executor.ChatOpenAI"),
            patch(
                "drug_discovery_agent.interfaces.langchain.executor.AgentExecutor"
            ) as mock_executor_class,
            patch("langchain_openai.ChatOpenAI") as mock_finish_llm,
            patch("langchain.prompts.ChatPromptTemplate") as mock_finish_prompt,
        ):
            # Setup API key
            mock_km = MagicMock()
            mock_km.get_api_key.return_value = (mock_api_key, "test")
            mock_key_manager.return_value = mock_km

            # Setup planner
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=sample_plan_output)
            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_planner_prompt.from_messages.return_value = mock_prompt

            # Setup executor to capture context
            captured_contexts: list[str] = []

            async def capture_context(input_dict: dict) -> dict:
                captured_contexts.append(input_dict.get("context", ""))
                return {
                    "output": f"Step {len(captured_contexts)} complete",
                    "intermediate_steps": [
                        (
                            MagicMock(tool=f"tool{len(captured_contexts)}"),
                            f"Result {len(captured_contexts)}",
                        )
                    ],
                }

            mock_executor = AsyncMock()
            mock_executor.ainvoke.side_effect = capture_context
            mock_executor_class.return_value = mock_executor

            # Mock finish node
            mock_finish_chain = AsyncMock()
            mock_finish_chain.ainvoke = AsyncMock(
                return_value=MagicMock(content="Final result")
            )
            mock_finish_prompt_inst = MagicMock()
            mock_finish_prompt_inst.__or__ = MagicMock(return_value=mock_finish_chain)
            mock_finish_prompt.from_messages.return_value = mock_finish_prompt_inst
            mock_finish_llm.return_value = MagicMock()

            client = AgentModeChatClient()

            # Execute workflow
            await client.create_plan("Test query")
            await client.approve_and_execute(approved=True)

            # Verify context propagation
            assert len(captured_contexts) == 3

            # First step has no context
            assert captured_contexts[0] == ""

            # Second step has context from step 1
            assert "Result 1" in captured_contexts[1]

            # Third step has context from steps 1 and 2
            assert "Result 1" in captured_contexts[2]
            assert "Result 2" in captured_contexts[2]

    @pytest.mark.asyncio
    async def test_get_state_returns_current_graph_state(
        self, mock_api_key: str, sample_plan_output: PlanOutput
    ) -> None:
        """Test that get_state returns current graph state."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_mode_chat_client.APIKeyManager"
            ) as mock_key_manager,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_planner_prompt,
        ):
            # Setup API key
            mock_km = MagicMock()
            mock_km.get_api_key.return_value = (mock_api_key, "test")
            mock_key_manager.return_value = mock_km

            # Setup planner
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=sample_plan_output)
            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_planner_prompt.from_messages.return_value = mock_prompt

            client = AgentModeChatClient()

            # Create plan
            await client.create_plan("Test query")

            # Get state
            state = client.get_state()

            # Verify state structure
            assert "input" in state
            assert "plan" in state
            assert "current_step_index" in state
            assert "past_steps" in state
            assert state["input"] == "Test query"
            assert state["plan"] is not None
