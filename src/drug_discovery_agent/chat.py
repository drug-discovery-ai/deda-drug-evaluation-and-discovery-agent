"""Comprehensive LangChain-based langchain interface for bioinformatics analysis."""

import argparse
import asyncio
import os

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, trim_messages
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient

# Local imports
from drug_discovery_agent.interfaces.langchain.tools import create_bioinformatics_tools
from drug_discovery_agent.utils.env import load_env_for_bundle


class BioinformaticsChatClient:
    """Comprehensive LangChain-based bioinformatics langchain client with conversation memory."""

    def __init__(
        self,
        uniprot_client: UniProtClient | None = None,
        pdb_client: PDBClient | None = None,
        sequence_analyzer: SequenceAnalyzer | None = None,
        verbose: bool = False,
    ):
        """Initialize the langchain client with LangChain components.

        Args:
            uniprot_client: UniProt client instance. Creates default if None.
            pdb_client: PDB client instance. Creates default if None.
            sequence_analyzer: Sequence analyzer instance. Creates default if None.
            verbose: Enable verbose output for debugging tool selection.
        """
        # Initialize LangChain components
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            api_key=SecretStr(api_key) if api_key else None,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
        )

        # Create bioinformatics tools with optional client injection
        self.tools = create_bioinformatics_tools(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        )

        # Setup conversation history (keep last 20 messages)
        self.chat_history: list[BaseMessage] = []
        self.max_history = 20

        # Create agent with bioinformatics-focused prompt
        self.agent_executor = self._create_agent(verbose=verbose)

    def _create_agent(self, verbose: bool = False) -> AgentExecutor:
        """Create LangChain agent with bioinformatics tools and prompt."""

        # Bioinformatics-focused system prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert bioinformatics assistant specializing in protein analysis and molecular data.

Your capabilities include:
- Fetching diseases and their related targets in the human body from the European Bioinformatics Institute (EMBL-EBI) and OpenTargets
- Fetching Target associated protein sequences and metadata from UniProt
- Analyzing protein properties (molecular weight, isoelectric point, composition)
- Working with PDB structures and experimental data
- Comparing protein variants and mutations
- Analyzing raw amino acid sequences
- Finding ligands associated with proteins
- Providing insights on protein function and structure

Guidelines:
- Use the available tools to fetch accurate, up-to-date data
- Explain complex concepts clearly and provide context
- When analyzing proteins, include relevant structural and functional insights
- Always validate UniProt IDs and handle errors gracefully
- For mutations, use standard notation (e.g., D614G means aspartate at position 614 changed to glycine)
- Provide detailed explanations of results and their biological significance
- When showing data, format it clearly and highlight important findings

