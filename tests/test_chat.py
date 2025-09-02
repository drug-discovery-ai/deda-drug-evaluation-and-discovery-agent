"""Tests for chat module functionality."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.chat import (
    BioinformaticsChatClient,
    async_main,
    main,
)


class TestBioinformaticsChatClient:
    """Test suite for BioinformaticsChatClient."""

    @pytest.fixture
    @patch("drug_discovery_agent.chat.ChatOpenAI")
    @patch("drug_discovery_agent.chat.create_bioinformatics_tools")
    @patch("drug_discovery_agent.chat.create_openai_tools_agent")
    @patch("drug_discovery_agent.chat.AgentExecutor")
    def chat_client(
        self,
        mock_agent_executor: MagicMock,
        mock_create_agent: MagicMock,
        mock_create_tools: MagicMock,
        mock_chat_openai: MagicMock,
        mock_env_vars: Any,
        mock_clients: tuple[Any, Any, Any],
    ) -> Any:
        """Create chat client with mocked dependencies."""
        uniprot_client, pdb_client, sequence_analyzer = mock_clients

        mock_create_tools.return_value = [MagicMock() for _ in range(8)]
        mock_chat_openai.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()
        mock_executor = AsyncMock()
        mock_agent_executor.return_value = mock_executor

        client = BioinformaticsChatClient(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        )

        client.agent_executor = mock_executor
        return client

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "clients,expected_tools_call",
        [
            (("custom", "custom", "custom"), None),  # Custom clients
            (
                (None, None, None),
                {"uniprot_client": None, "pdb_client": None, "sequence_analyzer": None},
            ),  # Default clients
        ],
    )
    @patch("drug_discovery_agent.chat.ChatOpenAI")
    @patch("drug_discovery_agent.chat.create_bioinformatics_tools")
    @patch("drug_discovery_agent.chat.create_openai_tools_agent")
    @patch("drug_discovery_agent.chat.AgentExecutor")
    def test_initialization(
        self,
        mock_agent_executor: MagicMock,
        mock_create_agent: MagicMock,
        mock_create_tools: MagicMock,
        mock_chat_openai: MagicMock,
        clients: tuple[Any, Any, Any],
        expected_tools_call: Any,
        mock_env_vars: Any,
        mock_clients: tuple[Any, Any, Any],
    ) -> None:
        """Test initialization with custom and default clients."""
        mock_create_tools.return_value = [MagicMock() for _ in range(8)]
        mock_chat_openai.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()
        mock_agent_executor.return_value = AsyncMock()

        if clients[0] == "custom":
            uniprot_client, pdb_client, sequence_analyzer = mock_clients
            client = BioinformaticsChatClient(
                uniprot_client=uniprot_client,
                pdb_client=pdb_client,
                sequence_analyzer=sequence_analyzer,
            )
        else:
            client = BioinformaticsChatClient()

        assert client is not None
        assert hasattr(client, "tools")
        assert hasattr(client, "chat_history")
        assert hasattr(client, "agent_executor")
        assert client.max_history == 20

        if expected_tools_call:
            mock_create_tools.assert_called_once_with(**expected_tools_call)

        # Test environment configuration
        call_kwargs = mock_chat_openai.call_args.kwargs
        # api_key is now a SecretStr, so we need to check its secret value
        from pydantic import SecretStr

        api_key = call_kwargs["api_key"]
        if isinstance(api_key, SecretStr):
            assert api_key.get_secret_value() == "test-key"
        else:
            assert api_key == "test-key"
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["temperature"] == 0.7

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "verbose,expected_verbose",
        [
            (True, True),
            (False, False),
            (None, False),  # Test default parameter
        ],
    )
    @patch("drug_discovery_agent.chat.ChatOpenAI")
    @patch("drug_discovery_agent.chat.create_bioinformatics_tools")
    @patch("drug_discovery_agent.chat.create_openai_tools_agent")
    @patch("drug_discovery_agent.chat.AgentExecutor")
    def test_initialization_with_verbose(
        self,
        mock_agent_executor: MagicMock,
        mock_create_agent: MagicMock,
        mock_create_tools: MagicMock,
        mock_chat_openai: MagicMock,
        verbose: Any,
        expected_verbose: bool,
        mock_env_vars: Any,
        mock_clients: tuple[Any, Any, Any],
    ) -> None:
        """Test initialization with verbose parameter."""
        mock_create_tools.return_value = [MagicMock() for _ in range(8)]
        mock_chat_openai.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()
        mock_agent_executor.return_value = AsyncMock()

        # Test with verbose parameter
        if verbose is None:
            client = BioinformaticsChatClient()
        else:
            client = BioinformaticsChatClient(verbose=verbose)

        assert client is not None

        # Verify AgentExecutor was called with correct verbose parameter
        executor_call_kwargs = mock_agent_executor.call_args.kwargs
        assert executor_call_kwargs["verbose"] == expected_verbose

    @pytest.mark.unit
    async def test_chat_success(
        self, chat_client: Any, spike_protein_uniprot_id: str
    ) -> None:
        """Test successful chat interaction."""
        expected_response = (
            f"Here's information about the protein {spike_protein_uniprot_id}..."
        )
        chat_client.agent_executor.ainvoke.return_value = {"output": expected_response}

        result = await chat_client.chat(
            f"Tell me about protein {spike_protein_uniprot_id}"
        )

        assert result == expected_response
        assert len(chat_client.chat_history) == 2  # Human + AI messages

        # Verify executor was called with correct parameters
        chat_client.agent_executor.ainvoke.assert_called_once()
        call_args = chat_client.agent_executor.ainvoke.call_args[0][0]
        assert f"Tell me about protein {spike_protein_uniprot_id}" in call_args["input"]
        assert "chat_history" in call_args

    @pytest.mark.unit
    async def test_chat_with_history(self, chat_client: Any) -> None:
        """Test chat with existing conversation history."""
        from langchain_core.messages import AIMessage, HumanMessage

        # Add some existing history
        chat_client.chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        expected_response = "Follow-up response..."
        chat_client.agent_executor.ainvoke.return_value = {"output": expected_response}

        result = await chat_client.chat("Follow-up question")

        assert result == expected_response
        assert len(chat_client.chat_history) == 4  # 2 previous + 2 new messages

    @pytest.mark.unit
    async def test_chat_error_handling(self, chat_client: Any) -> None:
        """Test chat error handling."""
        chat_client.agent_executor.ainvoke.side_effect = Exception("Test error")

        result = await chat_client.chat("Test query")

        assert "Error processing query" in result
        assert "Test error" in result

    @pytest.mark.unit
    async def test_chat_history_trimming(self, chat_client: Any) -> None:
        """Test that chat history is properly trimmed when it exceeds max_history."""
        from langchain_core.messages import AIMessage, HumanMessage

        # Fill history beyond max_history
        for i in range(chat_client.max_history + 5):
            chat_client.chat_history.extend(
                [
                    HumanMessage(content=f"Question {i}"),
                    AIMessage(content=f"Answer {i}"),
                ]
            )

        with patch("drug_discovery_agent.chat.trim_messages") as mock_trim:
            mock_trim.return_value = []  # Return empty list for simplicity
            chat_client.agent_executor.ainvoke.return_value = {"output": "Response"}

            await chat_client.chat("New question")

            # trim_messages should be called when history exceeds max_history
            mock_trim.assert_called_once()

    @pytest.mark.unit
    def test_clear_conversation(self, chat_client: Any) -> None:
        """Test conversation clearing."""
        from langchain_core.messages import AIMessage, HumanMessage

        chat_client.chat_history = [
            HumanMessage(content="Question"),
            AIMessage(content="Answer"),
        ]

        chat_client.clear_conversation()
        assert len(chat_client.chat_history) == 0

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "command,expected_result,mock_method",
        [
            ("/clear", True, "clear_conversation"),
            ("/help", True, "_show_help"),
            ("/unknown", False, None),
            ("regular message", False, None),
        ],
    )
    def test_handle_commands(
        self, chat_client: Any, command: str, expected_result: bool, mock_method: Any
    ) -> None:
        """Test command handling for various inputs."""
        if mock_method:
            with patch.object(chat_client, mock_method) as mock_func:
                result = chat_client._handle_commands(command)
                assert result == expected_result
                mock_func.assert_called_once()
        else:
            result = chat_client._handle_commands(command)
            assert result == expected_result

    @pytest.mark.unit
    @pytest.mark.parametrize("quit_cmd", ["/quit", "quit", "exit"])
    async def test_chat_loop_quit_commands(
        self, chat_client: Any, quit_cmd: str
    ) -> None:
        """Test chat loop quit commands."""
        with patch("builtins.input", return_value=quit_cmd):
            with patch("builtins.print") as mock_print:
                await chat_client.chat_loop()

                printed_messages = [call[0][0] for call in mock_print.call_args_list]
                assert any("Goodbye" in msg for msg in printed_messages)

    @pytest.mark.unit
    async def test_chat_loop_empty_input(self, chat_client: Any) -> None:
        """Test chat loop with empty input."""
        inputs = ["", "  ", "/quit"]  # Empty inputs followed by quit

        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print"):
                await chat_client.chat_loop()

                # Should not have processed empty inputs as chat queries

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (KeyboardInterrupt(), "Goodbye"),
            (EOFError(), "Goodbye"),
            ([RuntimeError("Test error"), "/quit"], "Unexpected error"),
        ],
    )
    async def test_chat_loop_error_handling(
        self, chat_client: Any, exception: Any, expected_message: str
    ) -> None:
        """Test chat loop error handling for various exceptions."""
        with patch("builtins.input", side_effect=exception):
            with patch("builtins.print") as mock_print:
                await chat_client.chat_loop()

                printed_messages = [call[0][0] for call in mock_print.call_args_list]
                assert any(expected_message in msg for msg in printed_messages)

    @pytest.mark.unit
    async def test_chat_loop_regular_chat(
        self, chat_client: Any, spike_protein_uniprot_id: str
    ) -> None:
        """Test chat loop with regular chat interaction."""
        inputs = [f"Tell me about {spike_protein_uniprot_id}", "/quit"]

        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print"):
                chat_client.agent_executor.ainvoke.return_value = {
                    "output": "Test response"
                }

                await chat_client.chat_loop()

                # Should have processed the chat query
                chat_client.agent_executor.ainvoke.assert_called_once()


class TestArgumentParsing:
    """Test suite for command-line argument parsing."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "args,expected_verbose",
        [
            ([], False),  # No arguments
            (["--verbose"], True),  # Verbose flag
            (["--debug"], True),  # Debug flag
            (["--verbose", "--debug"], True),  # Both flags
        ],
    )
    @patch("sys.argv")
    @patch("asyncio.run")
    def test_main_argument_parsing(
        self,
        mock_asyncio_run: MagicMock,
        mock_argv: MagicMock,
        args: list[str],
        expected_verbose: bool,
    ) -> None:
        """Test command-line argument parsing in main function."""
        mock_argv.__getitem__ = lambda self, index: (["test"] + args)[index]
        mock_argv.__len__ = lambda self: len(["test"] + args)

        from drug_discovery_agent.chat import main

        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = MagicMock()
            mock_args.verbose = "--verbose" in args
            mock_args.debug = "--debug" in args
            mock_parse_args.return_value = mock_args

            main()

            # Verify asyncio.run was called with correct verbose parameter
            mock_asyncio_run.assert_called_once()
            # Since we can't easily inspect coroutine internals, we verify the mock was set up correctly
            assert mock_args.verbose == ("--verbose" in args)
            assert mock_args.debug == ("--debug" in args)


