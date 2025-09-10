from typing import Any
from unittest.mock import patch

import pytest

from drug_discovery_agent.core.alphafold import AlphaFoldClient


class TestAlphaFold:
    """Test suite for AlphaFold."""

    @pytest.fixture(autouse=True)
    def httpx_mock_client(self, request: Any) -> Any:
        """Setup httpx.AsyncClient mock for unit tests only."""
        is_integration_test = any(
            marker.name == "integration" for marker in request.node.iter_markers()
        )
        if is_integration_test:
            yield None
        else:
            with patch("httpx.AsyncClient") as mock_client:
                yield mock_client

    @pytest.fixture
    def client(self) -> AlphaFoldClient:
        """Create an EBIClient instance."""
        return AlphaFoldClient()

    @pytest.mark.unit
    async def test_fetch_target_prediction_mock(
        self,
        httpx_mock_client: Any,
        client: AlphaFoldClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test prediction retrieval with a valid UniProt accession."""
        mock_response = [
            {
                "providerId": "GDM",
                "uniprotAccession": "P42336",
                "uniprotId": "PK3CA_HUMAN",
                "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P42336-F1-model_v4.cif",
            }
        ]

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_alphafold_prediction("any")

        assert isinstance(result, list)
        assert result[0]["uniprotAccession"] == "P42336"
        assert "cifUrl" in result[0]

    # @pytest.mark.integration
    # @pytest.mark.slow
    # async def test_fetch_target_prediction_rest(
    #     self,
    #     client: AlphaFoldClient,
    # ) -> None:
    #     """Test prediction retrieval with a valid UniProt accession."""
    #     result = await client.fetch_alphafold_prediction("P42336")
    #     print(result)
    #     assert isinstance(result, list)
    #     assert result[0]["uniprotAccession"] == "P42336"
    #     assert "cifUrl" in result[0]
