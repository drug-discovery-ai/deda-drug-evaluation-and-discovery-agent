# Unified Snapshot Testing System

## Overview

This system provides a clean, unified approach to API testing where **snapshots are the default behavior**. All tests use the same code but can operate in different modes via command-line flags.

## Key Features

- ✅ **Snapshots by default** - More realistic testing out of the box
- ✅ **Single test suite** - Same tests work in all modes  
- ✅ **Clean API clients** - No snapshot logic mixed with business logic
- ✅ **HTTP-level interception** - Transparent to application code
- ✅ **Simple command interface** - Just two optional flags

## Command Usage

```bash
# Default behavior - uses existing snapshots
pytest

# Record new snapshots from live API calls
pytest --update-snapshots

# Validate existing snapshots against live APIs  
pytest --validate-snapshots
```

## Architecture

### HTTP Interceptor (`snapshots/http_interceptor.py`)
- **SnapshotHTTPBackend** - Uses saved snapshots (default)
- **SnapshotRecordingBackend** - Records new snapshots from live APIs
- **SnapshotValidationBackend** - Validates snapshots against live APIs

### pytest Integration (`tests/conftest.py`)
- Global HTTP interception via `pytest_configure`
- Command-line options for different modes
- Automatic backend selection based on flags

### Clean API Clients
- `src/drug_discovery_agent/core/ebi.py` 
- `src/drug_discovery_agent/core/opentarget.py`
- `src/drug_discovery_agent/core/uniprot.py`
- `src/drug_discovery_agent/core/pdb.py`

All clients use standard `httpx.AsyncClient` - HTTP interceptor handles the rest.

## Benefits

1. **More Realistic Testing** - Snapshots provide real API response structure
2. **Faster Tests** - No network calls in default mode
3. **Reproducible** - Same results across environments
4. **Easy Updates** - Single flag to refresh all snapshots
5. **Clean Code** - Business logic separate from testing infrastructure

## Migration from Old System

- ❌ Removed `--mocks` option (snapshots are better default)
- ❌ Removed duplicate test files like `test_ebi_snapshots.py`
- ❌ Removed complex snapshot logic from API clients
- ❌ Simplified pytest markers to just `unit`, `integration`, `slow`

The new system is simpler, more powerful, and easier to maintain.