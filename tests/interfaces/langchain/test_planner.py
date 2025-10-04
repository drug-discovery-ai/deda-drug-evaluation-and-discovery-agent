"""Tests for agent mode planner functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.interfaces.langchain.agent_state import Plan
from drug_discovery_agent.interfaces.langchain.planner import PlanOutput, create_plan


class TestPlanner:
    """Test suite for plan generation."""

    @pytest.fixture
    def sample_tools(self) -> list[dict]:
        """Sample tool schemas for testing."""
        return [
            {
                "name": "get_disease_targets",
                "description": "Retrieve therapeutic targets associated with a disease",
            },
            {
                "name": "get_protein_fasta",
                "description": "Retrieve FASTA sequence for a UniProt ID",
            },
            {
                "name": "get_protein_details",
                "description": "Get detailed information about a protein from UniProt",
            },
        ]

    @pytest.fixture
    def mock_plan_output(self) -> PlanOutput:
        """Sample structured plan output."""
        return PlanOutput(
            steps=[
                "Search for Alzheimer's disease in the ontology database",
                "For disease ID EFO_0000249, retrieve associated therapeutic targets",
                "Get detailed information for the top target protein",
            ],
            tool_calls=[
                "get_disease_list",
                "get_disease_targets",
                "get_protein_details",
            ],
        )

    @pytest.mark.asyncio
    async def test_create_plan_success(
        self, sample_tools: list[dict], mock_plan_output: PlanOutput
    ) -> None:
        """Test successful plan creation."""
        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            # Mock the entire chain
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_plan_output)

            # Mock prompt | structured_llm to return our chain
            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            # Create plan
            plan = await create_plan(
                task="Find targets for Alzheimer's disease",
                available_tools=sample_tools,
                api_key="test-api-key",
            )

            # Verify plan structure
            assert isinstance(plan, Plan)
            assert len(plan.steps) == 3
            assert len(plan.tool_calls) == 3
            assert plan.id is not None
            assert plan.created_at is not None

            # Verify steps and tool mapping
            assert "Alzheimer's" in plan.steps[0]
            assert plan.tool_calls[0] == "get_disease_list"
            assert plan.tool_calls[1] == "get_disease_targets"

    @pytest.mark.asyncio
    async def test_create_plan_includes_tool_descriptions(
        self, sample_tools: list[dict], mock_plan_output: PlanOutput
    ) -> None:
        """Test that tool descriptions are passed to LLM."""
        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_plan_output)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            await create_plan(
                task="Test task", available_tools=sample_tools, api_key="test-api-key"
            )

            # Verify LLM was called with tool descriptions
            call_args = mock_chain.ainvoke.call_args[0][0]
            assert "task" in call_args
            assert "tools_description" in call_args
            assert "get_disease_targets" in call_args["tools_description"]

    @pytest.mark.asyncio
    async def test_create_plan_with_specific_parameters(
        self, sample_tools: list[dict]
    ) -> None:
        """Test that planner creates steps with specific parameters included."""
        plan_with_params = PlanOutput(
            steps=[
                "For UniProt ID P0DTC2, retrieve the FASTA sequence",
                "Analyze sequence properties for P0DTC2",
            ],
            tool_calls=["get_protein_fasta", "analyze_sequence_properties"],
        )

        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=plan_with_params)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            plan = await create_plan(
                task="Analyze spike protein P0DTC2",
                available_tools=sample_tools,
                api_key="test-api-key",
            )

            # Verify specific parameters are in step descriptions
            assert "P0DTC2" in plan.steps[0]
            assert "P0DTC2" in plan.steps[1]

    @pytest.mark.asyncio
    async def test_create_plan_uses_gpt4o(self, sample_tools: list[dict]) -> None:
        """Test that planner uses GPT-4o model."""
        plan_output = PlanOutput(steps=["step"], tool_calls=["tool"])

        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatOpenAI"
            ) as mock_llm_class,
            patch(
                "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
            ) as mock_prompt_class,
        ):
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=plan_output)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            await create_plan(
                task="Test", available_tools=sample_tools, api_key="test-key"
            )

            # Verify GPT-4o and temperature=0
            mock_llm_class.assert_called_once()
            call_kwargs = mock_llm_class.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["temperature"] == 0

    @pytest.mark.asyncio
    async def test_create_plan_atomic_steps(self, sample_tools: list[dict]) -> None:
        """Test that steps are atomic (one tool per step)."""
        atomic_plan = PlanOutput(
            steps=[
                "Get disease list for diabetes",
                "Get targets for disease ID EFO_0000400",
                "Get FASTA sequence for UniProt ID P12345",
            ],
            tool_calls=["get_disease_list", "get_disease_targets", "get_protein_fasta"],
        )

        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=atomic_plan)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            plan = await create_plan(
                task="Research diabetes", available_tools=sample_tools, api_key="test"
            )

            # Each step should have exactly one corresponding tool
            assert len(plan.steps) == len(plan.tool_calls)

    @pytest.mark.asyncio
    async def test_create_plan_error_handling(self, sample_tools: list[dict]) -> None:
        """Test error handling when LLM fails."""
        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            # Should propagate the error
            with pytest.raises(Exception, match="LLM API error"):
                await create_plan(
                    task="Test", available_tools=sample_tools, api_key="test"
                )

    @pytest.mark.asyncio
    async def test_plan_id_uniqueness(self, sample_tools: list[dict]) -> None:
        """Test that each plan gets a unique ID."""
        plan_output = PlanOutput(steps=["step"], tool_calls=["tool"])

        with patch(
            "drug_discovery_agent.interfaces.langchain.planner.ChatPromptTemplate"
        ) as mock_prompt_class:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=plan_output)

            mock_prompt = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_prompt_class.from_messages.return_value = mock_prompt

            plan1 = await create_plan(
                task="Task 1", available_tools=sample_tools, api_key="test"
            )
            plan2 = await create_plan(
                task="Task 2", available_tools=sample_tools, api_key="test"
            )

            # Plans should have different IDs
            assert plan1.id != plan2.id
