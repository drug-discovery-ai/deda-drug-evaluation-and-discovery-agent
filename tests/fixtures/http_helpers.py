"""Shared HTTP mocking helpers for testing."""

from unittest.mock import AsyncMock

import httpx
import pytest


class HttpMockHelpers:
    """Helper class for HTTP mocking patterns."""

    @staticmethod
    def create_mock_http_response(response_data, status_code=200, text_data=None):
        """Helper method to create mock HTTP response."""
        mock_response = AsyncMock()
        mock_response.status_code = status_code

        if text_data is not None:
            mock_response.text = text_data
        elif response_data is not None:
            mock_response.json = lambda: response_data

        mock_response.raise_for_status = AsyncMock()
        return mock_response

    @staticmethod
    def create_structure_response(
        title="Test Structure", method="X-RAY DIFFRACTION", resolution=2.5
    ):
        """Helper method to create mock structure response data."""
        return {
            "struct": {"title": title},
            "exptl": [{"method": method}],
            "rcsb_entry_info": {"resolution_combined": [resolution]},
            "rcsb_accession_info": {"initial_release_date": "2020-02-26T00:00:00Z"},
            "struct_keywords": {"pdbx_keywords": "VIRAL PROTEIN"},
        }

    @staticmethod
    def create_entry_response(entity_ids):
        """Helper method to create mock entry response data."""
        return {
            "rcsb_entry_container_identifiers": {"non_polymer_entity_ids": entity_ids}
        }

    @staticmethod
    def create_ligand_response(pdb_id, entity_id, comp_id, name, formula):
        """Helper method to create mock ligand response data."""
        return {
            "rcsb_id": f"{pdb_id}_{entity_id}",
            "chem_comp": {"id": comp_id, "name": name, "formula": formula},
        }

    @staticmethod
    def setup_httpx_mock(
        mock_client_cls, response_data, status_code=200, side_effect=None
    ):
        """Helper method to set up httpx client mocking."""
        mock_response_obj = AsyncMock()
        mock_response_obj.status_code = status_code

        if side_effect:
            mock_async_client = AsyncMock()
            mock_async_client.get.side_effect = side_effect
        else:
            mock_response_obj.json = lambda: response_data
            if status_code == 200:
                mock_response_obj.raise_for_status = AsyncMock()

            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response_obj

        mock_client_cls.return_value.__aenter__.return_value = mock_async_client
        return mock_async_client


@pytest.fixture
def http_mock_helpers():
    """Provide HTTP mocking helper methods."""
    return HttpMockHelpers


@pytest.fixture
def common_http_errors():
    """Common HTTP error scenarios for testing."""
    return {
        "not_found": httpx.HTTPStatusError(
            "Not found", request=None, response=AsyncMock(status_code=404)
        ),
        "timeout": httpx.TimeoutException("Request timeout"),
        "connection_error": httpx.ConnectError("Connection failed"),
    }
