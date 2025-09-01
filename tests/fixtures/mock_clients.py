"""Shared mock client fixtures for testing."""

from unittest.mock import AsyncMock

import pytest

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient


@pytest.fixture
def mock_uniprot_client() -> AsyncMock:
    """Create a mock UniProt client."""
    return AsyncMock(spec=UniProtClient)


@pytest.fixture
def mock_pdb_client() -> AsyncMock:
    """Create a mock PDB client."""
    return AsyncMock(spec=PDBClient)


@pytest.fixture
def mock_sequence_analyzer() -> AsyncMock:
    """Create a mock sequence analyzer."""
    return AsyncMock(spec=SequenceAnalyzer)


@pytest.fixture
def mock_clients(
    mock_uniprot_client: AsyncMock,
    mock_pdb_client: AsyncMock,
    mock_sequence_analyzer: AsyncMock,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    """Create all mock clients as a tuple."""
    return mock_uniprot_client, mock_pdb_client, mock_sequence_analyzer
