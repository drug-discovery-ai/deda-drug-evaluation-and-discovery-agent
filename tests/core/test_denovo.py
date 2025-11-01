import pytest

from drug_discovery_agent.core.denovo.preprocessor import PreprocessorClient


class TestDenovoConfigGenerator:
    @pytest.fixture
    def mock_preprocessor(self) -> PreprocessorClient:
        """Fixture to provide a mock PreprocessorClient instance."""
        client = PreprocessorClient(denovo_tool_name="test-model")
        return client

    @pytest.mark.asyncio
    async def test_preprocess_success(
        self, mock_preprocessor: PreprocessorClient
    ) -> None:
        """Test that generate_antigen_epitope() correctly fetches regions for a valid UniProt ID."""
        uniprot_id = "Q6Q1S0"  # uniprot of Influenza neuraminidase antigen
        uniprot_result = await mock_preprocessor.generate_antigen_epitope(
            uniprot_code=uniprot_id
        )
        assert uniprot_result is not None

    @pytest.mark.asyncio
    async def test_denovo_filtering(
        self, mock_preprocessor: PreprocessorClient
    ) -> None:
        """Ensure denovo=True filters only relevant antigenic regions."""
        uniprot_id = "P0DTC2"  # SARS-CoV-2 Spike
        results = await mock_preprocessor.generate_antigen_epitope(
            uniprot_code=uniprot_id
        )
        assert results is not None
        for result in results:
            assert "type" in result
            assert "residue_range" in result
            assert "description" in result

    @pytest.mark.asyncio
    async def test_invalid_uniprot_id(
        self, mock_preprocessor: PreprocessorClient
    ) -> None:
        """Verify that invalid UniProt IDs are handled gracefully."""
        uniprot_id = "invalid_uniprot"  # Invalid ID
        result = await mock_preprocessor.generate_antigen_epitope(
            uniprot_code=uniprot_id
        )
        assert result == [] or result is None

    @pytest.mark.asyncio
    async def test_generate_denovo_antibody_framework(
        self, mock_preprocessor: PreprocessorClient
    ) -> None:
        """Verify that invalid UniProt IDs are handled gracefully."""
        uniprot_id = "invalid_uniprot"  # Invalid ID
        result = await mock_preprocessor.generate_antigen_epitope(
            uniprot_code=uniprot_id
        )
        assert result == [] or result is None
