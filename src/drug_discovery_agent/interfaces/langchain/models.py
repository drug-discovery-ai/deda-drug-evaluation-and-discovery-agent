from pydantic import BaseModel, Field


class EBIDiseaseInput(BaseModel):
    """Input schema for disease search operations."""

    disease_name: str = Field(
        description="Disease name (e.g., 'Covid', 'brain tumor', 'chicken pox')"
    )


class OpenTargetOntologyInput(BaseModel):
    """Input schema for disease associated target details operations."""

    ontology_id: str = Field(
        description="Disease standard name (e.g., 'EFO_0007204', is ontology_id for one variant of chicken pox)"
    )


class UniProtCodeInput(BaseModel):
    """Input schema for UniProt code operations corresponds to the disease target"""

    uniprot_code: str = Field(description="The UniProt accession code (e.g., 'P0DTC2')")


class PDBIdInput(BaseModel):
    """Input schema for PDB ID operations."""

    pdb_id: str = Field(description="The 4-character PDB ID (e.g., '4HHB')")


class AlphaFoldIdInput(BaseModel):
    """Input schema for PDB ID operations."""

    uniprot_code: str = Field(description="The UniProt accession code (e.g., 'P0DTC2')")


class RawSequenceInput(BaseModel):
    """Input schema for raw sequence analysis."""

    sequence: str = Field(description="Raw amino acid sequence string")


class ProteinVariantInput(BaseModel):
    """Input schema for protein variant comparison."""

    uniprot_id: str = Field(description="UniProt accession (e.g., 'P0DTC2')")
    mutation: str = Field(description="Mutation string in format D614G")


__all__ = [
    "EBIDiseaseInput",
    "OpenTargetOntologyInput",
    "PDBIdInput",
    "RawSequenceInput",
    "ProteinVariantInput",
]
