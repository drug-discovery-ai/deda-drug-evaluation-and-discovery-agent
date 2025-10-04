"""Planner module for generating structured execution plans."""

from datetime import datetime
from uuid import uuid4

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

from drug_discovery_agent.interfaces.langchain.agent_state import Plan

PLANNER_PROMPT = """You are a bioinformatics research planner.
Break down complex research tasks into clear, sequential steps.
Each step should use one or more of the available tools.

Available tools:
{tools_description}

Guidelines:
- Make steps atomic and specific
- Ensure steps build on previous results
- Use appropriate tools for each step
- Keep plan concise (typically 3-7 steps)
- Each step should correspond to ONE tool in the tool_calls array
- If a step needs multiple tools, break it into multiple steps

CRITICAL: When writing step descriptions, ALWAYS include the specific input parameter (ID, code, etc.):
- GOOD: "For UniProt ID P0DTC2, retrieve the FASTA sequence"
- BAD: "Retrieve the FASTA sequence for the SARS-CoV-2 spike protein"

This ensures the executor can easily extract the required parameter from the step description."""


class PlanOutput(BaseModel):
    """Structured output schema for plan generation."""

    steps: list[str]
    tool_calls: list[str]


async def create_plan(task: str, available_tools: list[dict], api_key: str) -> Plan:
    """Generate execution plan for given task using GPT-4.

    Args:
        task: User's research question or task
        available_tools: List of tool schemas with names and descriptions
        api_key: OpenAI API key

    Returns:
        Plan object with steps and tool mappings
    """
    llm = ChatOpenAI(api_key=SecretStr(api_key), model="gpt-4o", temperature=0)

    # Use structured output to ensure reliable JSON parsing
    structured_llm = llm.with_structured_output(PlanOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PLANNER_PROMPT),
            ("user", "{task}"),
        ]
    )

    tools_description = "\n".join(
        [f"- {tool['name']}: {tool['description']}" for tool in available_tools]
    )

    chain = prompt | structured_llm
    plan_output = await chain.ainvoke(
        {"task": task, "tools_description": tools_description}
    )

    # Ensure plan_output is PlanOutput type
    if not isinstance(plan_output, PlanOutput):
        raise TypeError(f"Expected PlanOutput, got {type(plan_output)}")

    return Plan(
        id=str(uuid4()),
        steps=plan_output.steps,
        tool_calls=plan_output.tool_calls,
        created_at=datetime.now().isoformat(),
    )