Be helpful, accurate, and thorough in your responses. Always use tools when specific data is requested.""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create OpenAI tools agent
        agent = create_openai_tools_agent(llm=self.llm, tools=self.tools, prompt=prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=verbose,  # Show tool selection when enabled
            handle_parsing_errors=True,
            max_iterations=5,  # Prevent infinite loops
        )

    async def chat(self, query: str) -> str:
        """Process a single query through the LangChain agent."""
        try:
            # Trim chat history to keep only the last max_history messages
            if len(self.chat_history) > self.max_history:
                self.chat_history = trim_messages(
                    self.chat_history,
                    token_counter=len,
                    max_tokens=self.max_history,
                    strategy="last",
                    start_on="human",
                    include_system=True,
                    allow_partial=False,
                )

            response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": self.chat_history}
            )

            # Add the current exchange to chat history
            self.chat_history.append(HumanMessage(content=query))
            self.chat_history.append(AIMessage(content=response["output"]))

            return str(response["output"])

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"⚠️  {error_msg}")
            return error_msg

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.chat_history.clear()
        print("🗑️  Conversation history cleared")

    def _handle_commands(self, user_input: str) -> bool:
        """Handle langchain commands. Returns True if command was handled."""
        user_input = user_input.strip()

        if user_input == "/clear":
            self.clear_conversation()
            return True

        elif user_input == "/help":
            self._show_help()
            return True

        return False

    def _show_help(self) -> None:
        """Display comprehensive help information."""
        print(
            """
🧬 Bioinformatics Assistant - Help

CHAT EXAMPLES:
  Basic Queries:
  • "Show me details for UniProt ID P0DTC2"
  • "Get the FASTA sequence for P0DTC2"
  • "Analyze the properties of protein P0DTC2"

  Advanced Analysis:
  • "Compare D614G mutation in spike protein P0DTC2"
  • "Find PDB structures for UniProt ID P0DTC2"
  • "What ligands are associated with protein P0DTC2?"
  • "Analyze this raw sequence: MFVFLVLLPL..."

  Research Workflows:
  • "I'm studying SARS-CoV-2 spike protein. Get me the sequence, analyze its properties, and find available structures"
  • "Compare the molecular weight changes for mutations D614G and N501Y in P0DTC2"

COMMANDS:
  /clear    - Clear conversation history
  /help     - Show this help
  /quit     - Exit langchain

AVAILABLE TOOLS:
  • get_protein_fasta - Retrieve FASTA sequences from UniProt
  • get_protein_details - Get protein metadata and functional information
  • analyze_sequence_properties - Calculate MW, pI, composition from UniProt ID
  • analyze_raw_sequence - Analyze properties of raw amino acid sequences
  • compare_protein_variant - Compare mutated vs wildtype proteins
  • get_top_pdb_ids_for_uniprot - Find PDB structures for proteins
  • get_structure_details - Get detailed PDB structure information
  • get_ligand_smiles_from_uniprot - Find ligands associated with proteins

TIPS:
  • UniProt IDs are typically 6-10 characters (e.g., P0DTC2, Q9NZC2)
  • Mutations use standard notation: original amino acid + position + new amino acid
  • The assistant maintains conversation context for follow-up questions
  • All data is fetched from authoritative sources (UniProt, PDB, RCSB)
        """
        )

    async def chat_loop(self) -> None:
        """Run interactive langchain loop with proper error handling."""
        print("🧬 Bioinformatics Assistant")
        print("💡 Type '/help' for examples and commands, or '/quit' to exit")
        print("🔬 Ready to help with protein analysis and molecular data!\n")

        while True:
            try:
                user_input = input("You: ").strip()

                # Handle exit commands
                if user_input.lower() in ["/quit", "quit", "exit"]:
                    print("\n👋 Goodbye! Happy researching!")
                    break

                # Skip empty inputs
                if not user_input:
                    continue

                # Handle simple commands
                if self._handle_commands(user_input):
                    print()  # Add spacing after commands
                    continue

                # Process langchain query with loading indicator
                print("🤔 Analyzing...", end="", flush=True)
                response = await self.chat(user_input)
                print(f"\r🧬 Assistant: {response}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Happy researching!")
                break
            except EOFError:
                print("\n\n👋 Goodbye! Happy researching!")
                break
            except Exception as e:
                print(f"\n⚠️  Unexpected error: {str(e)}")
                print("💡 Try '/help' for usage examples or '/quit' to exit\n")


async def async_main(verbose: bool = False) -> None:
    """Async entry point for running the langchain interface."""
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY not found in environment variables")
            print("💡 Please create a .env file with your OpenAI API key")
            print("   See .env.example for the required format")
            return

        # Initialize and run langchain client
        client = BioinformaticsChatClient(verbose=verbose)
        await client.chat_loop()

    except ImportError as e:
        print(f"❌ Missing required dependencies: {e}")
        print(
            "💡 Please install required packages with: pip install -r requirements.txt"
        )
    except Exception as e:
        print(f"❌ Failed to start langchain client: {e}")
        print("💡 Check your configuration and try again")


def main() -> None:
    """Synchronous entry point that runs the async main function."""
    load_env_for_bundle()
    parser = argparse.ArgumentParser(
        description="Bioinformatics Assistant - Interactive chat interface for protein analysis"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output showing tool selection and execution details",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode (same as --verbose)"
    )

    args = parser.parse_args()
    verbose = args.verbose or args.debug

    asyncio.run(async_main(verbose=verbose))


if __name__ == "__main__":
    main()
