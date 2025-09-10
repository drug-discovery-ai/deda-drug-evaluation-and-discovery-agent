# Unified Snapshot Testing System

This directory contains unified snapshot testing system where **snapshots are the default behavior** for integration tests.

## Overview

The snapshot testing system provides HTTP-level interception to transparently capture and replay API responses. This provides:

- **Fast test execution** - No network calls during testing (default)
- **Realistic tests** - Use actual API response structures  
- **Change detection** - Validate snapshots against live APIs
- **Clean architecture** - No snapshot logic mixed with business code
- **Simple interface** - Just two optional command-line flags

## Core Components

### 1. HTTP Interceptor (`http_interceptor.py`)
**Main component** - Provides HTTP-level interception with multiple backends:
- `SnapshotHTTPBackend` - Uses saved snapshots (default mode)
- `SnapshotRecordingBackend` - Records new snapshots from live APIs
- `SnapshotValidationBackend` - Validates snapshots against live APIs
- Handles proper HTTP error status codes and exceptions

### 2. SnapshotManager (`manager.py`)
- Loads and saves snapshots to the filesystem
- Generates consistent keys for API requests
- Handles snapshot metadata and organization
- Supports all API services (EBI, OpenTargets, UniProt, PDB, Misc)


## Directory Structure

```
snapshots/
├── __init__.py           # Package initialization
├── http_interceptor.py   # 🚀 Main HTTP interceptor system
├── manager.py            # SnapshotManager for file operations
├── metadata.json         # Global snapshot metadata
├── ebi/                  # EBI API snapshots (existing)
├── opentargets/          # OpenTargets API snapshots
├── uniprot/             # UniProt API snapshots (new)
├── pdb/                 # PDB API snapshots (new)  
├── misc/                # Misc API snapshots (new)
```

## Usage

The unified system provides a simple command-line interface with **snapshots as the default behavior**.

### Command-Line Interface

```bash
# Default behavior - uses existing snapshots (fast, no network calls)
pytest

# Record new snapshots from live API calls  
pytest --update-snapshots

# Validate existing snapshots against live APIs
pytest --validate-snapshots
```

### How It Works

1. **Unit tests** with `@patch` decorators work normally (no HTTP interception)
2. **Integration tests** marked with `@pytest.mark.integration` automatically use HTTP interception:
   - Default: Use existing snapshots
   - `--update-snapshots`: Record from live APIs
   - `--validate-snapshots`: Validate against live APIs

### Writing Tests

**No changes needed to existing test code!** The system works transparently:

```python
@pytest.mark.integration
async def test_get_protein_details():
    """Integration test - automatically uses snapshots."""
    client = UniProtClient()
    result = await client.get_details("P0DTC2")  # Uses snapshot by default
    
    assert "proteinDescription" in result
    assert result["organism"]["scientificName"]

@pytest.mark.unit  
async def test_with_mock():
    """Unit test - mocks work normally."""
    with patch.object(client, '_make_request', return_value=mock_data):
        result = await client.get_details("P0DTC2")  # Uses mock
        assert result == mock_data
```

## Snapshot Management

### Current Snapshots

The system currently has snapshots for:

- **EBI API** (`ebi/`) - Existing snapshots
- **UniProt API** (`uniprot/`) - FASTA sequences and protein details  
- **PDB API** (`pdb/`) - Structure details and error responses
- **OpenTargets API** (`opentargets/`) - Ready for snapshot generation
- **Misc APIs** (`misc/`) - External test APIs (httpbin.org, etc.)

### Updating Snapshots

To refresh snapshots for all integration tests:

```bash
# Update all snapshots from live APIs
pytest tests/core/ -k "integration" --update-snapshots

# Update specific service snapshots
pytest tests/core/test_uniprot.py -k "integration" --update-snapshots
```

### Validating Snapshots

To check if existing snapshots match current API responses:

```bash
# Validate all snapshots
pytest tests/core/ -k "integration" --validate-snapshots

# Check specific snapshots
pytest tests/core/test_pdb.py -k "integration" --validate-snapshots
```

## Testing

```bash
# Run all tests (uses snapshots by default)
pytest tests/core/ tests/utils/

# Run only unit tests (uses mocks)  
pytest tests/core/ -k "unit"

# Run only integration tests (uses snapshots)
pytest tests/core/ -k "integration"
```
