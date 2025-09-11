import asyncio
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from drug_discovery_agent.core.alphafold import AlphaFoldClient
from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.ebi import EBIClient
from drug_discovery_agent.core.opentarget import OpenTargetsClient
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient
from drug_discovery_agent.interfaces.langchain.models import (
    AlphaFoldIdInput,
    EBIDiseaseInput,
    OpenTargetOntologyInput,
    PDBIdInput,
    ProteinVariantInput,
    RawSequenceInput,
    UniProtCodeInput,
)


class BioinformaticsToolBase(BaseTool):
    """Base class for bioinformatics tools with injectable client instances."""

    def __init__(
        self,
        uniprot_client: UniProtClient | None = None,
        pdb_client: PDBClient | None = None,
        sequence_analyzer: SequenceAnalyzer | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with optional client instances.

        Args:
            uniprot_client: UniProt client instance. Creates default if None.
            pdb_client: PDB client instance. Creates default if None.
            sequence_analyzer: Sequence analyzer instance. Creates default if None.
            **kwargs: Additional arguments passed to BaseTool.
        """
        # Initialize BaseTool first
        super().__init__(**kwargs)

        # Initialize clients - create defaults if not provided
        self._ebi_client = EBIClient()

        self._opentarget_client = OpenTargetsClient()

        self._alphafold_client = AlphaFoldClient()

        self._uniprot_client = uniprot_client or UniProtClient()
        self._pdb_client = pdb_client or PDBClient(self._uniprot_client)
        self._sequence_analyzer = sequence_analyzer or SequenceAnalyzer(
            self._uniprot_client
        )

    @property
    def ebi_client(self) -> EBIClient:
        """Access to UniProt client instance."""
        return self._ebi_client

    @property
    def opentarget_client(self) -> OpenTargetsClient:
        """Access to UniProt client instance."""
        return self._opentarget_client

    @property
    def uniprot_client(self) -> UniProtClient:
        """Access to UniProt client instance."""
        return self._uniprot_client

    @property
    def pdb_client(self) -> PDBClient:
        """Access to PDB client instance."""
        return self._pdb_client

    @property
    def alphafold_client(self) -> AlphaFoldClient:
        """Access to PDB client instance."""
        return self._alphafold_client

    @property
    def sequence_analyzer(self) -> SequenceAnalyzer:
        """Access to sequence analyzer instance."""
        return self._sequence_analyzer


class GetDiseaseListTool(BioinformaticsToolBase):
    """Tool for retrieving Ontology ID from European Bioinformatics Institute API."""

    name: str = "get_possible_diseases"
    description: str = (
        "Use this tool when a user provides a disease name, not protein name. "
        "It queries the European Bioinformatics Institute REST API and returns a list of possible ontology IDs (EFO terms). "
        "If multiple matches are found, ask the user to clarify which one they mean before proceeding. "
        "Once the correct ontology ID is chosen, pass it to `get_disease_targets` for target details."
    )
    args_schema: type[BaseModel] = EBIDiseaseInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def _run(
        self, disease_name: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve possible diseases from the disease input synchronously"""
        return asyncio.run(self.ebi_client.fetch_all_ontology_ids(disease_name))

    async def _arun(
        self,
        disease_name: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve possible diseases from the disease input asynchronously"""
        return await self.ebi_client.fetch_all_ontology_ids(disease_name)


class GetDiseaseTargetTool(BioinformaticsToolBase):
    """Tool for retrieving Ontology ID from European Bioinformatics Institute API."""

    name: str = "get_disease_targets"
    description: str = (
        "Tool for retrieving disease-associated targets, constraints, and drugs from OpenTargets using an ontology ID."
        "The results include each target’s approved name, functional descriptions, "
        "tractability information, and known drug associations for the disease. "
        "Invoke `get_protein_details`, `get_top_pdb_ids_for_uniprot`, "
        "`analyze_sequence_properties`, or any other available tools "
        "to explore the details of the target protein."
    )

    args_schema: type[BaseModel] = OpenTargetOntologyInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def _run(
        self, ontology_id: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> dict[str, Any]:
        """Retrieve disease associated target synchronously."""
        return asyncio.run(
            self.opentarget_client.disease_target_knowndrug_pipeline(ontology_id)
        )

    async def _arun(
        self,
        ontology_id: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        """Retrieve disease associated target asynchronously."""
        return await self.opentarget_client.disease_target_knowndrug_pipeline(
            ontology_id
        )


class GetProteinFastaTool(BioinformaticsToolBase):
    """Tool for retrieving FASTA sequences from UniProt."""

    name: str = "get_protein_fasta"
    description: str = "Retrieves FASTA sequence for a protein from UniProt"
    args_schema: type[BaseModel] = UniProtCodeInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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
    description: str = "Gets detailed metadata for a protein from UniProt"
    args_schema: type[BaseModel] = UniProtCodeInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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
    description: str = "Analyze properties of a protein sequence for a protein"
    args_schema: type[BaseModel] = UniProtCodeInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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
        "Fetches up to 10 representative PDB entries from UniProt cross-references "
        "for a given UniProt accession code."
    )
    args_schema: type[BaseModel] = UniProtCodeInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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


class GetAlphaFoldPredictionTool(BioinformaticsToolBase):
    """Tool for getting predicted 3D structure of a protein associated with UniProt."""

    name: str = "get_alphafold_structure_prediction_from_uniprot"
    description: str = (
        "Given a UniProt ID, fetch the AlphaFold DB prediction including: "
        "links to 3D structure files (.cif, .pdb, .bcif), model metadata "
        "(pipeline, version, creation date), UniProt sequence and annotations, "
        "confidence scores (pLDDT, PAE), and related resources. "
        "This tool is used for structure prediction, not ligand retrieval."
    )
    args_schema: type[BaseModel] = AlphaFoldIdInput

    # Explicit __init__ needed for mypy to recognize inherited constructor from BaseTool
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def _run(
        self, uniprot_code: str, run_manager: CallbackManagerForToolRun | None = None
    ) -> list[dict[str, Any]]:
        """Get protein structure prediction synchronously."""
        return asyncio.run(
            self.alphafold_client.fetch_alphafold_prediction(uniprot_code)
        )

    async def _arun(
        self,
        uniprot_code: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> list[dict[str, Any]]:
        """Get protein structure prediction asynchronously."""
        return await self.alphafold_client.fetch_alphafold_prediction(uniprot_code)


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
        GetDiseaseListTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetDiseaseTargetTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetProteinFastaTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetProteinDetailsTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        AnalyzeSequencePropertiesTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        AnalyzeRawSequenceTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        CompareProteinVariantTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetTopPDBIdsTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetStructureDetailsTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetLigandSmilesTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
        GetAlphaFoldPredictionTool(
            uniprot_client=uniprot_client,
            pdb_client=pdb_client,
            sequence_analyzer=sequence_analyzer,
        ),
    ]


# Export tool classes and factory function
__all__ = [
    # Tool classes
    "BioinformaticsToolBase",
    "GetDiseaseListTool",
    "GetDiseaseTargetTool",
    "GetProteinFastaTool",
    "GetProteinDetailsTool",
    "AnalyzeSequencePropertiesTool",
    "AnalyzeRawSequenceTool",
    "CompareProteinVariantTool",
    "GetTopPDBIdsTool",
    "GetStructureDetailsTool",
    "GetLigandSmilesTool",
    "GetAlphaFoldPredictionTool",
    # Factory function
    "create_bioinformatics_tools",
]
