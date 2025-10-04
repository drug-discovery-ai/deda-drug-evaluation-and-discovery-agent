"""LangGraph orchestration for plan-approve-execute workflow."""

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from drug_discovery_agent.interfaces.langchain.agent_state import AgentState
from drug_discovery_agent.interfaces.langchain.executor import execute_step
from drug_discovery_agent.interfaces.langchain.planner import create_plan

SYNTHESIS_PROMPT = """You are a bioinformatics research assistant summarizing the results of a multi-step analysis.

Given the original task and the results from each step, provide a concise, well-structured final answer that:
1. Directly answers the user's original question
2. Synthesizes key findings across all steps
3. Presents information in a clear, organized format
4. Omits unnecessary technical details unless critical to the answer
5. Uses markdown formatting (bullet points, headers, etc.) for readability

Do NOT simply list all step results. Instead, intelligently combine and present the information."""


def create_agent_graph(tools: list, tool_schemas: list[dict], api_key: str) -> Any:
    """Create LangGraph for agent mode workflow.

    Args:
        tools: LangChain tool instances for execution
        tool_schemas: Tool descriptions for planning
        api_key: OpenAI API key

    Returns:
        Compiled graph with checkpointing
    """
    graph = StateGraph(AgentState)

    # --- Node Functions ---

    async def plan_node(state: AgentState) -> AgentState:
        """Generate initial plan."""
        plan = await create_plan(state["input"], tool_schemas, api_key)
        return {
            **state,
            "plan": plan,
            "needs_approval": True,
            "current_step_index": 0,
            "past_steps": [],
        }

    async def replan_node(state: AgentState) -> AgentState:
        """Regenerate plan based on user modifications."""
        # Use modification_request if provided
        modified_task = state.get("modification_request") or state["input"]
        plan = await create_plan(modified_task, tool_schemas, api_key)
        return {**state, "plan": plan, "needs_approval": True}

    async def execute_node(state: AgentState) -> AgentState:
        """Execute current step."""
        plan = state["plan"]
        if plan is None:
            return {**state, "error": "No plan available"}
        idx = state["current_step_index"]

        # Print clean progress indicator
        print(f"\n🔄 Step {idx + 1}/{len(plan.steps)}: {plan.steps[idx]}")
        print(f"   Tool: {plan.tool_calls[idx]}")

        # Build context from previous steps
        context = "\n".join(
            [
                f"Step {i + 1}: {s.step}\nResult: {s.result}"
                for i, s in enumerate(state["past_steps"])
            ]
        )

        # Execute step
        result = await execute_step(
            step=plan.steps[idx], tools=tools, api_key=api_key, context=context
        )

        # Print completion status
        if result.success:
            print(f"   ✓ Completed in {result.duration:.2f}s")
        else:
            print(f"   ✗ Failed: {result.error}")

        # Update state
        past_steps = state["past_steps"] + [result]
        next_idx = idx + 1

        return {
            **state,
            "past_steps": past_steps,
            "current_step_index": next_idx,
        }

    async def finish_node(state: AgentState) -> AgentState:
        """Compile final response from all step results."""
        from langchain.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        # Build context from all steps
        steps_context = []
        for i, step_result in enumerate(state["past_steps"], 1):
            steps_context.append(f"Step {i}: {step_result.step}")
            if step_result.success:
                steps_context.append(f"Result: {step_result.result}")
            else:
                steps_context.append(f"Error: {step_result.error}")

        # Use LLM to synthesize a concise final answer
        llm = ChatOpenAI(api_key=SecretStr(api_key), model="gpt-4o-mini", temperature=0)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYNTHESIS_PROMPT),
                (
                    "user",
                    """Original task: {task}

Step-by-step results:
{steps}

Provide the final answer:""",
                ),
            ]
        )

        chain = prompt | llm
        response = await chain.ainvoke(
            {"task": state["input"], "steps": "\n".join(steps_context)}
        )

        # Extract string content from response
        content = response.content
        if isinstance(content, list):
            # Join list items if content is a list
            final_text = " ".join(str(item) for item in content)
        else:
            final_text = str(content)

        return {**state, "final_response": final_text}

    # --- Routing Functions ---

    def route_after_execute(state: AgentState) -> str:
        """Decide next action after executing a step."""
        if state.get("error"):
            return "error"
        plan = state["plan"]
        if plan and state["current_step_index"] < len(plan.steps):
            return "continue"
        return "finish"

    # --- Build Graph ---

    graph.add_node("plan", plan_node)
    graph.add_node("replan", replan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("finish", finish_node)

    # Set entry point
    graph.set_entry_point("plan")

    # Plan -> Execute (with interrupt for approval)
    graph.add_edge("plan", "execute")

    # Replan -> Execute
    graph.add_edge("replan", "execute")

    # Execute -> Continue/Finish/Error
    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {"continue": "execute", "finish": "finish", "error": END},
    )

    # Finish -> End
    graph.add_edge("finish", END)

    # Compile with checkpointing and interrupt
    checkpointer = MemorySaver()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute"],  # Pause before first execution
    )
