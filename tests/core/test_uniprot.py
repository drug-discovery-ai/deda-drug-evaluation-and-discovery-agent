from typing import Any
from unittest.mock import patch

import pytest

from drug_discovery_agent.core.uniprot import UniProtClient


class TestUniProtClient:
    """Test suite for UniProtClient."""

    @pytest.fixture
    def client(self) -> UniProtClient:
        """Create a UniProtClient instance."""
        return UniProtClient()

    @pytest.mark.unit
    @patch("drug_discovery_agent.core.uniprot.make_fasta_request")
    async def test_get_fasta_sequence_success(
        self, mock_request: Any, client: UniProtClient
    ) -> None:
        """Test successful FASTA sequence retrieval."""
        expected_fasta = """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT"""

        mock_request.return_value = expected_fasta

        result = await client.get_fasta_sequence("P0DTC2")

        assert result == expected_fasta
        mock_request.assert_called_once_with(
            "https://rest.uniprot.org/uniprotkb/P0DTC2.fasta"
        )

    @pytest.mark.unit
    @patch("drug_discovery_agent.core.uniprot.make_fasta_request")
    async def test_get_fasta_sequence_empty_response(
        self, mock_request: Any, client: UniProtClient
    ) -> None:
        """Test FASTA sequence retrieval with empty response."""
        mock_request.return_value = None

        result = await client.get_fasta_sequence("INVALID")

        assert result == ""

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_details_success(
        self,
        mock_client_cls: Any,
        client: UniProtClient,
        mock_uniprot_details_response: Any,
        http_mock_helpers: Any,
    ) -> None:
        """Test successful protein details retrieval."""
        http_mock_helpers.setup_httpx_mock(
            mock_client_cls, mock_uniprot_details_response
        )

        result = await client.get_details("P0DTC2")

        assert result["accession"] == "P0DTC2"
        assert result["organism"] == "Severe acute respiratory syndrome coronavirus 2"
        assert result["lineage"] == "Viruses → Riboviria → Orthornavirae"
        assert result["taxonomy_id"] == 2697049
        assert result["hosts"] == "Homo sapiens(Human)"
        assert result["function"] == "Attaches the virion to the cell membrane"
        assert result["virus_protein_name"] == "Spike glycoprotein"
        assert result["virus_protein_sequence"] == "MFVFLVLLPLVSSQCV"
        assert "Reference" in result

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_details_http_error(
        self, mock_client_cls: Any, client: UniProtClient, http_mock_helpers: Any
    ) -> None:
        """Test protein details retrieval with HTTP error."""
        http_mock_helpers.setup_httpx_mock(mock_client_cls, None, status_code=404)

        result = await client.get_details("INVALID")

        assert "error" in result
        assert result["status_code"] == 404
        assert "Could not retrieve data" in result["error"]

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_details_missing_fields(
        self,
        mock_client_cls: Any,
        client: UniProtClient,
        http_mock_helpers: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test protein details retrieval with missing fields."""
        minimal_response = {"primaryAccession": spike_protein_uniprot_id}
        http_mock_helpers.setup_httpx_mock(mock_client_cls, minimal_response)

        result = await client.get_details(spike_protein_uniprot_id)

        assert result["accession"] == spike_protein_uniprot_id
        assert result["organism"] is None
        assert result["lineage"] == ""
        assert result["taxonomy_id"] == "NONE"
        assert result["hosts"] == ""
        assert result["virus_protein_name"] == "Unknown"

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_pdb_ids_success(
        self,
        mock_client_cls: Any,
        client: UniProtClient,
        mock_uniprot_pdb_response: Any,
        http_mock_helpers: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test successful PDB IDs retrieval."""
        http_mock_helpers.setup_httpx_mock(mock_client_cls, mock_uniprot_pdb_response)

        result = await client.get_pdb_ids(spike_protein_uniprot_id)

        assert result == ["6VSB", "6VXX"]
        assert len(result) == 2  # Duplicates removed

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_pdb_ids_no_pdb_refs(
        self,
        mock_client_cls: Any,
        client: UniProtClient,
        http_mock_helpers: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test PDB IDs retrieval with no PDB cross-references."""
        no_pdb_response = {
            "uniProtKBCrossReferences": [{"database": "EMBL", "id": "MT326090"}]
        }
        http_mock_helpers.setup_httpx_mock(mock_client_cls, no_pdb_response)

        result = await client.get_pdb_ids(spike_protein_uniprot_id)

        assert result == []

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_pdb_ids_http_error(
        self, mock_client_cls: Any, client: UniProtClient, http_mock_helpers: Any
    ) -> None:
        """Test PDB IDs retrieval with HTTP error."""
        http_mock_helpers.setup_httpx_mock(
            mock_client_cls, None, side_effect=Exception("HTTP error")
        )

        result = await client.get_pdb_ids("INVALID")

        assert result == []

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_get_pdb_ids_timeout(
        self,
        mock_client_cls: Any,
        client: UniProtClient,
        http_mock_helpers: Any,
        common_http_errors: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test PDB IDs retrieval with timeout."""
        http_mock_helpers.setup_httpx_mock(
            mock_client_cls, None, side_effect=common_http_errors["timeout"]
        )

        result = await client.get_pdb_ids(spike_protein_uniprot_id)

        assert result == []

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_fasta_sequence_integration(self, client: UniProtClient) -> None:
        """Integration test for FASTA sequence retrieval with real API."""
        # Test with known SARS-CoV-2 spike protein
        result = await client.get_fasta_sequence("P0DTC2")

        assert result != ""
        assert result.startswith(">sp|P0DTC2")
        assert "SPIKE_SARS2" in result
        assert "MFVFLVLLPLVSSQC" in result  # Start of spike protein sequence

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_details_integration(self, client: UniProtClient) -> None:
        """Integration test for protein details retrieval with real API."""
        # Test with known SARS-CoV-2 spike protein
        result = await client.get_details("P0DTC2")

        assert "error" not in result
        assert result["accession"] == "P0DTC2"
        assert "coronavirus" in result["organism"].lower()
        assert result["virus_protein_name"] == "Spike glycoprotein"
        assert result["taxonomy_id"] == 2697049

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_pdb_ids_integration(
        self,
        client: UniProtClient,
        spike_protein_uniprot_id: str,
        spike_protein_pdb_id: str,
    ) -> None:
        """Integration test for PDB IDs retrieval with real API."""
        # Test with known SARS-CoV-2 spike protein
        result = await client.get_pdb_ids(spike_protein_uniprot_id)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(len(pdb_id) == 4 for pdb_id in result)
        assert spike_protein_pdb_id in result  # Known structure for spike protein
