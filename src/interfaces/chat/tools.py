"""LangChain tool wrappers for bioinformatics functions."""
import asyncio
from typing import Dict, Any, List
from langchain.tools import tool

# Import from core modules
from ...core.uniprot import (
    fetch_protein_fasta_sequence,
    fetch_protein_details,
    fetch_top_pdb_ids_for_uniprot,
)
from ...core.pdb import (
    fetch_structure_details,
    fetch_ligand_smiles_from_uniprot,
)
from ...core.analysis import (
    analyze_sequence_properties,
    analyze_raw_sequence_properties,
    compare_protein_variant,
)


@tool
def get_protein_fasta(uniprot_code: str) -> str:
    """Retrieves FASTA sequence for a viral protein from UniProt.
    
    Args:
        uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").
        
    Returns:
        A string containing the protein sequence in FASTA format.
    """
    return asyncio.run(fetch_protein_fasta_sequence(uniprot_code))


@tool
def get_protein_details(uniprot_code: str) -> Dict[str, Any]:
    """Gets detailed metadata for a viral protein from UniProt.
    
    Args:
        uniprot_code: UniProt accession code (e.g., P0DTC2).
    
    Returns:
        Dictionary containing organism, scientific name, lineage, function, reference URL, etc.
    """
    return asyncio.run(fetch_protein_details(uniprot_code))


@tool
def analyze_sequence_properties(uniprot_code: str) -> Dict[str, Any]:
    """Analyze properties of a protein sequence for a viral protein.

    Args:
        uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

    Returns:
        Dictionary with length, molecular_weight_kda, isoelectric_point, and composition.
    """
    return asyncio.run(analyze_sequence_properties(uniprot_code))


@tool
def analyze_raw_sequence(sequence: str) -> Dict[str, Any]:
    """Analyze properties of a raw protein sequence string.
    
    Args:
        sequence: Raw amino acid sequence string.
        
    Returns:
        Dictionary with analysis results including length, MW, pI, and composition.
    """
    return analyze_raw_sequence_properties(sequence)


@tool
def compare_protein_variant(uniprot_id: str, mutation: str) -> Dict[str, Any]:
    """Compare a mutated protein against the reference from UniProt.
    
    Args:
        uniprot_id: UniProt accession (e.g., "P0DTC2").
        mutation: Mutation string in format D614G.

    Returns:
        Dictionary with differences in molecular weight, charge, and other properties.
    """
    return asyncio.run(compare_protein_variant(uniprot_id, mutation))


@tool
def get_top_pdb_ids_for_uniprot(uniprot_id: str) -> List[str]:
    """Fetch top 10 representative PDB entries from UniProt cross-references.
    
    Args:
        uniprot_id: A valid UniProt accession (e.g., 'P0DTC2').

    Returns:
        List of up to 10 unique PDB IDs linked to the protein.
    """
    return asyncio.run(fetch_top_pdb_ids_for_uniprot(uniprot_id))


@tool
def get_structure_details(pdb_id: str) -> Dict[str, Any]:
    """Get experimental structure details from RCSB PDB.
    
    Args:
        pdb_id: The 4-character PDB ID (e.g., '4HHB').

    Returns:
        Dictionary with metadata including structure title, method, resolution, and download link.
    """
    return asyncio.run(fetch_structure_details(pdb_id))


@tool
def get_ligand_smiles_from_uniprot(uniprot_id: str) -> List[Dict[str, Any]]:
    """Fetch ligands from PDB structures related to a UniProt ID.
    
    Args:
        uniprot_id: A valid UniProt accession (e.g., 'P0DTC2').

    Returns:
        List of dictionaries with ligand metadata including ID, name, formula, and SMILES.
    """
    return asyncio.run(fetch_ligand_smiles_from_uniprot(uniprot_id))


# Export all tools for easy importing
__all__ = [
    "get_protein_fasta",
    "get_protein_details",
    "analyze_sequence_properties",
    "analyze_raw_sequence",
    "compare_protein_variant",
    "get_top_pdb_ids_for_uniprot",
    "get_structure_details",
    "get_ligand_smiles_from_uniprot",
]