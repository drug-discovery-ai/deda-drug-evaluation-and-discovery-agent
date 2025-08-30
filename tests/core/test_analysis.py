from unittest.mock import MagicMock

import pytest

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.uniprot import UniProtClient


class TestSequenceAnalyzer:
    """Test suite for SequenceAnalyzer."""

    @pytest.fixture
    def analyzer(self, mock_uniprot_client):
        """Create a SequenceAnalyzer instance with mocked UniProt client."""
        return SequenceAnalyzer(uniprot_client=mock_uniprot_client)

    @pytest.fixture
    def analyzer_with_default_uniprot(self):
        """Create a SequenceAnalyzer instance with default UniProt client."""
        return SequenceAnalyzer()

    @pytest.mark.unit
    async def test_analyze_from_uniprot_success(
        self, analyzer, mock_uniprot_client, sample_fasta, spike_protein_uniprot_id
    ):
        """Test successful sequence analysis from UniProt."""
        mock_uniprot_client.get_fasta_sequence.return_value = sample_fasta

        result = await analyzer.analyze_from_uniprot(spike_protein_uniprot_id)

        assert "error" not in result
        assert result["length"] == 69  # Length of the sequence after header
        assert result["molecular_weight_kda"] > 0
        assert result["isoelectric_point"] > 0
        assert "composition" in result
        assert isinstance(result["composition"], dict)

        # Check that common amino acids are present in composition
        expected_sequence = sample_fasta.split("\n")[1]  # Extract sequence from fixture
        for aa in set(expected_sequence):
            assert aa in result["composition"]

    @pytest.mark.unit
    def test_analyze_raw_sequence_success(self, analyzer, sample_sequence):
        """Test successful raw sequence analysis."""
        result = analyzer.analyze_raw_sequence(sample_sequence)

        assert "error" not in result
        assert result["length"] == len(sample_sequence)
        assert result["molecular_weight_kda"] > 0
        assert result["isoelectric_point"] > 0
        assert "composition" in result

        # Check composition correctness
        for aa in set(sample_sequence):
            assert result["composition"][aa] == sample_sequence.count(aa)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "test_type,sequence_data,expected_error",
        [
            (
                "uniprot",
                {
                    "fasta": """>sp|TEST|TEST Test protein
MKTVRQERLXZ""",
                    "uniprot_id": "TEST",
                },
                "canonical amino acids",
            ),
            ("raw", {"sequence": "MKTVRQERLXZ"}, "Invalid sequence"),
        ],
    )
    async def test_invalid_amino_acids(
        self, analyzer, mock_uniprot_client, test_type, sequence_data, expected_error
    ):
        """Test sequence analysis with invalid amino acids for both UniProt and raw sequences."""
        if test_type == "uniprot":
            mock_uniprot_client.get_fasta_sequence.return_value = sequence_data["fasta"]
            result = await analyzer.analyze_from_uniprot(sequence_data["uniprot_id"])
        else:
            result = analyzer.analyze_raw_sequence(sequence_data["sequence"])

        assert "error" in result
        assert "Invalid sequence" in result["error"]
        if expected_error == "canonical amino acids":
            assert "canonical amino acids" in result["error"]

    @pytest.mark.unit
    async def test_analyze_from_uniprot_empty_sequence(
        self, analyzer, mock_uniprot_client
    ):
        """Test sequence analysis with empty sequence."""
        empty_fasta = ">sp|TEST|TEST Test protein\n"
        mock_uniprot_client.get_fasta_sequence.return_value = empty_fasta

        result = await analyzer.analyze_from_uniprot("TEST")

        assert result["length"] == 0
        assert result["molecular_weight_kda"] == 0
        assert result["composition"] == {}

    @pytest.mark.unit
    def test_analyze_raw_sequence_lowercase(self, analyzer):
        """Test raw sequence analysis with lowercase input."""
        lowercase_sequence = "mktvrqerl"

        result = analyzer.analyze_raw_sequence(lowercase_sequence)

        assert "error" not in result
        assert result["length"] == 9
        assert result["molecular_weight_kda"] > 0

    @pytest.mark.unit
    def test_analyze_raw_sequence_empty(self, analyzer):
        """Test raw sequence analysis with empty sequence."""
        result = analyzer.analyze_raw_sequence("")

        assert result["length"] == 0
        assert result["molecular_weight_kda"] == 0
        assert result["composition"] == {}

    @pytest.mark.unit
    async def test_compare_variant_success(
        self, analyzer, mock_uniprot_client, sample_fasta, spike_protein_uniprot_id
    ):
        """Test successful variant comparison."""
        wild_fasta = sample_fasta.replace(
            sample_fasta.split("\n")[1], "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNDD"
        )  # D at position 31
        mock_uniprot_client.get_fasta_sequence.return_value = wild_fasta

        result = await analyzer.compare_variant(spike_protein_uniprot_id, "D31G")

        assert "error" not in result
        assert result["mutation"] == "D31G"
        assert result["position"] == 31
        assert result["amino_acid_change"] == "D → G"
        assert "wildtype" in result
        assert "variant" in result

        # Check that both analyses have required fields
        for analysis in [result["wildtype"], result["variant"]]:
            assert "length" in analysis
            assert "molecular_weight_kda" in analysis
            assert "isoelectric_point" in analysis
            assert "composition" in analysis

    @pytest.mark.unit
    async def test_compare_variant_invalid_format(
        self, analyzer, mock_uniprot_client, spike_protein_uniprot_id
    ):
        """Test variant comparison with invalid mutation format."""
        wild_fasta = ">sp|P0DTC2|SPIKE_SARS2\nMFVFLVLLPLVSSQCV"
        mock_uniprot_client.get_fasta_sequence.return_value = wild_fasta

        # Test key invalid formats that don't match the regex pattern
        invalid_mutations = ["D", "6G", "", "D-6-G"]

        for mutation in invalid_mutations:
            result = await analyzer.compare_variant(spike_protein_uniprot_id, mutation)
            assert "error" in result
            assert "Invalid mutation format" in result["error"]

    @pytest.mark.unit
    async def test_compare_variant_reference_mismatch(
        self, analyzer, mock_uniprot_client, sample_fasta, spike_protein_uniprot_id
    ):
        """Test variant comparison with reference amino acid mismatch."""
        wild_fasta = sample_fasta.replace(
            sample_fasta.split("\n")[1], "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNDD"
        )  # D at position 31
        mock_uniprot_client.get_fasta_sequence.return_value = wild_fasta

        result = await analyzer.compare_variant(
            spike_protein_uniprot_id, "G31D"
        )  # G not D at position 31

        assert "error" in result
        assert "Reference mismatch" in result["error"]
        assert "expected G at position 31, found D" in result["error"]

    @pytest.mark.unit
    async def test_compare_variant_case_insensitive_mutation(
        self, analyzer, mock_uniprot_client, sample_fasta, spike_protein_uniprot_id
    ):
        """Test variant comparison with case-insensitive mutation format."""
        wild_fasta = sample_fasta.replace(
            sample_fasta.split("\n")[1], "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNDD"
        )  # D at position 31
        mock_uniprot_client.get_fasta_sequence.return_value = wild_fasta

        result = await analyzer.compare_variant(spike_protein_uniprot_id, "d31g")

        assert "error" not in result
        assert result["mutation"] == "d31g"
        assert result["amino_acid_change"] == "D → G"

    @pytest.mark.unit
    async def test_compare_variant_exception_handling(
        self, analyzer, mock_uniprot_client, spike_protein_uniprot_id
    ):
        """Test variant comparison with exception handling."""
        mock_uniprot_client.get_fasta_sequence.side_effect = Exception("Network error")

        result = await analyzer.compare_variant(spike_protein_uniprot_id, "D614G")

        assert "error" in result
        assert "Network error" in result["error"]

    @pytest.mark.unit
    def test_sequence_analyzer_initialization(self):
        """Test SequenceAnalyzer initialization with and without UniProt client."""
        # Test with custom UniProt client
        mock_client = MagicMock(spec=UniProtClient)
        analyzer = SequenceAnalyzer(uniprot_client=mock_client)
        assert analyzer.uniprot_client == mock_client

        # Test with default UniProt client
        analyzer_default = SequenceAnalyzer()
        assert isinstance(analyzer_default.uniprot_client, UniProtClient)

    @pytest.mark.unit
    def test_property_calculations_known_values(self, analyzer):
        """Test sequence analysis with known protein properties."""
        # Use a short, well-characterized sequence
        test_sequence = "AAAA"  # 4 alanines

        result = analyzer.analyze_raw_sequence(test_sequence)

        assert result["length"] == 4
        assert result["composition"]["A"] == 4
        assert len(result["composition"]) == 1  # Only alanine present

        # Molecular weight should be approximately 4 * 89.1 (alanine MW) - 3 * 18 (water for peptide bonds)
        expected_mw = (4 * 89.09 - 3 * 18.015) / 1000  # In kDa
        assert abs(result["molecular_weight_kda"] - expected_mw) < 0.01

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_uniprot_integration_with_spike_protein(
        self, analyzer_with_default_uniprot, spike_protein_uniprot_id
    ):
        """Integration test for UniProt API with SARS-CoV-2 spike protein analysis and D614G variant."""
        # Test sequence analysis with known spike protein
        seq_result = await analyzer_with_default_uniprot.analyze_from_uniprot(
            spike_protein_uniprot_id
        )

        assert "error" not in seq_result
        assert seq_result["length"] == 1273  # Known length of spike protein
        assert 140 < seq_result["molecular_weight_kda"] < 142  # ~141 kDa
        assert seq_result["isoelectric_point"] > 0
        assert len(seq_result["composition"]) > 15  # Should have most amino acids

        # Test the well-known D614G mutation using same protein
        variant_result = await analyzer_with_default_uniprot.compare_variant(
            spike_protein_uniprot_id, "D614G"
        )

        assert "error" not in variant_result
        assert variant_result["mutation"] == "D614G"
        assert variant_result["position"] == 614
        assert variant_result["amino_acid_change"] == "D → G"

        # Both analyses should be successful
        assert "error" not in variant_result["wildtype"]
        assert "error" not in variant_result["variant"]

        # The mutation should result in different molecular weights
        wt_mw = variant_result["wildtype"]["molecular_weight_kda"]
        var_mw = variant_result["variant"]["molecular_weight_kda"]
        assert wt_mw != var_mw
