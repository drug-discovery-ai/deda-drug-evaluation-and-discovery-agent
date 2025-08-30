"""Shared mock client fixtures for testing."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from drug_discovery_agent.core.uniprot import UniProtClient
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.analysis import SequenceAnalyzer


@pytest.fixture
def mock_uniprot_client():
    """Create a mock UniProt client."""
    return AsyncMock(spec=UniProtClient)


@pytest.fixture
def mock_pdb_client():
    """Create a mock PDB client."""
    return AsyncMock(spec=PDBClient)


@pytest.fixture
def mock_sequence_analyzer():
    """Create a mock sequence analyzer."""
    return AsyncMock(spec=SequenceAnalyzer)


@pytest.fixture
def mock_clients(mock_uniprot_client, mock_pdb_client, mock_sequence_analyzer):
    """Create all mock clients as a tuple."""
    return mock_uniprot_client, mock_pdb_client, mock_sequence_analyzer