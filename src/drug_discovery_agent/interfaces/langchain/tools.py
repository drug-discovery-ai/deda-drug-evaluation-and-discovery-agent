import asyncio
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient
from drug_discovery_agent.interfaces.langchain.models import (
    PDBIdInput,
    ProteinVariantInput,
    RawSequenceInput,
    UniProtCodeInput,
)


class BioinformaticsToolBase(BaseTool):
    """Base class for bioinformatics tools with injectable client instances."""

    # Declare these as class attributes to avoid mypy issues
    _uniprot_client: UniProtClient
    _pdb_client: PDBClient
    _sequence_analyzer: SequenceAnalyzer

    def __init__(
        self,
        uniprot_client: UniProtClient | None = None,
        pdb_client: PDBClient | None = None,
        sequence_analyzer: SequenceAnalyzer | None = None,
        **kwargs: Any,
    ):
        """Initialize with optional client instances.

        Args:
            uniprot_client: UniProt client instance. Creates default if None.
            pdb_client: PDB client instance. Creates default if None.
            sequence_analyzer: Sequence analyzer instance. Creates default if None.
            **kwargs: Additional arguments passed to BaseTool.
        """
        # Initialize clients first - create defaults if not provided
        self._uniprot_client = uniprot_client or UniProtClient()
        self._pdb_client = pdb_client or PDBClient(self._uniprot_client)
        self._sequence_analyzer = sequence_analyzer or SequenceAnalyzer(
            self._uniprot_client
        )
        
        super().__init__(**kwargs)

    @property
    def uniprot_client(self) -> UniProtClient:
        """Access to UniProt client instance."""
        return self._uniprot_client

    @property
    def pdb_client(self) -> PDBClient:
        """Access to PDB client instance."""
        return self._pdb_client

    @property
    def sequence_analyzer(self) -> SequenceAnalyzer:
        """Access to sequence analyzer instance."""
        return self._sequence_analyzer


class GetProteinFastaTool(BioinformaticsToolBase):
    """Tool for retrieving FASTA sequences from UniProt."""

    name: str = "get_protein_fasta"
    description: str = "Retrieves FASTA sequence for a viral protein from UniProt"
    args_schema: type[BaseModel] = UniProtCodeInput

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> str:
        """Retrieve FASTA sequence synchronously."""
        return asyncio.run(self.uniprot_client.get_fasta_sequence(uniprot_code))

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        """Retrieve FASTA sequence asynchronously."""
        return await self.uniprot_client.get_fasta_sequence(uniprot_code)


class GetProteinDetailsTool(BioinformaticsToolBase):
    """Tool for retrieving protein details from UniProt."""

    name: str = "get_protein_details"
    description: str = "Gets detailed metadata for a viral protein from UniProt"
    args_schema: type[BaseModel] = UniProtCodeInput

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Retrieve protein details synchronously."""
        return asyncio.run(self.uniprot_client.get_details(uniprot_code))

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Retrieve protein details asynchronously."""
        return await self.uniprot_client.get_details(uniprot_code)


class AnalyzeSequencePropertiesTool(BioinformaticsToolBase):
    """Tool for analyzing protein sequence properties."""

    name: str = "analyze_sequence_properties"
    description: str = "Analyze properties of a protein sequence for a viral protein"
    args_schema: type[BaseModel] = UniProtCodeInput

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Analyze sequence properties synchronously."""
        return asyncio.run(self.sequence_analyzer.analyze_from_uniprot(uniprot_code))

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Analyze sequence properties asynchronously."""
        return await self.sequence_analyzer.analyze_from_uniprot(uniprot_code)


