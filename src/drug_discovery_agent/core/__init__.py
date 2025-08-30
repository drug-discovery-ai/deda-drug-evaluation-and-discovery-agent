"""Core bioinformatics functionality."""

# Import class-based clients
from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient

# Export classes for clean API
__all__ = [
    "UniProtClient",
    "PDBClient",
    "SequenceAnalyzer",
]
