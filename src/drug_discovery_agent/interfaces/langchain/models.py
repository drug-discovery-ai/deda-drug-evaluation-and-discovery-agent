from pydantic import BaseModel, Field


class UniProtCodeInput(BaseModel):
    """Input schema for UniProt code operations."""
    uniprot_code: str = Field(description="The UniProt accession code (e.g., 'P0DTC2')")


class PDBIdInput(BaseModel):
    """Input schema for PDB ID operations."""
    pdb_id: str = Field(description="The 4-character PDB ID (e.g., '4HHB')")


class RawSequenceInput(BaseModel):
    """Input schema for raw sequence analysis."""
    sequence: str = Field(description="Raw amino acid sequence string")


class ProteinVariantInput(BaseModel):
    """Input schema for protein variant comparison."""
    uniprot_id: str = Field(description="UniProt accession (e.g., 'P0DTC2')")
    mutation: str = Field(description="Mutation string in format D614G")


__all__ = [
    "UniProtCodeInput",
    "PDBIdInput", 
    "RawSequenceInput",
    "ProteinVariantInput",
]