class AnalyzeRawSequenceTool(BioinformaticsToolBase):
    """Tool for analyzing raw sequence properties."""

    name: str = "analyze_raw_sequence"
    description: str = "Analyze properties of a raw protein sequence string"
    args_schema: type[BaseModel] = RawSequenceInput

    def _run(
        self, sequence: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Analyze raw sequence properties synchronously."""
        return self.sequence_analyzer.analyze_raw_sequence(sequence)

    async def _arun(
        self,
        sequence: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Analyze raw sequence properties asynchronously."""
        return self.sequence_analyzer.analyze_raw_sequence(sequence)


class CompareProteinVariantTool(BioinformaticsToolBase):
    """Tool for comparing protein variants."""

    name: str = "compare_protein_variant"
    description: str = "Compare a mutated protein against the reference from UniProt"
    args_schema: type[BaseModel] = ProteinVariantInput

    def _run(
        self,
        uniprot_id: str,
        mutation: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Compare protein variant synchronously."""
        return asyncio.run(self.sequence_analyzer.compare_variant(uniprot_id, mutation))

    async def _arun(
        self,
        uniprot_id: str,
        mutation: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Compare protein variant asynchronously."""
        return await self.sequence_analyzer.compare_variant(uniprot_id, mutation)


class GetTopPDBIdsTool(BioinformaticsToolBase):
    """Tool for getting PDB IDs for a UniProt entry."""

    name: str = "get_top_pdb_ids_for_uniprot"
    description: str = (
        "Fetch top 10 representative PDB entries from UniProt cross-references"
    )
    args_schema: type[BaseModel] = UniProtCodeInput

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> list[str]:
        """Get PDB IDs synchronously."""
        return asyncio.run(self.uniprot_client.get_pdb_ids(uniprot_code))

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> list[str]:
        """Get PDB IDs asynchronously."""
        return await self.uniprot_client.get_pdb_ids(uniprot_code)


class GetStructureDetailsTool(BioinformaticsToolBase):
    """Tool for getting experimental structure details."""

    name: str = "get_structure_details"
    description: str = "Get experimental structure details from RCSB PDB"
    args_schema: type[BaseModel] = PDBIdInput

    def _run(
        self, pdb_id: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Get structure details synchronously."""
        return asyncio.run(self.pdb_client.get_structure_details(pdb_id))

    async def _arun(
        self, pdb_id: str, run_manager: AsyncCallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Get structure details asynchronously."""
        return await self.pdb_client.get_structure_details(pdb_id)


class GetLigandSmilesTool(BioinformaticsToolBase):
    """Tool for getting ligand SMILES from UniProt."""

    name: str = "get_ligand_smiles_from_uniprot"
    description: str = "Fetch ligands from PDB structures related to a UniProt ID"
    args_schema: type[BaseModel] = UniProtCodeInput

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> list[dict[str, Any]]:
        """Get ligand SMILES synchronously."""
        return asyncio.run(self.pdb_client.get_ligands_for_uniprot(uniprot_code))

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> list[dict[str, Any]]:
        """Get ligand SMILES asynchronously."""
        return await self.pdb_client.get_ligands_for_uniprot(uniprot_code)


# Factory functions for convenient tool creation
def create_bioinformatics_tools(
    uniprot_client: UniProtClient | None = None,
    pdb_client: PDBClient | None = None,
    sequence_analyzer: SequenceAnalyzer | None = None,
) -> list[BioinformaticsToolBase]:
    """Create all bioinformatics tools with shared client instances.

    Args:
        uniprot_client: UniProt client instance. Creates default if None.
        pdb_client: PDB client instance. Creates default if None.
        sequence_analyzer: Sequence analyzer instance. Creates default if None.

    Returns:
        List of all bioinformatics tool instances.
    """
    # Create shared clients if not provided
    if uniprot_client is None:
        uniprot_client = UniProtClient()
    if pdb_client is None:
        pdb_client = PDBClient(uniprot_client)
    if sequence_analyzer is None:
        sequence_analyzer = SequenceAnalyzer(uniprot_client)

    return [
        GetProteinFastaTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetProteinDetailsTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        AnalyzeSequencePropertiesTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        AnalyzeRawSequenceTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        CompareProteinVariantTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetTopPDBIdsTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetStructureDetailsTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetLigandSmilesTool(  # type: ignore[call-arg]
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
    ]


# Export tool classes and factory function
__all__ = [
    # Tool classes
    "BioinformaticsToolBase",
    "GetProteinFastaTool",
    "GetProteinDetailsTool",
    "AnalyzeSequencePropertiesTool",
    "AnalyzeRawSequenceTool",
    "CompareProteinVariantTool",
    "GetTopPDBIdsTool",
    "GetStructureDetailsTool",
    "GetLigandSmilesTool",
    # Factory function
    "create_bioinformatics_tools",
]
