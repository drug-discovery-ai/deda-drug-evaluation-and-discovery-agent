from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient


class TestPDBClient:
    """Test suite for PDBClient."""

    @pytest.fixture
    def client(self, mock_uniprot_client):
        """Create a PDBClient instance with mocked UniProt client."""
        return PDBClient(uniprot_client=mock_uniprot_client)

    @pytest.fixture
    def client_with_default_uniprot(self):
        """Create a PDBClient instance with default UniProt client."""
        return PDBClient()

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_structure_details_success(
        self, mock_client_cls, client, http_mock_helpers
    ):
        """Test successful structure details retrieval."""
        mock_response = http_mock_helpers.create_structure_response(
            title="Prefusion 2019-nCoV spike glycoprotein",
            method="X-RAY DIFFRACTION",
            resolution=3.46,
        )
        mock_response["rcsb_entry_info"]["deposited_atom_count"] = 22615

        mock_http_response = http_mock_helpers.create_mock_http_response(mock_response)
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_http_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await client.get_structure_details("6VSB")

        assert result["pdb_id"] == "6VSB"
        assert result["title"] == "Prefusion 2019-nCoV spike glycoprotein"
        assert result["method"] == "X-RAY DIFFRACTION"
        assert result["resolution"] == 3.46
        assert result["deposited_atoms"] == 22615
        assert result["release_date"] == "2020-02-26T00:00:00Z"
        assert result["keywords"] == "VIRAL PROTEIN"
        assert result["structure_url"] == "https://files.rcsb.org/download/6VSB.pdb"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "error_type,expected_error",
        [
            ("not_found", "No entry found for PDB ID: INVALID"),
            ("timeout", "Request failed"),
        ],
    )
    @patch("httpx.AsyncClient")
    async def test_get_structure_details_errors(
        self, mock_client_cls, error_type, expected_error, client, common_http_errors
    ):
        """Test structure details retrieval with various errors."""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = common_http_errors[error_type]
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        pdb_id = "INVALID" if "No entry found" in expected_error else "6VSB"
        result = await client.get_structure_details(pdb_id)

        assert "error" in result
        assert expected_error in result["error"]

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_structure_details_missing_fields(
        self, mock_client_cls, client, http_mock_helpers
    ):
        """Test structure details retrieval with missing fields."""
        mock_response = {}
        mock_http_response = http_mock_helpers.create_mock_http_response(mock_response)
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_http_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await client.get_structure_details("6VSB")

        assert result["pdb_id"] == "6VSB"
        assert result["title"] is None
        assert result["method"] is None
        assert result["resolution"] is None
        assert result["deposited_atoms"] is None
        assert result["release_date"] is None
        assert result["keywords"] is None

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_ligands_for_uniprot_success(
        self,
        mock_client_cls,
        client,
        mock_uniprot_client,
        http_mock_helpers,
        spike_protein_uniprot_id,
    ):
        """Test successful ligands retrieval for UniProt ID."""
        mock_uniprot_client.get_pdb_ids.return_value = ["6VSB", "6VXX"]

        # Create test data
        responses = {
            "entry/6VSB": http_mock_helpers.create_entry_response(["3", "4"]),
            "entry/6VXX": http_mock_helpers.create_entry_response(["2"]),
            "nonpolymer_entity/6VSB/3": http_mock_helpers.create_ligand_response(
                "6VSB", "3", "NAG", "N-ACETYL-D-GLUCOSAMINE", "C8 H15 N O6"
            ),
            "nonpolymer_entity/6VSB/4": http_mock_helpers.create_ligand_response(
                "6VSB", "4", "SO4", "SULFATE ION", "O4 S"
            ),
            "nonpolymer_entity/6VXX/2": http_mock_helpers.create_ligand_response(
                "6VXX", "2", "ZN", "ZINC ION", "Zn"
            ),
        }

        def get_side_effect(url, **kwargs):
            for url_pattern, response_data in responses.items():
                if url_pattern in url:
                    return http_mock_helpers.create_mock_http_response(response_data)
            return http_mock_helpers.create_mock_http_response({}, 404)

        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = get_side_effect
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await client.get_ligands_for_uniprot(spike_protein_uniprot_id)

        assert len(result) == 3
        ligand_ids = [ligand.get("chem_comp", {}).get("id") for ligand in result]
        assert "NAG" in ligand_ids
        assert "SO4" in ligand_ids
        assert "ZN" in ligand_ids

    @pytest.mark.unit
    async def test_get_ligands_for_uniprot_no_pdb_ids(
        self, client, mock_uniprot_client, spike_protein_uniprot_id
    ):
        """Test ligands retrieval when no PDB IDs are found."""
        mock_uniprot_client.get_pdb_ids.return_value = []

        result = await client.get_ligands_for_uniprot(spike_protein_uniprot_id)

        assert result == []

    @pytest.mark.unit
    async def test_get_ligands_for_uniprot_exception(
        self, client, mock_uniprot_client, spike_protein_uniprot_id
    ):
        """Test ligands retrieval with exception handling."""
        mock_uniprot_client.get_pdb_ids.side_effect = Exception("Network error")

        result = await client.get_ligands_for_uniprot(spike_protein_uniprot_id)

        assert len(result) == 1
        assert "error" in result[0]
        assert "Network error" in result[0]["error"]

    @pytest.mark.unit
    def test_pdb_client_initialization(self):
        """Test PDBClient initialization with and without UniProt client."""
        # Test with custom UniProt client
        mock_client = MagicMock(spec=UniProtClient)
        pdb_client = PDBClient(uniprot_client=mock_client)
        assert pdb_client.uniprot_client == mock_client

        # Test with default UniProt client
        pdb_client_default = PDBClient()
        assert isinstance(pdb_client_default.uniprot_client, UniProtClient)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_structure_details_integration(
        self, client_with_default_uniprot, spike_protein_pdb_id
    ):
        """Integration test for structure details retrieval with real API."""
        # Test with known PDB structure
        result = await client_with_default_uniprot.get_structure_details(
            spike_protein_pdb_id
        )

        assert "error" not in result
        assert result["pdb_id"] == spike_protein_pdb_id
        assert result["title"] is not None
        assert "spike" in result["title"].lower()
        assert result["method"] is not None
        assert result["resolution"] is not None
        assert (
            result["structure_url"]
            == f"https://files.rcsb.org/download/{spike_protein_pdb_id}.pdb"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_structure_details_invalid_pdb_integration(
        self, client_with_default_uniprot
    ):
        """Integration test for invalid PDB ID."""
        result = await client_with_default_uniprot.get_structure_details("INVALID")

        assert "error" in result
        assert "No entry found" in result["error"]
