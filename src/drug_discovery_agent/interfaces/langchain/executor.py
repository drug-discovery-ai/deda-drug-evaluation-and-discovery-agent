"""Executor module for executing individual plan steps."""

import time

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from drug_discovery_agent.interfaces.langchain.agent_state import StepResult

EXECUTOR_PROMPT = """You are executing a single step in a research plan.

Previous context:
{context}

Current step: {input}

You have access to the following tools:

{tools}

Use the following format:

Thought: I need to identify which tool to use and extract the required input parameter from the step description
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (just the value, no quotes, no comments)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I have completed this step
Final Answer: Step completed successfully

CRITICAL INSTRUCTIONS FOR ACTION INPUT:
- Action Input must be ONLY the raw parameter value required by the tool
- Extract the key identifier from the step description (e.g., UniProt ID, PDB ID, etc.)
- Do NOT pass the entire step description or any explanatory text
- Do NOT include quotes, comments, or formatting

Example:
  Step: "Retrieve the FASTA sequence for UniProt ID P0DTC2"
  GOOD Action Input: P0DTC2
  BAD Action Input: "P0DTC2" or Retrieve the FASTA sequence for UniProt ID P0DTC2

Begin!

{agent_scratchpad}"""


async def execute_step(
    step: str, tools: list, api_key: str, context: str = ""
) -> StepResult:
    """Execute a single step using ReAct agent with available tools.

    Args:
        step: Step description to execute
        tools: List of LangChain tool instances
        api_key: OpenAI API key
        context: Results from previous steps (optional)

    Returns:
        StepResult with success status and result/error
    """
    llm = ChatOpenAI(api_key=SecretStr(api_key), model="gpt-4o-mini", temperature=0)

    # ReAct agent requires specific prompt variables: tools, tool_names, agent_scratchpad
    prompt = PromptTemplate.from_template(EXECUTOR_PROMPT)

    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,  # Disable verbose output for cleaner logs
        handle_parsing_errors=True,
        max_iterations=5,
        return_intermediate_steps=True,  # Enable access to tool outputs
    )

    start_time = time.time()

    try:
        result = await executor.ainvoke({"input": step, "context": context})

        duration = time.time() - start_time

        # Extract tool calls and outputs from intermediate_steps
        tool_calls = []
        tool_outputs = []

        # AgentExecutor returns intermediate_steps when return_intermediate_steps=True
        intermediate_steps = result.get("intermediate_steps", [])

        for action, observation in intermediate_steps:
            # Action is an AgentAction with attributes: tool, tool_input, log
            tool_name = getattr(action, "tool", None)
            if tool_name:
                tool_calls.append(tool_name)
            # Collect all tool outputs
            tool_outputs.append(str(observation))

        # Prefer the last tool output (actual data), fall back to agent output if no tools were called
        if tool_outputs:
            step_result = tool_outputs[-1]
        else:
            step_result = result.get("output", "")

        return StepResult(
            step=step,
            result=step_result,
            success=True,
            duration=duration,
            tool_calls=tool_calls,
        )

    except Exception as e:
        duration = time.time() - start_time

        return StepResult(
            step=step, result="", success=False, error=str(e), duration=duration
        )