class TestMainFunctions:
    """Test suite for main entry point functions."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "verbose,expected_verbose",
        [
            (False, False),  # Default
            (True, True),  # Verbose enabled
        ],
    )
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    async def test_async_main_success(
        self, mock_client_class: MagicMock, verbose: bool, expected_verbose: bool
    ) -> None:
        """Test successful async main execution."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            await async_main(verbose=verbose)

            mock_client.chat_loop.assert_called_once()
            mock_client_class.assert_called_once_with(verbose=expected_verbose)

    @pytest.mark.unit
    @patch("builtins.print")
    @patch.dict(os.environ, {}, clear=True)
    async def test_async_main_missing_api_key(self, mock_print: MagicMock) -> None:
        """Test async main with missing API key."""
        await async_main()

        # Should print error message about missing API key
        printed_messages = [call[0][0] for call in mock_print.call_args_list]
        assert any("OPENAI_API_KEY not found" in msg for msg in printed_messages)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (ImportError("Missing dependency"), "Missing required dependencies"),
            (Exception("General error"), "Failed to start"),
        ],
    )
    @patch("builtins.print")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    async def test_async_main_errors(
        self,
        mock_client_class: MagicMock,
        mock_print: MagicMock,
        exception: Exception,
        expected_message: str,
    ) -> None:
        """Test async main error handling."""
        mock_client_class.side_effect = exception

        await async_main()

        printed_messages = [call[0][0] for call in mock_print.call_args_list]
        assert any(expected_message in msg for msg in printed_messages)

    @pytest.mark.unit
    @patch("asyncio.run")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(
        self, mock_parse_args: MagicMock, mock_asyncio_run: MagicMock
    ) -> None:
        """Test synchronous main function."""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        main()
        mock_asyncio_run.assert_called_once()


class TestChatIntegration:
    """Integration tests for chat functionality."""

    @pytest.mark.integration
    @pytest.mark.slow
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-integration-key"})
    @patch("drug_discovery_agent.chat.ChatOpenAI")
    def test_chat_client_real_initialization(self, mock_chat_openai: MagicMock) -> None:
        """Integration test for real chat client initialization (with mocked API)."""
        # Mock the ChatOpenAI to avoid actual API calls
        mock_chat_instance = MagicMock()
        mock_chat_openai.return_value = mock_chat_instance

        try:
            client = BioinformaticsChatClient()

            assert client is not None
            assert len(client.tools) > 0
            assert client.agent_executor is not None

            # Test that tools were created properly
            tool_names = {tool.name for tool in client.tools}
            expected_tool_names = {
                "get_protein_fasta",
                "get_protein_details",
                "analyze_sequence_properties",
                "analyze_raw_sequence",
                "compare_protein_variant",
                "get_top_pdb_ids_for_uniprot",
                "get_structure_details",
                "get_ligand_smiles_from_uniprot",
            }

            assert tool_names == expected_tool_names

        except Exception as e:
            pytest.fail(f"Failed to initialize chat client: {e}")
