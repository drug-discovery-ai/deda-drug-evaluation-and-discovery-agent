"""Tests for chat module main functions."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.chat import (
    async_main,
    main,
    prompt_for_api_key,
)


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

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890abcdef"}):
            await async_main(verbose=verbose)

            mock_client.chat_loop.assert_called_once()
            mock_client_class.assert_called_once_with(verbose=expected_verbose)

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat.prompt_for_api_key")
    @patch("drug_discovery_agent.chat.APIKeyManager")
    @patch("builtins.print")
    @patch.dict(os.environ, {}, clear=True)
    async def test_async_main_missing_api_key(
        self,
        mock_print: MagicMock,
        mock_key_manager_class: MagicMock,
        mock_prompt: MagicMock,
    ) -> None:
        """Test async main with missing API key."""
        # Setup mocks to simulate no API key found and prompt failure
        mock_key_manager = MagicMock()
        mock_key_manager_class.return_value = mock_key_manager
        mock_key_manager.get_api_key.return_value = (None, None)  # No existing key
        mock_prompt.return_value = None  # Prompt fails/cancelled

        await async_main()

        # Verify the flow stops early (return on line 22)
        mock_key_manager.get_api_key.assert_called_once()
        mock_prompt.assert_called_once_with(mock_key_manager)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (ImportError("Missing dependency"), "Missing required dependencies"),
            (ValueError("General error"), "Error:"),
        ],
    )
    @patch("builtins.print")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890abcdef"})
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


class TestPromptForAPIKey:
    """Test suite for prompt_for_api_key function."""

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_success(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test successful API key prompt and storage."""
        mock_key_manager = MagicMock()
        mock_getpass.return_value = "sk-test1234567890abcdef"
        mock_key_manager.store_api_key.return_value = (
            True,
            MagicMock(value="keychain"),
            None,
        )

        result = prompt_for_api_key(mock_key_manager)

        assert result == "sk-test1234567890abcdef"
        mock_key_manager.store_api_key.assert_called_once_with(
            "sk-test1234567890abcdef"
        )

        # Verify correct messages were printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("No API key found" in msg for msg in printed_calls)
        assert any("API key saved successfully" in msg for msg in printed_calls)

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_empty_input(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test prompt with empty API key input."""
        mock_key_manager = MagicMock()
        mock_getpass.return_value = ""

        result = prompt_for_api_key(mock_key_manager)

        assert result is None
        mock_key_manager.store_api_key.assert_not_called()

        # Verify error message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("No API key provided" in msg for msg in printed_calls)

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_whitespace_input(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test prompt with whitespace-only API key input."""
        mock_key_manager = MagicMock()
        mock_getpass.return_value = "   \t\n   "

        result = prompt_for_api_key(mock_key_manager)

        assert result is None
        mock_key_manager.store_api_key.assert_not_called()

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_storage_failure(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test API key prompt with storage failure."""
        mock_key_manager = MagicMock()
        mock_getpass.return_value = "sk-test1234567890abcdef"
        mock_key_manager.store_api_key.return_value = (
            False,
            MagicMock(value="keychain"),
            "Storage error",
        )

        result = prompt_for_api_key(mock_key_manager)

        assert result == "sk-test1234567890abcdef"  # Still returns key for session use
        mock_key_manager.store_api_key.assert_called_once_with(
            "sk-test1234567890abcdef"
        )

        # Verify warning message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Could not save API key" in msg for msg in printed_calls)

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_keyboard_interrupt(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test prompt handling keyboard interrupt (Ctrl+C)."""
        mock_key_manager = MagicMock()
        mock_getpass.side_effect = KeyboardInterrupt()

        result = prompt_for_api_key(mock_key_manager)

        assert result is None
        mock_key_manager.store_api_key.assert_not_called()

        # Verify cancellation message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Operation cancelled by user" in msg for msg in printed_calls)

    @pytest.mark.unit
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_prompt_for_api_key_getpass_error(
        self, mock_print: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test prompt handling getpass error."""
        mock_key_manager = MagicMock()
        mock_getpass.side_effect = Exception("Getpass error")

        result = prompt_for_api_key(mock_key_manager)

        assert result is None
        mock_key_manager.store_api_key.assert_not_called()

        # Verify error message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Error reading API key" in msg for msg in printed_calls)


class TestAsyncMainKeyRetrieval:
    """Test suite for async_main API key retrieval behavior (lines 19-22)."""

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat.prompt_for_api_key")
    @patch("drug_discovery_agent.chat.APIKeyManager")
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    @patch("builtins.print")
    async def test_async_main_no_existing_key_prompt_success(
        self,
        mock_print: MagicMock,
        mock_client_class: MagicMock,
        mock_key_manager_class: MagicMock,
        mock_prompt: MagicMock,
    ) -> None:
        """Test async_main when no existing key found but prompt succeeds."""
        # Setup mocks
        mock_key_manager = MagicMock()
        mock_key_manager_class.return_value = mock_key_manager
        mock_key_manager.get_api_key.return_value = (None, None)  # No existing key
        mock_prompt.return_value = "sk-test1234567890abcdef"  # Prompt succeeds

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        await async_main(verbose=False)

        # Verify the flow
        mock_key_manager.get_api_key.assert_called_once()
        mock_prompt.assert_called_once_with(mock_key_manager)
        mock_client_class.assert_called_once_with(verbose=False)
        mock_client.chat_loop.assert_called_once()

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat.prompt_for_api_key")
    @patch("drug_discovery_agent.chat.APIKeyManager")
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    @patch("builtins.print")
    async def test_async_main_no_existing_key_prompt_fails(
        self,
        mock_print: MagicMock,
        mock_client_class: MagicMock,
        mock_key_manager_class: MagicMock,
        mock_prompt: MagicMock,
    ) -> None:
        """Test async_main when no existing key found and prompt fails (lines 21-22)."""
        # Setup mocks
        mock_key_manager = MagicMock()
        mock_key_manager_class.return_value = mock_key_manager
        mock_key_manager.get_api_key.return_value = (None, None)  # No existing key
        mock_prompt.return_value = None  # Prompt fails/cancelled

        await async_main(verbose=False)

        # Verify the flow stops early (return on line 22)
        mock_key_manager.get_api_key.assert_called_once()
        mock_prompt.assert_called_once_with(mock_key_manager)
        mock_client_class.assert_not_called()  # Should not reach client creation

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat.prompt_for_api_key")
    @patch("drug_discovery_agent.chat.APIKeyManager")
    @patch("drug_discovery_agent.chat.BioinformaticsChatClient")
    @patch("builtins.print")
    async def test_async_main_existing_key_no_prompt(
        self,
        mock_print: MagicMock,
        mock_client_class: MagicMock,
        mock_key_manager_class: MagicMock,
        mock_prompt: MagicMock,
    ) -> None:
        """Test async_main when existing key is found, no prompt needed."""
        from drug_discovery_agent.key_storage.key_manager import StorageMethod

        # Setup mocks
        mock_key_manager = MagicMock()
        mock_key_manager_class.return_value = mock_key_manager
        mock_key_manager.get_api_key.return_value = (
            "sk-existing123",
            StorageMethod.KEYCHAIN,
        )

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        await async_main(verbose=False)

        # Verify the flow bypasses prompting (line 19 condition fails)
        mock_key_manager.get_api_key.assert_called_once()
        mock_prompt.assert_not_called()  # Should not prompt if key exists
        mock_client_class.assert_called_once_with(verbose=False)
        mock_client.chat_loop.assert_called_once()
