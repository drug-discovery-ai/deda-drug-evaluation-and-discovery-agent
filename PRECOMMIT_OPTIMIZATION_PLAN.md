# Pre-commit Hook Optimization Plan: pytest-testmon Implementation

## Objective
Configure pre-commit hooks to run tests only for changed files using pytest-testmon, reducing commit time while maintaining comprehensive test coverage.

## What is pytest-testmon?
pytest-testmon is a pytest plugin that automatically tracks which tests depend on which source files. It only runs tests that are affected by code changes, making test execution much faster while maintaining full coverage.

## Current State
The current pytest hook in `.pre-commit-config.yaml` has:
- `pass_filenames: false` - ignores changed filenames
- `always_run: true` - runs on every commit regardless of changes
- Runs entire test suite on every commit, even for unrelated changes

## Implementation Steps

### 1. Add pytest-testmon dependency
**File**: `pyproject.toml`
**Action**: Add `pytest-testmon>=2.0.0` to the `test` dependencies array

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.10.0",
    "pytest-cov>=4.0.0",
    "pytest-httpx>=0.30.0",
    "pytest-testmon>=2.0.0",  # ADD THIS LINE
    "responses>=0.23.0",
    "respx>=0.22.0",
]
```

### 2. Update pre-commit configuration
**File**: `.pre-commit-config.yaml`
**Action**: Modify the pytest hook configuration

**Current:**
```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: pytest
      language: system
      pass_filenames: false
      always_run: true
```

**Updated:**
```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: pytest --testmon
      language: system
      files: \.py$
      types: [python]
```

### 3. Initialize testmon database
**Action**: Run initial test suite to build the dependency tracking database
```bash
pytest --testmon
```
This creates a `.testmondata` file that stores test-to-source mappings.

### 4. Configure testmon behavior (optional)
**File**: `pyproject.toml`
**Action**: Add testmon configuration section if needed

```toml
[tool.testmon]
# Optional: specify which files to monitor
# norecursedirs = ["venv", ".git"]
```

## How it works

### First run
- All tests execute and testmon builds dependency graph
- Creates `.testmondata` file with test-to-source mappings

### Subsequent runs
- Only tests depending on changed files execute
- New/modified tests always run regardless of dependencies
- Dramatically reduces test execution time

### Clean state option
- Use `pytest --testmon-off` to run full suite when needed
- Use `pytest --testmon-clear` to rebuild dependency database

## Benefits

1. **Faster commits**: Only affected tests run instead of entire suite
2. **Automatic tracking**: No manual mapping of tests to source files needed  
3. **Comprehensive**: Catches all tests that import/depend on changed code
4. **Zero maintenance**: Automatically updates dependency tracking
5. **Reliable**: Uses actual import dependencies, not filename patterns

## Files to be modified

1. `pyproject.toml` - Add pytest-testmon dependency
2. `.pre-commit-config.yaml` - Update pytest hook configuration
3. `.gitignore` - Consider adding `.testmondata` (or commit it for team sharing)

## Testing the implementation

1. Install dependencies: `pip install -e .[test]`
2. Run initial testmon setup: `pytest --testmon`
3. Make a small change to a source file\
4. Run pre-commit: `pre-commit run pytest`
5. Verify only affected tests run
