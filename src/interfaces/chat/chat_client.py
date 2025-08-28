"""Comprehensive LangChain-based chat interface for bioinformatics analysis."""
import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Local imports
from .tools import (
    get_protein_fasta,
    get_protein_details,
    analyze_sequence_properties,
    analyze_raw_sequence,
    compare_protein_variant,
    get_top_pdb_ids_for_uniprot,
    get_structure_details,
    get_ligand_smiles_from_uniprot,
)

load_dotenv()  # Load environment variables from .env


class BioinformaticsChatClient:
    """Comprehensive LangChain-based bioinformatics chat client with conversation memory."""
    
    def __init__(self):
        """Initialize the chat client with LangChain components."""
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
        )
        
        # Load all bioinformatics tools
        self.tools = [
            get_protein_fasta,
            get_protein_details,
            analyze_sequence_properties,
            analyze_raw_sequence,
            compare_protein_variant,
            get_top_pdb_ids_for_uniprot,
            get_structure_details,
            get_ligand_smiles_from_uniprot,
        ]
        
        # Setup conversation history (20 exchanges)
        self.memory = ConversationBufferWindowMemory(
            k=20,  # Keep last 20 exchanges for context
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create agent with bioinformatics-focused prompt
        self.agent_executor = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """Create LangChain agent with bioinformatics tools and prompt."""
        
        # Bioinformatics-focused system prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert bioinformatics assistant specializing in protein analysis and molecular data.

Your capabilities include:
- Fetching protein sequences and metadata from UniProt
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

Be helpful, accurate, and thorough in your responses. Always use tools when specific data is requested."""),
            
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create OpenAI tools agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=False,  # Clean output
            handle_parsing_errors=True,
            max_iterations=5  # Prevent infinite loops
        )
    
    async def chat(self, query: str) -> str:
        """Process a single query through the LangChain agent."""
        try:
            response = await self.agent_executor.ainvoke(
                {"input": query}
            )
            return response["output"]
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"⚠️  {error_msg}")
            return error_msg
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.memory.clear()
        print("🗑️  Conversation history cleared")
    
    def _handle_commands(self, user_input: str) -> bool:
        """Handle chat commands. Returns True if command was handled."""
        user_input = user_input.strip()
        
        if user_input == "/clear":
            self.clear_conversation()
            return True
            
        elif user_input == "/help":
            self._show_help()
            return True
            
        return False
    
    def _show_help(self):
        """Display comprehensive help information."""
        print("""
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
  /quit     - Exit chat

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
        """)
    
    async def chat_loop(self):
        """Run interactive chat loop with proper error handling."""
        print("🧬 Bioinformatics Assistant")
        print("💡 Type '/help' for examples and commands, or '/quit' to exit")
        print("🔬 Ready to help with protein analysis and molecular data!\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                # Handle exit commands
                if user_input.lower() in ['/quit', 'quit', 'exit']:
                    print("\n👋 Goodbye! Happy researching!")
                    break
                
                # Skip empty inputs
                if not user_input:
                    continue
                
                # Handle simple commands
                if self._handle_commands(user_input):
                    print()  # Add spacing after commands
                    continue
                
                # Process chat query with loading indicator
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


async def main():
    """Main entry point for running the chat interface directly."""
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY not found in environment variables")
            print("💡 Please create a .env file with your OpenAI API key")
            print("   See .env.example for the required format")
            return
        
        # Initialize and run chat client
        client = BioinformaticsChatClient()
        await client.chat_loop()
        
    except ImportError as e:
        print(f"❌ Missing required dependencies: {e}")
        print("💡 Please install required packages with: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Failed to start chat client: {e}")
        print("💡 Check your configuration and try again")


if __name__ == "__main__":
    asyncio.run(main())