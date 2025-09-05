"""Tests for langchain tools functionality."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient
from drug_discovery_agent.interfaces.langchain.tools import (
    AnalyzeRawSequenceTool,
    AnalyzeSequencePropertiesTool,
    BioinformaticsToolBase,
    CompareProteinVariantTool,
    GetLigandSmilesTool,
    GetProteinDetailsTool,
    GetProteinFastaTool,
    GetStructureDetailsTool,
    GetTopPDBIdsTool,
    create_bioinformatics_tools,
)

# Note: Mock client fixtures are now imported from shared fixtures


class TestBioinformaticsToolBase:
    """Test suite for BioinformaticsToolBase."""

    @pytest.mark.unit
    def test_tool_base_initialization_with_clients(
        self,
        mock_uniprot_client: Any,
        mock_pdb_client: Any,
        mock_sequence_analyzer: Any,
    ) -> None:
        """Test tool base initialization with provided clients."""

        # Create a concrete tool class for testing
        class TestTool(BioinformaticsToolBase):
            name: str = "test_tool"
            description: str = "Test tool"

            def __init__(self, **kwargs: Any) -> None:
                super().__init__(**kwargs)

            def _run(self, **kwargs: Any) -> str:
                return "test"

            async def _arun(self, **kwargs: Any) -> str:
                return "test"

        tool = TestTool(
            uniprot_client=mock_uniprot_client,
            pdb_client=mock_pdb_client,
            sequence_analyzer=mock_sequence_analyzer,
        )

        assert tool.uniprot_client == mock_uniprot_client
        assert tool.pdb_client == mock_pdb_client
        assert tool.sequence_analyzer == mock_sequence_analyzer

    @pytest.mark.unit
    def test_tool_base_initialization_default_clients(self) -> None:
        """Test tool base initialization with default clients."""

        class TestTool(BioinformaticsToolBase):
            name: str = "test_tool"
            description: str = "Test tool"

            def __init__(self, **kwargs: Any) -> None:
                super().__init__(**kwargs)

            def _run(self, **kwargs: Any) -> str:
                return "test"

            async def _arun(self, **kwargs: Any) -> str:
                return "test"

        tool = TestTool()

        assert isinstance(tool.uniprot_client, UniProtClient)
        assert isinstance(tool.pdb_client, PDBClient)
        assert isinstance(tool.sequence_analyzer, SequenceAnalyzer)


# Parameterized test for tool properties
@pytest.mark.unit
@pytest.mark.parametrize(
    "tool_class,expected_name,expected_desc_contains",
    [
        (GetProteinFastaTool, "get_protein_fasta", "FASTA"),
        (GetProteinDetailsTool, "get_protein_details", "metadata"),
        (AnalyzeSequencePropertiesTool, "analyze_sequence_properties", "properties"),
        (AnalyzeRawSequenceTool, "analyze_raw_sequence", "raw"),
        (CompareProteinVariantTool, "compare_protein_variant", "mutated"),
        (GetTopPDBIdsTool, "get_top_pdb_ids_for_uniprot", "PDB"),
        (GetStructureDetailsTool, "get_structure_details", "structure"),
        (GetLigandSmilesTool, "get_ligand_smiles_from_uniprot", "ligand"),
    ],
)
def test_tool_properties(
    tool_class: Any, expected_name: str, expected_desc_contains: str
) -> None:
    """Test tool name and description for all tools."""
    tool = tool_class()
    assert tool.name == expected_name
    assert expected_desc_contains.lower() in tool.description.lower()


class TestGetProteinFastaTool:
    """Test suite for GetProteinFastaTool."""

    @pytest.fixture
    def fasta_tool(self, mock_uniprot_client: Any) -> GetProteinFastaTool:
        """Create FASTA tool with mock client."""
        return GetProteinFastaTool(uniprot_client=mock_uniprot_client)

    @pytest.mark.unit
    async def test_async_run(
        self,
        fasta_tool: GetProteinFastaTool,
        mock_uniprot_client: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_fasta = f">sp|{spike_protein_uniprot_id}|SPIKE_SARS2\nMKTVRQERL"
        mock_uniprot_client.get_fasta_sequence.return_value = expected_fasta

        result = await fasta_tool._arun(spike_protein_uniprot_id)

        assert result == expected_fasta
        mock_uniprot_client.get_fasta_sequence.assert_called_once_with(
            spike_protein_uniprot_id
        )


class TestGetProteinDetailsTool:
    """Test suite for GetProteinDetailsTool."""

    @pytest.fixture
    def details_tool(self, mock_uniprot_client: Any) -> GetProteinDetailsTool:
        """Create details tool with mock client."""
        return GetProteinDetailsTool(uniprot_client=mock_uniprot_client)

    @pytest.mark.unit
    async def test_async_run(
        self,
        details_tool: GetProteinDetailsTool,
        mock_uniprot_client: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_details = {
            "accession": spike_protein_uniprot_id,
            "organism": "SARS-CoV-2",
            "function": "Spike protein",
        }
        mock_uniprot_client.get_details.return_value = expected_details

        result = await details_tool._arun(spike_protein_uniprot_id)

        assert result == expected_details
        mock_uniprot_client.get_details.assert_called_once_with(
            spike_protein_uniprot_id
        )


class TestAnalyzeSequencePropertiesTool:
    """Test suite for AnalyzeSequencePropertiesTool."""

    @pytest.fixture
    def analyze_tool(
        self, mock_sequence_analyzer: Any
    ) -> AnalyzeSequencePropertiesTool:
        """Create analyze tool with mock analyzer."""
        return AnalyzeSequencePropertiesTool(sequence_analyzer=mock_sequence_analyzer)

    @pytest.mark.unit
    async def test_async_run(
        self,
        analyze_tool: AnalyzeSequencePropertiesTool,
        mock_sequence_analyzer: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_analysis = {
            "length": 1273,
            "molecular_weight_kda": 141.2,
            "isoelectric_point": 8.5,
            "composition": {"M": 42, "K": 54},
        }
        mock_sequence_analyzer.analyze_from_uniprot.return_value = expected_analysis

        result = await analyze_tool._arun(spike_protein_uniprot_id)

        assert result == expected_analysis
        mock_sequence_analyzer.analyze_from_uniprot.assert_called_once_with(
            spike_protein_uniprot_id
        )


class TestAnalyzeRawSequenceTool:
    """Test suite for AnalyzeRawSequenceTool."""

    @pytest.fixture
    def raw_analyze_tool(self, mock_sequence_analyzer: Any) -> AnalyzeRawSequenceTool:
        """Create raw analyze tool with mock analyzer."""
        return AnalyzeRawSequenceTool(sequence_analyzer=mock_sequence_analyzer)

    @pytest.mark.unit
    async def test_async_run(
        self, raw_analyze_tool: AnalyzeRawSequenceTool, mock_sequence_analyzer: Any
    ) -> None:
        """Test asynchronous execution."""
        expected_analysis = {
            "length": 10,
            "molecular_weight_kda": 1.2,
            "isoelectric_point": 7.0,
        }
        mock_sequence_analyzer.analyze_raw_sequence.return_value = expected_analysis

        result = await raw_analyze_tool._arun("MKTVRQERL")

        assert result == expected_analysis
        mock_sequence_analyzer.analyze_raw_sequence.assert_called_once_with("MKTVRQERL")


class TestCompareProteinVariantTool:
    """Test suite for CompareProteinVariantTool."""

    @pytest.fixture
    def variant_tool(self, mock_sequence_analyzer: Any) -> CompareProteinVariantTool:
        """Create variant tool with mock analyzer."""
        return CompareProteinVariantTool(sequence_analyzer=mock_sequence_analyzer)

    @pytest.mark.unit
    async def test_async_run(
        self,
        variant_tool: CompareProteinVariantTool,
        mock_sequence_analyzer: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_comparison = {
            "mutation": "D614G",
            "wildtype": {"molecular_weight_kda": 141.2},
            "variant": {"molecular_weight_kda": 141.1},
        }
        mock_sequence_analyzer.compare_variant.return_value = expected_comparison

        result = await variant_tool._arun(spike_protein_uniprot_id, "D614G")

        assert result == expected_comparison
        mock_sequence_analyzer.compare_variant.assert_called_once_with(
            spike_protein_uniprot_id, "D614G"
        )


class TestGetTopPDBIdsTool:
    """Test suite for GetTopPDBIdsTool."""

    @pytest.fixture
    def pdb_ids_tool(self, mock_uniprot_client: Any) -> GetTopPDBIdsTool:
        """Create PDB IDs tool with mock client."""
        return GetTopPDBIdsTool(uniprot_client=mock_uniprot_client)

    @pytest.mark.unit
    async def test_async_run(
        self,
        pdb_ids_tool: GetTopPDBIdsTool,
        mock_uniprot_client: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_pdb_ids = ["6VSB", "6VXX", "7CAM"]
        mock_uniprot_client.get_pdb_ids.return_value = expected_pdb_ids

        result = await pdb_ids_tool._arun(spike_protein_uniprot_id)

        assert result == expected_pdb_ids
        mock_uniprot_client.get_pdb_ids.assert_called_once_with(
            spike_protein_uniprot_id
        )


class TestGetStructureDetailsTool:
    """Test suite for GetStructureDetailsTool."""

    @pytest.fixture
    def structure_tool(self, mock_pdb_client: Any) -> GetStructureDetailsTool:
        """Create structure tool with mock client."""
        return GetStructureDetailsTool(pdb_client=mock_pdb_client)

    @pytest.mark.unit
    async def test_async_run(
        self,
        structure_tool: GetStructureDetailsTool,
        mock_pdb_client: Any,
        spike_protein_pdb_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_details = {
            "pdb_id": spike_protein_pdb_id,
            "title": "SARS-CoV-2 spike protein",
            "resolution": 3.46,
            "method": "X-RAY DIFFRACTION",
        }
        mock_pdb_client.get_structure_details.return_value = expected_details

        result = await structure_tool._arun(spike_protein_pdb_id)

        assert result == expected_details
        mock_pdb_client.get_structure_details.assert_called_once_with(
            spike_protein_pdb_id
        )


class TestGetLigandSmilesTool:
    """Test suite for GetLigandSmilesTool."""

    @pytest.fixture
    def ligands_tool(self, mock_pdb_client: Any) -> GetLigandSmilesTool:
        """Create ligands tool with mock client."""
        return GetLigandSmilesTool(pdb_client=mock_pdb_client)

    @pytest.mark.unit
    async def test_async_run(
        self,
        ligands_tool: GetLigandSmilesTool,
        mock_pdb_client: Any,
        spike_protein_uniprot_id: str,
    ) -> None:
        """Test asynchronous execution."""
        expected_ligands = [
            {"id": "NAG", "name": "N-ACETYL-D-GLUCOSAMINE", "formula": "C8 H15 N O6"},
            {"id": "SO4", "name": "SULFATE ION", "formula": "O4 S"},
        ]
        mock_pdb_client.get_ligands_for_uniprot.return_value = expected_ligands

        result = await ligands_tool._arun(spike_protein_uniprot_id)

        assert result == expected_ligands
        mock_pdb_client.get_ligands_for_uniprot.assert_called_once_with(
            spike_protein_uniprot_id
        )


class TestCreateBioinformaticsTools:
    """Test suite for create_bioinformatics_tools factory function."""

    @pytest.mark.unit
    def test_create_with_default_clients(self) -> None:
        """Test creating tools with default clients."""
        tools = create_bioinformatics_tools()

        assert len(tools) == 10  # All tool classes
        assert isinstance(tools, list)

        # Check that all tools are BioinformaticsToolBase instances
        for tool in tools:
            assert isinstance(tool, BioinformaticsToolBase)

        # Check that all expected tool types are present
        tool_names = {tool.name for tool in tools}
        expected_names = {
            "get_possible_diseases",
            "get_disease_targets",
            "get_protein_fasta",
            "get_protein_details",
            "analyze_sequence_properties",
            "analyze_raw_sequence",
            "compare_protein_variant",
            "get_top_pdb_ids_for_uniprot",
            "get_structure_details",
            "get_ligand_smiles_from_uniprot",
        }
        assert tool_names == expected_names

    @pytest.mark.unit
    def test_create_with_custom_clients(self) -> None:
        """Test creating tools with custom clients."""
        mock_uniprot = AsyncMock(spec=UniProtClient)
        mock_pdb = MagicMock(spec=PDBClient)
        mock_analyzer = MagicMock(spec=SequenceAnalyzer)

        tools = create_bioinformatics_tools(
            uniprot_client=mock_uniprot,
            pdb_client=mock_pdb,
            sequence_analyzer=mock_analyzer,
        )

        assert len(tools) == 10

        # Check that all tools use the same client instances
        for tool in tools:
            if hasattr(tool, "uniprot_client"):
                assert tool.uniprot_client == mock_uniprot
            if hasattr(tool, "pdb_client"):
                assert tool.pdb_client == mock_pdb
            if hasattr(tool, "sequence_analyzer"):
                assert tool.sequence_analyzer == mock_analyzer

    @pytest.mark.unit
    def test_create_with_partial_clients(self) -> None:
        """Test creating tools with some custom clients."""
        mock_uniprot = AsyncMock(spec=UniProtClient)

        tools = create_bioinformatics_tools(uniprot_client=mock_uniprot)

        assert len(tools) == 10

        # Check that custom client is used
        for tool in tools:
            if hasattr(tool, "uniprot_client"):
                assert tool.uniprot_client == mock_uniprot
            # Other clients should be created as defaults
            if hasattr(tool, "pdb_client"):
                assert isinstance(tool.pdb_client, PDBClient)
            if hasattr(tool, "sequence_analyzer"):
                assert isinstance(tool.sequence_analyzer, SequenceAnalyzer)

    @pytest.mark.unit
    def test_tools_have_correct_args_schema(self) -> None:
        """Test that all tools have the correct args schema."""
        tools = create_bioinformatics_tools()

        # Map tool names to expected schema types
        from drug_discovery_agent.interfaces.langchain.models import (
            EBIDiseaseInput,
            OpenTargetOntologyInput,
            PDBIdInput,
            ProteinVariantInput,
            RawSequenceInput,
            UniProtCodeInput,
        )

        expected_schemas = {
            "get_possible_diseases": EBIDiseaseInput,
            "get_disease_targets": OpenTargetOntologyInput,
            "get_protein_fasta": UniProtCodeInput,
            "get_protein_details": UniProtCodeInput,
            "analyze_sequence_properties": UniProtCodeInput,
            "analyze_raw_sequence": RawSequenceInput,
            "compare_protein_variant": ProteinVariantInput,
            "get_top_pdb_ids_for_uniprot": UniProtCodeInput,
            "get_structure_details": PDBIdInput,
            "get_ligand_smiles_from_uniprot": UniProtCodeInput,
        }

        for tool in tools:
            expected_schema = expected_schemas[tool.name]
            assert tool.args_schema == expected_schema

    @pytest.mark.unit
    def test_all_tools_exported(self) -> None:
        """Test that all expected tools are in __all__ exports."""
        from drug_discovery_agent.interfaces.langchain.tools import (
            __all__ as exported_names,
        )

        expected_exports = [
            "BioinformaticsToolBase",
            "GetProteinFastaTool",
            "GetProteinDetailsTool",
            "AnalyzeSequencePropertiesTool",
            "AnalyzeRawSequenceTool",
            "CompareProteinVariantTool",
            "GetTopPDBIdsTool",
            "GetStructureDetailsTool",
            "GetLigandSmilesTool",
            "create_bioinformatics_tools",
        ]

        for export_name in expected_exports:
            assert export_name in exported_names, (
                f"{export_name} not in __all__ exports"
            )
