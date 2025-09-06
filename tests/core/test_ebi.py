from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from drug_discovery_agent.core.ebi import EBIClient


class TestEBIClient:
    """Test suite for EBIClient."""

    @pytest.fixture(autouse=True)
    def httpx_mock_client(self) -> Any:
        """Setup httpx.AsyncClient mock for all tests in this class."""
        with patch("httpx.AsyncClient") as mock_client:
            yield mock_client

    @pytest.fixture
    def client(self) -> EBIClient:
        """Create an EBIClient instance."""
        return EBIClient()

    @pytest.mark.unit
    async def test_client_initialization(self, client: EBIClient) -> None:
        """Test EBIClient initialization."""
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_success(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful ontology ID retrieval."""
        mock_response = {
            "response": {
                "docs": [
                    {
                        "label": "Alzheimer disease",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000249",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000249",
                        "description": ["A neurodegenerative disease"],
                    },
                    {
                        "label": "Early-onset Alzheimer disease",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0009636",
                        "ontology_name": "efo",
                        "short_form": "EFO_0009636",
                        "description": ["Early onset form of Alzheimer disease"],
                    },
                    {
                        "label": "Non-EFO term",
                        "iri": "http://purl.obolibrary.org/obo/MONDO_0004975",
                        "ontology_name": "mondo",
                        "short_form": "MONDO_0004975",
                        "description": ["Should be filtered out"],
                    },
                ]
            }
        }

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("alzheimer")

        # Should only include EFO terms, not MONDO terms
        assert len(result) == 2
        assert result[0]["label"] == "Alzheimer disease"
        assert result[0]["ontology_id"] == "EFO_0000249"
        assert result[1]["label"] == "Early-onset Alzheimer disease"
        assert result[1]["ontology_id"] == "EFO_0009636"

        # Check that ontology_matches was populated
        assert len(client.ontology_matches) == 2

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_no_docs(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval with no results."""
        mock_response: dict[str, Any] = {"response": {"docs": []}}

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("nonexistent_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_no_response(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval with malformed response."""
        mock_response = {"data": "unexpected_format"}

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("test_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_http_404_error(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
        common_http_errors: Any,
    ) -> None:
        """Test ontology ID retrieval with HTTP 404 error."""
        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, None, side_effect=common_http_errors["not_found"]
        )

        result = await client.fetch_all_ontology_ids("test_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_http_500_error(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval with HTTP 500 error."""
        # Create a 500 error manually since it's not in common_http_errors
        http_500_error = httpx.HTTPStatusError(
            "Server Error", request=AsyncMock(), response=AsyncMock(status_code=500)
        )

        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, None, side_effect=http_500_error
        )

        result = await client.fetch_all_ontology_ids("test_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_timeout(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
        common_http_errors: Any,
    ) -> None:
        """Test ontology ID retrieval with timeout error."""
        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, None, side_effect=common_http_errors["timeout"]
        )

        result = await client.fetch_all_ontology_ids("test_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_connection_error(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
        common_http_errors: Any,
    ) -> None:
        """Test ontology ID retrieval with connection error."""
        http_mock_helpers.setup_httpx_mock(
            httpx_mock_client, None, side_effect=common_http_errors["connection_error"]
        )

        result = await client.fetch_all_ontology_ids("test_disease")

        assert result == []
        assert client.ontology_matches == []

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_filters_non_efo(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test that non-EFO terms are filtered out."""
        mock_response = {
            "response": {
                "docs": [
                    {
                        "label": "EFO term",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000001",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000001",
                        "description": ["An EFO term"],
                    },
                    {
                        "label": "MONDO term",
                        "iri": "http://purl.obolibrary.org/obo/MONDO_0000001",
                        "ontology_name": "mondo",
                        "short_form": "MONDO_0000001",
                        "description": ["A MONDO term"],
                    },
                    {
                        "label": "DOID term",
                        "iri": "http://purl.obolibrary.org/obo/DOID_0000001",
                        "ontology_name": "doid",
                        "short_form": "DOID_0000001",
                        "description": ["A DOID term"],
                    },
                ]
            }
        }

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("test")

        # Should only include the EFO term
        assert len(result) == 1
        assert result[0]["ontology_id"] == "EFO_0000001"
        assert result[0]["label"] == "EFO term"

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_missing_fields(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval with missing fields."""
        mock_response = {
            "response": {
                "docs": [
                    {
                        "label": "Complete term",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000001",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000001",
                        "description": ["Complete description"],
                    },
                    {
                        "label": "Missing description",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000002",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000002",
                        # description missing
                    },
                    {
                        # Missing label
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000003",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000003",
                    },
                ]
            }
        }

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("test")

        assert len(result) == 3

        # First entry should have all fields
        assert result[0]["description"] == ["Complete description"]

        # Second entry should have None for description
        assert result[1]["description"] is None
        assert result[1]["label"] == "Missing description"

        # Third entry should have None for label
        assert result[2]["label"] is None
        assert result[2]["description"] is None

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_special_characters(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval with special characters in disease name."""
        mock_response = {
            "response": {
                "docs": [
                    {
                        "label": "COVID-19",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0009932",
                        "ontology_name": "efo",
                        "short_form": "EFO_0009932",
                        "description": ["Coronavirus disease 2019"],
                    }
                ]
            }
        }

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        # Test with special characters
        result = await client.fetch_all_ontology_ids("COVID-19")

        assert len(result) == 1
        assert result[0]["label"] == "COVID-19"
        assert result[0]["ontology_id"] == "EFO_0009932"

    @pytest.mark.unit
    async def test_fetch_all_ontology_ids_empty_response(
        self,
        httpx_mock_client: Any,
        client: EBIClient,
        http_mock_helpers: Any,
    ) -> None:
        """Test ontology ID retrieval that returns empty results."""
        mock_response: dict[str, dict[str, list[dict]]] = {"response": {"docs": []}}

        http_mock_helpers.setup_httpx_mock(httpx_mock_client, mock_response)

        result = await client.fetch_all_ontology_ids("nonexistent_disease")

        assert isinstance(result, list)
        assert len(result) == 0
        assert client.ontology_matches == []
