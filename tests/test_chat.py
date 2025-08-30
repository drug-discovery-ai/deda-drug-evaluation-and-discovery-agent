"""Tests for chat module functionality."""

import os
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
        mock_agent_executor,
        mock_create_agent,
        mock_create_tools,
        mock_chat_openai,
        mock_env_vars,
        mock_clients,
    ):
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

        client._mock_executor = mock_executor
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
        mock_agent_executor,
        mock_create_agent,
        mock_create_tools,
        mock_chat_openai,
        clients,
        expected_tools_call,
        mock_env_vars,
        mock_clients,
    ):
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
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["temperature"] == 0.7

    @pytest.mark.unit
    async def test_chat_success(self, chat_client, spike_protein_uniprot_id):
        """Test successful chat interaction."""
        expected_response = (
            f"Here's information about the protein {spike_protein_uniprot_id}..."
        )
        chat_client._mock_executor.ainvoke.return_value = {"output": expected_response}

        result = await chat_client.chat(
            f"Tell me about protein {spike_protein_uniprot_id}"
        )

        assert result == expected_response
        assert len(chat_client.chat_history) == 2  # Human + AI messages

        # Verify executor was called with correct parameters
        chat_client._mock_executor.ainvoke.assert_called_once()
        call_args = chat_client._mock_executor.ainvoke.call_args[0][0]
        assert f"Tell me about protein {spike_protein_uniprot_id}" in call_args["input"]
        assert "chat_history" in call_args

    @pytest.mark.unit
    async def test_chat_with_history(self, chat_client):
        """Test chat with existing conversation history."""
        from langchain_core.messages import AIMessage, HumanMessage

        # Add some existing history
        chat_client.chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        expected_response = "Follow-up response..."
        chat_client._mock_executor.ainvoke.return_value = {"output": expected_response}

        result = await chat_client.chat("Follow-up question")

        assert result == expected_response
        assert len(chat_client.chat_history) == 4  # 2 previous + 2 new messages

    @pytest.mark.unit
    async def test_chat_error_handling(self, chat_client):
        """Test chat error handling."""
        chat_client._mock_executor.ainvoke.side_effect = Exception("Test error")

        result = await chat_client.chat("Test query")

        assert "Error processing query" in result
        assert "Test error" in result

    @pytest.mark.unit
    async def test_chat_history_trimming(self, chat_client):
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
            chat_client._mock_executor.ainvoke.return_value = {"output": "Response"}

            await chat_client.chat("New question")

            # trim_messages should be called when history exceeds max_history
            mock_trim.assert_called_once()

    @pytest.mark.unit
    def test_clear_conversation(self, chat_client):
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
    def test_handle_commands(self, chat_client, command, expected_result, mock_method):
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
    async def test_chat_loop_quit_commands(self, chat_client, quit_cmd):
        """Test chat loop quit commands."""
        with patch("builtins.input", return_value=quit_cmd):
            with patch("builtins.print") as mock_print:
                await chat_client.chat_loop()

                printed_messages = [call[0][0] for call in mock_print.call_args_list]
                assert any("Goodbye" in msg for msg in printed_messages)

    @pytest.mark.unit
    async def test_chat_loop_empty_input(self, chat_client):
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
        self, chat_client, exception, expected_message
    ):
        """Test chat loop error handling for various exceptions."""
        with patch("builtins.input", side_effect=exception):
            with patch("builtins.print") as mock_print:
                await chat_client.chat_loop()

                printed_messages = [call[0][0] for call in mock_print.call_args_list]
                assert any(expected_message in msg for msg in printed_messages)

    @pytest.mark.unit
    async def test_chat_loop_regular_chat(self, chat_client, spike_protein_uniprot_id):
        """Test chat loop with regular chat interaction."""
        inputs = [f"Tell me about {spike_protein_uniprot_id}", "/quit"]

        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print"):
                chat_client._mock_executor.ainvoke.return_value = {
                    "output": "Test response"
                }

                await chat_client.chat_loop()

                # Should have processed the chat query
                chat_client._mock_executor.ainvoke.assert_called_once()


class TestMainFunctions:
    """Test suite for main entry point functions."""

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    async def test_async_main_success(self, mock_client_class):
        """Test successful async main execution."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            await async_main()

            mock_client.chat_loop.assert_called_once()

    @pytest.mark.unit
    @patch("builtins.print")
    @patch.dict(os.environ, {}, clear=True)
    async def test_async_main_missing_api_key(self, mock_print):
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
        self, mock_client_class, mock_print, exception, expected_message
    ):
        """Test async main error handling."""
        mock_client_class.side_effect = exception

        await async_main()

        printed_messages = [call[0][0] for call in mock_print.call_args_list]
        assert any(expected_message in msg for msg in printed_messages)

    @pytest.mark.unit
    @patch("asyncio.run")
    def test_main_function(self, mock_asyncio_run):
        """Test synchronous main function."""
        main()
        mock_asyncio_run.assert_called_once()


class TestChatIntegration:
    """Integration tests for chat functionality."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_chat_client_real_initialization(self):
        """Integration test for real chat client initialization (requires API key)."""
        # Skip if no API key available
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not available for integration test")

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
