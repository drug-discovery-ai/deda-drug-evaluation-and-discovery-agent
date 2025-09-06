from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from drug_discovery_agent.core.opentarget import OpenTargetsClient


class TestOpenTargetsClient:
    """Test suite for OpenTargetsClient."""

    @pytest.fixture(autouse=True)
    def httpx_mock_client(self) -> Any:
        """Setup httpx.AsyncClient mock for all tests in this class."""
        with patch("httpx.AsyncClient") as mock_client:
            yield mock_client

    @pytest.fixture
    def client(self) -> OpenTargetsClient:
        """Create an OpenTargetsClient instance."""
        return OpenTargetsClient()

    @pytest.mark.unit
    async def test_client_initialization(self, client: OpenTargetsClient) -> None:
        """Test OpenTargetsClient initialization."""
        assert client.limit == 10
        assert client.BASE_URL is not None

    @pytest.mark.unit
    async def test_fetch_disease_details_success(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful disease details retrieval."""
        mock_response_data = {
            "data": {
                "disease": {
                    "id": "EFO_0000249",
                    "name": "Alzheimer disease",
                    "description": "A neurodegenerative disease characterized by memory loss",
                }
            }
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_disease_details("EFO_0000249")

        assert result == mock_response_data["data"]

    @pytest.mark.unit
    async def test_fetch_disease_details_http_error(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
        common_http_errors: Any,
    ) -> None:
        """Test disease details retrieval with HTTP error."""
        # Create HTTP 500 error
        http_error = httpx.HTTPStatusError(
            "Server Error", request=AsyncMock(), response=AsyncMock(status_code=500)
        )

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, None, side_effect=http_error, method="post"
        )

        result = await client.fetch_disease_details("INVALID_ID")

        assert result is None

    @pytest.mark.unit
    async def test_fetch_disease_to_target_association_success(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful disease-to-target association retrieval."""
        mock_response_data = {
            "data": {
                "disease": {
                    "id": "EFO_0000249",
                    "name": "Alzheimer disease",
                    "description": "A neurodegenerative disease",
                    "associatedTargets": {
                        "rows": [
                            {
                                "target": {
                                    "approvedSymbol": "APP",
                                    "id": "ENSG00000142192",
                                    "functionDescriptions": [
                                        "Amyloid beta precursor protein"
                                    ],
                                },
                                "score": 0.95,
                            }
                        ]
                    },
                }
            }
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_disease_to_target_association("EFO_0000249")

        assert result == mock_response_data["data"]

    @pytest.mark.unit
    async def test_fetch_target_details_info_success(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful target details retrieval."""
        mock_response_data = {
            "data": {
                "target": {
                    "id": "ENSG00000142192",
                    "approvedSymbol": "APP",
                    "approvedName": "amyloid beta precursor protein",
                    "biotype": "protein_coding",
                    "functionDescriptions": ["Amyloid beta precursor protein"],
                    "geneticConstraint": [
                        {
                            "exp": 10.5,
                            "constraintType": "lof",
                            "oeLower": 0.8,
                            "upperBin6": 5,
                            "score": 0.9,
                            "obs": 9,
                            "upperRank": 100,
                        }
                    ],
                    "tractability": [
                        {"modality": "SM", "label": "High", "value": True}
                    ],
                    "proteinIds": [{"source": "uniprot", "id": "P05067"}],
                    "knownDrugs": {
                        "count": 5,
                        "rows": [
                            {
                                "targetId": "ENSG00000142192",
                                "drugId": "CHEMBL123",
                                "drugType": "Small molecule",
                                "approvedName": "Example Drug",
                            }
                        ],
                    },
                }
            }
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_target_details_info("ENSG00000142192")

        assert result == mock_response_data["data"]["target"]

    @pytest.mark.unit
    async def test_fetch_target_details_info_graphql_error(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test target details retrieval with GraphQL error."""
        mock_response_data = {
            "errors": [
                {
                    "message": "Invalid target ID",
                    "locations": [{"line": 2, "column": 3}],
                }
            ]
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_target_details_info("INVALID_ID")

        assert result is None

    @pytest.mark.unit
    async def test_fetch_target_details_info_exception(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test target details retrieval with exception."""
        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client,
            None,
            side_effect=Exception("Network error"),
            method="post",
        )

        result = await client.fetch_target_details_info("ENSG00000142192")

        assert result is None

    @pytest.mark.unit
    async def test_fetch_target_details_info_no_target_data(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test target details retrieval with no target in response."""
        mock_response_data: dict[str, Any] = {"data": {}}

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_target_details_info("ENSG00000142192")

        assert result is None

    @pytest.mark.unit
    async def test_fetch_drug_details_info_success(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful drug details retrieval."""
        mock_response_data = {
            "data": {
                "drug": {
                    "description": "A drug for Alzheimer's disease",
                    "drugType": "Small molecule",
                    "isApproved": True,
                    "crossReferences": [
                        {"ids": ["DB123", "CAS456"], "source": "drugbank"}
                    ],
                }
            }
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_drug_details_info("CHEMBL123")

        assert result == mock_response_data["data"]["drug"]

    @pytest.mark.unit
    async def test_fetch_drug_details_info_graphql_error(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test drug details retrieval with GraphQL error."""
        mock_response_data = {
            "errors": [{"message": "Drug not found", "path": ["drug"]}]
        }

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, mock_response_data, method="post"
        )

        result = await client.fetch_drug_details_info("INVALID_DRUG")

        assert result is None

    @pytest.mark.unit
    async def test_fetch_drug_details_info_exception(
        self,
        httpx_mock_client: Any,
        client: OpenTargetsClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test drug details retrieval with exception."""
        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client,
            None,
            side_effect=Exception("Network error"),
            method="post",
        )

        result = await client.fetch_drug_details_info("CHEMBL123")

        assert result is None

    @pytest.mark.unit
    @patch.object(OpenTargetsClient, "fetch_disease_to_target_association")
    @patch.object(OpenTargetsClient, "fetch_target_details_info")
    async def test_fetch_disease_associated_target_details_success(
        self,
        mock_fetch_target: AsyncMock,
        mock_fetch_association: AsyncMock,
        client: OpenTargetsClient,
    ) -> None:
        """Test successful disease-associated target details retrieval."""
        # Mock the association data
        mock_fetch_association.return_value = {
            "disease": {
                "associatedTargets": {
                    "rows": [
                        {
                            "target": {
                                "approvedSymbol": "APP",
                                "id": "ENSG00000142192",
                                "functionDescriptions": [
                                    "Amyloid beta precursor protein"
                                ],
                            },
                            "score": 0.95,
                        },
                        {
                            "target": {
                                "approvedSymbol": "PSEN1",
                                "id": "ENSG00000080815",
                                "functionDescriptions": ["Presenilin 1"],
                            },
                            "score": 0.87,
                        },
                    ]
                }
            }
        }

        # Mock target details
        mock_fetch_target.side_effect = [
            {"id": "ENSG00000142192", "approvedName": "amyloid beta precursor protein"},
            {"id": "ENSG00000080815", "approvedName": "presenilin 1"},
        ]

        result = await client.fetch_disease_associated_target_details("EFO_0000249")

        assert len(result) == 2
        assert result[0]["approved_symbol"] == "APP"
        assert result[0]["target_id"] == "ENSG00000142192"
        assert result[0]["score"] == 0.95
        assert result[1]["approved_symbol"] == "PSEN1"

        # Verify method calls
        mock_fetch_association.assert_called_once_with("EFO_0000249")
        assert mock_fetch_target.call_count == 2

    @pytest.mark.unit
    @patch.object(OpenTargetsClient, "fetch_disease_to_target_association")
    async def test_fetch_disease_associated_target_details_no_data(
        self,
        mock_fetch_association: AsyncMock,
        client: OpenTargetsClient,
    ) -> None:
        """Test disease-associated target details retrieval with no data."""
        mock_fetch_association.return_value = None

        result = await client.fetch_disease_associated_target_details("INVALID_ID")

        assert result == []

    @pytest.mark.unit
    @patch.object(OpenTargetsClient, "fetch_disease_details")
    @patch.object(OpenTargetsClient, "fetch_disease_associated_target_details")
    async def test_disease_target_knowndrug_pipeline_success(
        self,
        mock_fetch_targets: AsyncMock,
        mock_fetch_disease: AsyncMock,
        client: OpenTargetsClient,
    ) -> None:
        """Test successful disease-target-drug pipeline."""
        # Mock disease details
        mock_fetch_disease.return_value = {
            "disease": {
                "id": "EFO_0000249",
                "name": "Alzheimer disease",
                "description": "A neurodegenerative disease",
            }
        }

        # Mock target details
        mock_fetch_targets.return_value = [
            {
                "approved_symbol": "APP",
                "target_id": "ENSG00000142192",
                "description": ["Amyloid beta precursor protein"],
                "score": 0.95,
                "target_details": {"approvedName": "amyloid beta precursor protein"},
            }
        ]

        result = await client.disease_target_knowndrug_pipeline("EFO_0000249")

        assert result["disease"]["id"] == "EFO_0000249"
        assert result["disease"]["name"] == "Alzheimer disease"
        assert len(result["targets"]) == 1
        assert result["targets"][0]["approved_symbol"] == "APP"

        # Verify method calls
        mock_fetch_disease.assert_called_once_with("EFO_0000249")
        mock_fetch_targets.assert_called_once_with("EFO_0000249")

    @pytest.mark.unit
    @patch.object(OpenTargetsClient, "fetch_disease_details")
    async def test_disease_target_knowndrug_pipeline_no_disease_data(
        self,
        mock_fetch_disease: AsyncMock,
        client: OpenTargetsClient,
    ) -> None:
        """Test disease-target-drug pipeline with no disease data."""
        mock_fetch_disease.return_value = None

        result = await client.disease_target_knowndrug_pipeline("INVALID_ID")

        assert result == {}
