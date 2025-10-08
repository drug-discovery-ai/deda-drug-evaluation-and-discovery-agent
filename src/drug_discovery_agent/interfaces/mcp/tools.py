# tools.py
from typing import Any

from fastmcp import FastMCP

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.ebi import EBIClient
from drug_discovery_agent.core.opentarget import OpenTargetsClient
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient


class BioinformaticsToolBase:
    """Base class encapsulating all MCP bioinformatics tools."""

    def __init__(self) -> None:
        self.uniprot_client = UniProtClient()
        self.pdb_client = PDBClient(self.uniprot_client)
        self.sequence_analyzer = SequenceAnalyzer(self.uniprot_client)
        self.ebi_client = EBIClient()
        self.open_target_client = OpenTargetsClient()

        # Shared MCP interface
        self.mcp: FastMCP = FastMCP("DEDA")

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Registers all tools under the FastMCP instance."""

        # Retrieve possible disease ontology matches (Human-in-the-Loop verification)
        @self.mcp.tool(
            name="get_possible_diseases_list",
            description=(
                "Use this tool when the input is a disease name rather than a protein or ontology ID. "
                "It queries the European Bioinformatics Institute (EBI) REST API and returns a list of possible "
                "ontology matches (EFO terms) related to the provided disease name. "
                "If multiple matches are returned, ask the user to clarify or confirm the correct one "
                "before proceeding. Once confirmed, pass the selected ontology ID to `get_disease_targets` "
                "to retrieve detailed target and drug association information."
            ),
        )
        async def get_disease_list(disease_name: str) -> list[dict[str, Any]]:
            """Retrieve a list of possible ontology matches for a given disease name."""
            return await self.ebi_client.fetch_all_ontology_ids(
                disease_name=disease_name
            )

        # Retrieve disease-associated target proteins from OpenTargets
        @self.mcp.tool(
            name="get_disease_targets",
            description=(
                "Retrieves disease-associated targets, genetic constraints, and known drugs from OpenTargets "
                "using a disease ontology ID. The results include each target’s approved name, functional "
                "description, tractability data, and drug associations relevant to the disease. "
                "You can further explore target protein details using `get_virus_protein_details`, "
                "`get_top_pdb_ids_for_uniprot`, or `analyze_sequence_properties`. "
                "For advanced users, invoke `get_experimental_structure_details` with a valid PDB ID "
                "to access detailed experimental metadata and structure resources."
            ),
            annotations=None,
        )
        async def get_disease_targets(ontology_id: str) -> dict[str, Any]:
            """Retrieve disease-associated target proteins and related data from OpenTargets."""
            return await self.open_target_client.disease_target_knowndrug_pipeline(
                ontology_id=ontology_id
            )

        # Retrieve detailed metadata for a viral protein from UniProt
        @self.mcp.tool(
            name="get_virus_protein_details",
            description=(
                "Retrieves detailed metadata for a viral protein from UniProt using its accession code. "
                "Returns key biological information such as organism name, taxonomic lineage, host species, "
                "functional annotations, and the complete amino acid sequence. "
                "Also includes the recommended protein name and a direct reference link to the UniProt entry. "
                "Use this tool to gain biological context about a protein before performing downstream analyses "
                "with tools such as `analyze_sequence_properties` or `get_experimental_structure_details`."
            ),
        )
        async def get_virus_protein_details(uniprot_code: str) -> dict[str, Any]:
            """Fetch comprehensive UniProt metadata for a given viral protein accession code."""
            return await self.uniprot_client.get_details(uniprot_code)

        # Retrieve experimental 3D structure details from RCSB PDB
        @self.mcp.tool(
            name="get_experimental_structure_details",
            description=(
                "Fetches experimental structure metadata for a given PDB ID from the RCSB Protein Data Bank (PDB). "
                "Returns detailed information including structure title, experimental method, resolution, atom count, "
                "release date, and associated keywords. Also provides a direct download link to the corresponding "
                "PDB structure file. This tool is useful for structural biologists and advanced users seeking "
                "to explore experimentally determined 3D protein data."
            ),
        )
        async def get_experimental_structure_details(pdb_id: str) -> dict[str, Any]:
            """Retrieve experimental structure metadata from RCSB PDB for a given PDB ID."""
            return await self.pdb_client.get_structure_details(pdb_id)

        # Retrieve co-crystallized ligands associated with a UniProt protein
        @self.mcp.tool(
            name="get_ligand_smiles_from_uniprot",
            description=(
                "Fetches ligands (non-polymer entities) co-crystallized with PDB structures associated with a given UniProt ID. "
                "For each related PDB entry, this tool retrieves ligand identifiers, names, chemical formulas, and SMILES strings "
                "from the RCSB Protein Data Bank (PDB). Useful for exploring potential small-molecule binding partners "
                "or understanding protein-ligand interactions in experimental structures."
            ),
        )
        async def get_ligand_smiles_from_uniprot(
            uniprot_id: str,
        ) -> list[dict[str, Any]]:
            """Retrieve ligand metadata (SMILES, formula, name) from PDB entries linked to a given UniProt ID."""
            return await self.pdb_client.get_ligands_for_uniprot(uniprot_id)

        @self.mcp.tool(
            name="analyze_sequence_properties",
            description="Analyze protein properties by UniProt code (length, molecular weight, pI, composition).",
        )
        async def analyze_protein_sequence_properties(
            uniprot_code: str,
        ) -> dict[str, Any]:
            return await self.sequence_analyzer.analyze_from_uniprot(uniprot_code)

        # Attach for external access
        self.get_disease_list = get_disease_list
        self.get_disease_targets = get_disease_targets
        self.get_virus_protein_details = get_virus_protein_details
        self.analyze_protein_sequence_properties = analyze_protein_sequence_properties
        self.get_experimental_structure_details = get_experimental_structure_details
        self.get_ligand_smiles_from_uniprot = get_ligand_smiles_from_uniprot


# Instantiate globally to reuse
bio_tools = BioinformaticsToolBase()
mcp = bio_tools.mcp
