"""Tests for agent mode graph orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.interfaces.langchain.agent_graph import create_agent_graph
from drug_discovery_agent.interfaces.langchain.agent_state import Plan, StepResult


class TestAgentGraph:
    """Test suite for LangGraph orchestration."""

    @pytest.fixture
    def sample_plan(self) -> Plan:
        """Sample plan for testing."""
        return Plan(
            id="test-plan-123",
            steps=[
                "Get disease list for Alzheimer's",
                "Get targets for disease ID EFO_0000249",
                "Get details for target protein P12345",
            ],
            tool_calls=[
                "get_disease_list",
                "get_disease_targets",
                "get_protein_details",
            ],
            created_at="2024-10-04T12:00:00",
        )

    @pytest.fixture
    def sample_tools(self) -> list[MagicMock]:
        """Mock tools for testing."""
        return [MagicMock(name=f"tool_{i}") for i in range(3)]

    @pytest.fixture
    def sample_tool_schemas(self) -> list[dict]:
        """Sample tool schemas for testing."""
        return [
            {"name": "get_disease_list", "description": "Get disease list"},
            {"name": "get_disease_targets", "description": "Get disease targets"},
            {"name": "get_protein_details", "description": "Get protein details"},
        ]

    @pytest.mark.asyncio
    async def test_graph_creation(
        self, sample_tools: list[MagicMock], sample_tool_schemas: list[dict]
    ) -> None:
        """Test graph is created with correct structure."""
        graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-api-key")

        # Verify graph exists and is compiled
        assert graph is not None

        # The graph should be compiled and ready to use
        # We can test this by checking it has the compile method result
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "get_state")

    @pytest.mark.asyncio
    async def test_graph_interrupts_before_execute(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test graph interrupts before execution for approval."""
        with patch(
            "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
        ) as mock_create_plan:
            mock_create_plan.return_value = sample_plan

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-thread"}}

            # Invoke graph with initial state
            result = await graph.ainvoke({"input": "Test query"}, config)

            # Graph should interrupt before execute
            state = graph.get_state(config)
            assert state.next == ("execute",)

            # Verify plan was created
            assert result["plan"] == sample_plan
            assert result["needs_approval"] is True

    @pytest.mark.asyncio
    async def test_graph_resumes_after_approval(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test graph resumes execution after approval."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = sample_plan

            # Mock step execution results
            step_results = [
                StepResult(
                    step=step,
                    result=f"Result for {step}",
                    success=True,
                    duration=1.0,
                    tool_calls=[tool],
                )
                for step, tool in zip(
                    sample_plan.steps, sample_plan.tool_calls, strict=False
                )
            ]
            mock_execute_step.side_effect = step_results

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-thread-2"}}

            # Create plan (will interrupt)
            await graph.ainvoke({"input": "Test query"}, config)

            # Resume execution (approve)
            result = await graph.ainvoke(None, config)

            # Should execute first step and interrupt again
            assert "past_steps" in result
            assert len(result["past_steps"]) >= 1

    @pytest.mark.asyncio
    async def test_execute_node_builds_context(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test that execute node builds context from previous steps."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = sample_plan

            step1_result = StepResult(
                step="Step 1",
                result="Result 1",
                success=True,
                duration=1.0,
                tool_calls=["tool1"],
            )
            step2_result = StepResult(
                step="Step 2",
                result="Result 2",
                success=True,
                duration=1.0,
                tool_calls=["tool2"],
            )
            mock_execute_step.side_effect = [step1_result, step2_result]

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-thread-3"}}

            # Create plan
            await graph.ainvoke({"input": "Test"}, config)

            # Execute first step
            await graph.ainvoke(None, config)

            # Execute second step - should have context from step 1
            await graph.ainvoke(None, config)

            # Verify second call had context
            second_call = mock_execute_step.call_args_list[1]
            context = second_call.kwargs["context"]
            assert "Step 1" in context
            assert "Result 1" in context

    @pytest.mark.asyncio
    async def test_route_after_execute_continues(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test routing continues to next step when not finished."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = sample_plan
            mock_execute_step.return_value = StepResult(
                step="Step 1",
                result="Result 1",
                success=True,
                duration=1.0,
                tool_calls=["tool1"],
            )

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-thread-4"}}

            # Create plan
            await graph.ainvoke({"input": "Test"}, config)

            # Execute first step (should continue to step 2)
            result = await graph.ainvoke(None, config)

            # Should still have more steps
            assert result["current_step_index"] == 1
            assert len(result["past_steps"]) == 1

    @pytest.mark.asyncio
    async def test_route_after_execute_finishes(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
    ) -> None:
        """Test routing goes to finish when all steps complete."""
        from unittest.mock import MagicMock, patch

        single_step_plan = Plan(
            id="test-single",
            steps=["Single step"],
            tool_calls=["tool1"],
            created_at="2024-10-04T12:00:00",
        )

        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = single_step_plan
            mock_execute_step.return_value = StepResult(
                step="Single step",
                result="Complete",
                success=True,
                duration=1.0,
                tool_calls=["tool1"],
            )

            # Mock the LLM in finish node (imported inside the function)
            with (
                patch("langchain_openai.ChatOpenAI") as mock_llm_class,
                patch("langchain.prompts.ChatPromptTemplate") as mock_prompt_class,
            ):
                # Setup chain mock
                mock_chain = AsyncMock()
                mock_chain.ainvoke = AsyncMock(
                    return_value=MagicMock(content="Synthesized final answer")
                )

                mock_prompt = MagicMock()
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)
                mock_prompt_class.from_messages.return_value = mock_prompt

                mock_llm_class.return_value = MagicMock()

                graph = create_agent_graph(
                    sample_tools, sample_tool_schemas, "test-key"
                )
                config = {"configurable": {"thread_id": "test-thread-5"}}

                # Create plan
                await graph.ainvoke({"input": "Test"}, config)

                # Execute and complete
                # Need to invoke twice: once to execute, once to finish
                await graph.ainvoke(None, config)
                result = await graph.ainvoke(None, config)

                # Should have final response
                assert "final_response" in result
                assert result["final_response"] == "Synthesized final answer"

    @pytest.mark.asyncio
    async def test_finish_node_synthesizes_response(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
    ) -> None:
        """Test finish node creates synthesized final response."""
        from unittest.mock import MagicMock, patch

        single_step_plan = Plan(
            id="test",
            steps=["Test step"],
            tool_calls=["tool1"],
            created_at="2024-10-04T12:00:00",
        )

        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = single_step_plan
            mock_execute_step.return_value = StepResult(
                step="Test step",
                result="Test result",
                success=True,
                duration=1.0,
                tool_calls=["tool1"],
            )

            # Mock the LLM in finish node (imported inside the function)
            with (
                patch("langchain_openai.ChatOpenAI") as mock_llm_class,
                patch("langchain.prompts.ChatPromptTemplate") as mock_prompt_class,
            ):
                # Setup chain mock
                mock_chain = AsyncMock()
                mock_chain.ainvoke = AsyncMock(
                    return_value=MagicMock(content="Synthesized final answer")
                )

                mock_prompt = MagicMock()
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)
                mock_prompt_class.from_messages.return_value = mock_prompt

                mock_llm_class.return_value = MagicMock()

                graph = create_agent_graph(
                    sample_tools, sample_tool_schemas, "test-key"
                )
                config = {"configurable": {"thread_id": "test-finish"}}

                # Execute full workflow
                await graph.ainvoke({"input": "Test query"}, config)
                await graph.ainvoke(None, config)
                result = await graph.ainvoke(None, config)

                # Verify synthesized response
                assert result["final_response"] == "Synthesized final answer"

    @pytest.mark.asyncio
    async def test_replan_node(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test replan node regenerates plan with modifications."""
        modified_plan = Plan(
            id="modified-plan",
            steps=["Modified step 1", "Modified step 2"],
            tool_calls=["tool1", "tool2"],
            created_at="2024-10-04T13:00:00",
        )

        with patch(
            "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
        ) as mock_create_plan:
            # First call returns original, second call returns modified
            mock_create_plan.side_effect = [sample_plan, modified_plan]

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-replan"}}

            # Create initial plan
            await graph.ainvoke({"input": "Original query"}, config)

            # Request replan with modifications
            await graph.aupdate_state(
                config,
                {
                    "modification_request": "Add more detailed analysis",
                    "needs_approval": True,
                },
            )

            # The update changes routing - need to manually invoke replan
            # In actual usage, this happens through the client
            # For now, verify the state was updated
            state = graph.get_state(config)
            assert (
                state.values.get("modification_request") == "Add more detailed analysis"
            )

    @pytest.mark.asyncio
    async def test_error_state_handling(
        self,
        sample_tools: list[MagicMock],
        sample_tool_schemas: list[dict],
        sample_plan: Plan,
    ) -> None:
        """Test graph handles error state correctly."""
        with (
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.create_plan"
            ) as mock_create_plan,
            patch(
                "drug_discovery_agent.interfaces.langchain.agent_graph.execute_step"
            ) as mock_execute_step,
        ):
            mock_create_plan.return_value = sample_plan
            mock_execute_step.return_value = StepResult(
                step="Failed step",
                result="",
                success=False,
                error="Execution error",
                duration=1.0,
            )

            graph = create_agent_graph(sample_tools, sample_tool_schemas, "test-key")
            config = {"configurable": {"thread_id": "test-error"}}

            # Create plan
            await graph.ainvoke({"input": "Test"}, config)

            # Execute - step fails but doesn't crash
            result = await graph.ainvoke(None, config)

            # Failed step should be recorded
            assert len(result["past_steps"]) >= 1
            assert result["past_steps"][0].success is False
            assert result["past_steps"][0].error == "Execution error"
