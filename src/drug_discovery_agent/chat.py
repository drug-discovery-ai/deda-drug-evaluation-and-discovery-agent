"""Comprehensive LangChain-based langchain interface for bioinformatics analysis."""

import argparse
import asyncio
import getpass

from drug_discovery_agent.interfaces.langchain.agent_mode_chat_client import (
    AgentModeChatClient,
)
from drug_discovery_agent.interfaces.langchain.agent_state import Plan
from drug_discovery_agent.interfaces.langchain.chat_client import (
    BioinformaticsChatClient,
)
from drug_discovery_agent.key_storage.key_manager import APIKeyManager
from drug_discovery_agent.utils.env import load_env_for_bundle


async def async_main(verbose: bool = False, agent_mode: bool = False) -> None:
    """Async entry point for running the langchain interface."""
    key_manager = APIKeyManager()
    existing_key, source = key_manager.get_api_key()

    if not existing_key:
        existing_key = prompt_for_api_key(key_manager)
        if not existing_key:
            return

    if source:
        print(f"✅ Using existing API key from {source.value}")
    else:
        print("✅ Using provided API key")

    try:
        client = BioinformaticsChatClient(verbose=verbose)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return
    except ImportError as e:
        print(f"❌ Missing required dependencies: {e}")
        print(
            "💡 Please install required packages with: pip install -r requirements.txt"
        )
        return

    print("✅ Chat client configured successfully!")

    try:
        if agent_mode:
            agent_client = AgentModeChatClient(verbose=verbose)
            print("🤖 Agent Mode enabled")
            print("Enter your research question (or 'exit' to quit):\n")

            while True:
                query = input("> ").strip()
                if query.lower() in ["exit", "quit"]:
                    break

                print("\n🤖 Agent Mode: Planning...\n")
                try:
                    plan = await agent_client.create_plan(query)

                    # Display plan
                    print("📋 Proposed Plan:")
                    print("━" * 50)
                    for i, (step, tool) in enumerate(
                        zip(plan.steps, plan.tool_calls, strict=False), 1
                    ):
                        print(f"Step {i}: {step}")
                        print(f"  Tool: {tool}")
                        print()
                    print("━" * 50)

                    # Get approval
                    while True:
                        approval = input("\nApprove? (y/n/modify): ").strip().lower()

                        if approval == "y":
                            print("\n✓ Approved - Starting execution...\n")
                            result = await agent_client.approve_and_execute(
                                approved=True
                            )
                            print("\n" + "━" * 50)
                            print("✓ Plan completed!")
                            print("━" * 50)
                            print(result)
                            break

                        elif approval == "n":
                            print("❌ Plan rejected. Let's try a different approach.")
                            break

                        elif approval == "modify":
                            modifications = input("Enter modifications: ").strip()
                            print("\n🤖 Replanning with your modifications...\n")
                            result = await agent_client.approve_and_execute(
                                False, modifications
                            )
                            if isinstance(result, Plan):
                                plan = result
                                print("📋 Proposed Plan:")
                                print("━" * 50)
                                for i, (step, tool) in enumerate(
                                    zip(plan.steps, plan.tool_calls, strict=False), 1
                                ):
                                    print(f"Step {i}: {step}")
                                    print(f"  Tool: {tool}")
                                    print()
                                print("━" * 50)
                            else:
                                print("❌ Replanning failed")
                                break

                        else:
                            print("Invalid input. Use y/n/modify")

                except Exception as e:
                    print(f"❌ Error: {e}")
        else:
            await client.chat_loop()
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
    parser.add_argument(
        "--agent-mode",
        action="store_true",
        help="Enable agent mode with plan-approve-execute workflow",
    )

    args = parser.parse_args()
    verbose = args.verbose or args.debug

    asyncio.run(async_main(verbose=verbose, agent_mode=args.agent_mode))


def prompt_for_api_key(key_manager: APIKeyManager) -> str | None:
    """Prompt user for API key and attempt to save it.

    Args:
        key_manager: APIKeyManager instance to use for saving the key

    Returns:
        The API key if successfully obtained, None if user cancelled or error occurred
    """
    print("\n🔑 No API key found. Let's configure one now.")
    print("💡 You can get an OpenAI API key from: https://platform.openai.com/api-keys")

    try:
        api_key = getpass.getpass("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ No API key provided. Exiting.")
            return None

        # Save the API key
        success, method, error = key_manager.store_api_key(api_key)
        if success:
            print(f"✅ API key saved successfully using {method.value}!")
        else:
            print(
                f"⚠️ Could not save API key ({error}), but will use it for this session."
            )

        return api_key

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        return None
    except Exception as e:
        print(f"❌ Error reading API key: {e}")
        return None


if __name__ == "__main__":
    main()
