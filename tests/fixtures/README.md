# Test Fixtures and Shared Components

This directory contains shared test fixtures and utilities that are commonly used across multiple test files in the project.

## Files Created

### 1. `mock_clients.py`
Contains shared mock client fixtures:
- `mock_uniprot_client`: AsyncMock for UniProtClient
- `mock_pdb_client`: AsyncMock for PDBClient  
- `mock_sequence_analyzer`: AsyncMock for SequenceAnalyzer
- `mock_clients`: Tuple of all mock clients

### 2. `sample_data.py`
Contains common test data constants and fixtures:
- `sample_fasta`: Sample FASTA sequence
- `sample_sequence`: Basic protein sequence
- `invalid_sequence`: Sequence with invalid amino acids
- `spike_protein_uniprot_id`: P0DTC2 UniProt ID
- `spike_protein_pdb_id`: 6VSB PDB ID
- `mock_uniprot_details_response`: Sample UniProt API response
- `mock_uniprot_pdb_response`: Sample PDB cross-references response
- `sample_fasta_long`: Extended FASTA sequence

### 3. `http_helpers.py`
Contains HTTP mocking helper utilities:
- `HttpMockHelpers` class with static methods for creating mock responses
- `http_mock_helpers` fixture providing the helper instance
- `common_http_errors` fixture with standard HTTP error scenarios
- Methods for creating structure, entry, and ligand responses

### 4. `env_helpers.py`
Contains environment variable mocking:
- `mock_env_vars`: OpenAI API key and model mocks
- `empty_env`: Empty environment fixture
- Individual fixtures for API key and model name

## Integration

These fixtures are automatically available in all test files through `tests/conftest.py`, which imports:
```python
from tests.fixtures.http_helpers import *
from tests.fixtures.env_helpers import *
```

## Usage Examples

### Before (duplicated code):
```python
@pytest.fixture
def mock_uniprot_client(self):
    return AsyncMock(spec=UniProtClient)

def _create_mock_http_response(self, response_data, status_code=200):
    mock_response = AsyncMock()
    mock_response.status_code = status_code
    mock_response.json = lambda: response_data
    return mock_response
```

### After (using shared fixtures):
```python
def test_example(self, mock_uniprot_client, http_mock_helpers):
    mock_response = http_mock_helpers.create_mock_http_response({"key": "value"})
```

## Benefits

1. **Reduced Duplication**: Common fixtures are defined once and reused
2. **Consistency**: Standardized mock objects and test data across all tests
3. **Maintainability**: Changes to common patterns need to be made in one place
4. **Readability**: Tests focus on test logic rather than mock setup
5. **Reusability**: New tests can easily leverage existing patterns

## Refactored Files

The following test files have been partially refactored to demonstrate the usage:
- `tests/utils/test_http_client.py`
- `tests/core/test_pdb.py`  
- `tests/core/test_uniprot.py`
- `tests/test_chat.py`

Additional files can be refactored following the same patterns shown in these examples.