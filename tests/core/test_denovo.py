import pytest

from drug_discovery_agent.core.denovo.preprocessor import PreprocessorClient


class TestDenovoConfigGenerator:
    @pytest.fixture
    def mock_preprocessor(self) -> PreprocessorClient:
        """Fixture to provide a mock PreprocessorClient instance."""
        client = PreprocessorClient(denovo_tool_name="test-model")
        return client

    def test_preprocess_success(self, mock_preprocessor: PreprocessorClient) -> None:
        """Test that preprocess() correctly processes valid input."""
        pass
