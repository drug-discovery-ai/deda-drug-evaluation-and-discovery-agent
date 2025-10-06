# tools.py
from typing import Any
from fastmcp import FastMCP

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient

uniprot_client = UniProtClient()
pdb_client = PDBClient(uniprot_client)
sequence_analyzer = SequenceAnalyzer(uniprot_client)

mcp = FastMCP("FASTA")

@mcp.tool(
    name="get_virus_protein_FASTA_format_sequence",
    description="Retrieves the amino acid sequence in FASTA format for a given viral protein using its UniProt accession code.",
)
async def get_fasta_protein(uniprot_code: str) -> str:
    return await uniprot_client.get_fasta_sequence(uniprot_code)

@mcp.tool(
    name="get_virus_protein_details",
    description="Retrieve virus protein metadata from UniProt given an accession code like 'P0DTC2'.",
)
async def get_virus_protein_details(uniprot_code: str) -> dict[str, Any]:
    return await uniprot_client.get_details(uniprot_code)

@mcp.tool(
    name="analyze_sequence_properties",
    description="Analyze protein properties by UniProt code (length, molecular weight, pI, composition).",
)
async def analyze_protein_sequence_properties(uniprot_code: str) -> dict[str, Any]:
    return await sequence_analyzer.analyze_from_uniprot(uniprot_code)

@mcp.tool(
    name="compare_protein_variant",
    description="Compares a mutated protein (e.g., D614G) against the reference from UniProt.",
)
async def compare_variant_protein(uniprot_id: str, mutation: str) -> dict[str, Any]:
    return await sequence_analyzer.compare_variant(uniprot_id, mutation)

@mcp.tool(
    name="get_top_pdb_ids_for_uniprot",
    description="Returns up to 10 representative PDB IDs for a given UniProt protein.",
)
async def get_top_pdb_ids_for_uniprot(uniprot_id: str) -> list[str]:
    return await uniprot_client.get_pdb_ids(uniprot_id)

@mcp.tool(
    name="get_experimental_structure_details",
    description="Fetches experimental structure metadata from RCSB PDB using a PDB ID.",
)
async def get_experimental_structure_details(pdb_id: str) -> dict[str, Any]:
    return await pdb_client.get_structure_details(pdb_id)

@mcp.tool(
    name="get_ligand_smiles_from_uniprot",
    description="Fetches up to 10 ligands co-crystallized with PDB structures related to a UniProt ID.",
)
async def get_ligand_smiles_from_uniprot(uniprot_id: str) -> list[dict[str, Any]]:
    return await pdb_client.get_ligands_for_uniprot(uniprot_id)
