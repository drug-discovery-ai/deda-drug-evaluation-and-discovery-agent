"""High-level client interface for agent mode interactions."""

from typing import cast
from uuid import uuid4

from drug_discovery_agent.interfaces.langchain.agent_graph import create_agent_graph
from drug_discovery_agent.interfaces.langchain.agent_state import AgentState, Plan
from drug_discovery_agent.interfaces.langchain.tools import create_bioinformatics_tools
from drug_discovery_agent.key_storage.key_manager import APIKeyManager


class AgentModeChatClient:
    """Client for agent mode with plan-approve-execute workflow.

    Separate from BioinformaticsChatClient for clean separation.
    """

    def __init__(self, verbose: bool = False):
        """Initialize agent mode client.

        Args:
            verbose: Enable verbose output for debugging
        """
        self.verbose = verbose

        # Get API key from key manager
        key_manager = APIKeyManager()
        api_key, _ = key_manager.get_api_key()

        if not api_key:
            raise ValueError(
                "No API key found. Please configure an OpenAI API key through environment variables, keychain, or the application settings."
            )

        self.api_key = api_key
        self.tools = create_bioinformatics_tools()

        # Extract tool schemas for planner
        self.tool_schemas = [
            {"name": tool.name, "description": tool.description} for tool in self.tools
        ]

        self.graph = create_agent_graph(self.tools, self.tool_schemas, self.api_key)
        self.thread_id = str(uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}

    async def create_plan(self, query: str) -> Plan:
        """Create execution plan for user query.

        Graph will interrupt before execution.

        Args:
            query: User's research question

        Returns:
            Plan object for user review
        """
        state = {"input": query}
        result = await self.graph.ainvoke(state, self.config)
        return cast(Plan, result["plan"])

    async def approve_and_execute(
        self, approved: bool, modifications: str | None = None
    ) -> str | Plan:
        """Approve plan and execute, or reject with modifications.

        Args:
            approved: True to execute, False to replan
            modifications: Optional modification request

        Returns:
            Final response after execution or new plan if replanning
        """
        if approved:
            # Resume execution from checkpoint - keep invoking until we get final_response
            while True:
                result = await self.graph.ainvoke(None, self.config)

                if "final_response" in result:
                    return cast(str, result["final_response"])

                if "error" in result and result["error"]:
                    return f"Execution failed with error: {result['error']}"

                # Check if there are more nodes to execute
                state = self.graph.get_state(self.config)
                if not state.next:
                    # No more nodes and no final_response - shouldn't happen but handle gracefully
                    return "Execution completed but no final response was generated."
        else:
            # Request replanning
            await self.graph.aupdate_state(
                self.config,
                {"modification_request": modifications, "needs_approval": True},
            )
            result = await self.graph.ainvoke(None, self.config)
            return cast(Plan, result.get("plan"))

    def get_state(self) -> AgentState:
        """Get current graph state."""
        state = self.graph.get_state(self.config)
        return cast(AgentState, state.values)
