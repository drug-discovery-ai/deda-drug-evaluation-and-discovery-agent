# Snapshot Testing Implementation Plan

## Overview
This document outlines a comprehensive plan to implement snapshot testing for external API responses, replacing current mock data with real API responses that are automatically validated and updated.

## Current State Analysis

### Tests Using Mock External API Responses

Based on the codebase analysis, the following test files currently use mock external API responses:

1. **EBI Client Tests** (`tests/core/test_ebi.py`)
   - **External APIs:** EBI Ontology Lookup Service
   - **Mock Data:** Disease ontology data (EFO terms, descriptions, IRIs)
   - **Endpoints:** `https://www.ebi.ac.uk/ols/api/search`

2. **OpenTargets Client Tests** (`tests/core/test_opentarget.py`)
   - **External APIs:** OpenTargets Platform GraphQL API
   - **Mock Data:** Disease details, target associations, drug information
   - **Endpoints:** `https://api.platform.opentargets.org/api/v4/graphql`

3. **UniProt Client Tests** (`tests/core/test_uniprot.py`)
   - **External APIs:** UniProt REST API
   - **Mock Data:** Protein sequences (FASTA), protein details, PDB cross-references
   - **Endpoints:** 
     - `https://rest.uniprot.org/uniprotkb/{id}.fasta`
     - `https://rest.uniprot.org/uniprotkb/{id}`

4. **PDB Client Tests** (`tests/core/test_pdb.py`)
   - **External APIs:** RCSB PDB Data API
   - **Mock Data:** Structure information, ligand data, entry details
   - **Endpoints:** `https://data.rcsb.org/rest/v1/core/entry/{id}`

5. **HTTP Client Tests** (`tests/utils/test_http_client.py`)
   - **External APIs:** Generic HTTP endpoints for testing utilities
   - **Mock Data:** Various HTTP responses

6. **Mock Infrastructure Files**
   - `tests/fixtures/mock_http_server.py` - HTTP mocking infrastructure
   - `tests/fixtures/http_helpers.py` - HTTP mocking utilities
   - `tests/fixtures/common_api_mocks.py` - Pre-configured mock responses

## Snapshot Testing Architecture

### 1. Snapshot Data Structure

```
snapshots/
├── ebi/
│   ├── ontology_search_alzheimer.json
│   ├── ontology_search_covid19.json
│   └── ...
├── opentargets/
│   ├── disease_details_EFO_0000249.json
│   ├── target_association_EFO_0000249.json
│   └── ...
├── uniprot/
│   ├── protein_details_P0DTC2.json
│   ├── fasta_P0DTC2.txt
│   ├── pdb_refs_P0DTC2.json
│   └── ...
├── pdb/
│   ├── structure_6VSB.json
│   ├── ligands_6VSB.json
│   └── ...
└── metadata.json
```

### 2. Snapshot Management System

#### Core Components

1. **Snapshot Manager (`snapshots/manager.py`)**
   - Load and save snapshots
   - Generate snapshot keys from requests
   - Handle snapshot versioning
   - Validate snapshot freshness

2. **API Response Capturer (`snapshots/capturer.py`)**
   - Intercept real API calls during snapshot creation
   - Store responses with metadata (timestamp, status, headers)
   - Handle different response formats (JSON, text, binary)

3. **Snapshot Validator (`snapshots/validator.py`)**
   - Compare new responses with existing snapshots
   - Detect schema changes
   - Generate change reports
   - Validate response integrity

4. **Test Integration (`snapshots/pytest_plugin.py`)**
   - Pytest plugin for snapshot testing
   - Automatic snapshot loading/saving
   - Test modes: use-snapshots, update-snapshots, validate-snapshots

### 3. Implementation Phases

#### Phase 1: Core Infrastructure (Week 1)

1. **Create Snapshot Manager**
   ```python
   class SnapshotManager:
       def load_snapshot(self, key: str) -> Optional[dict]
       def save_snapshot(self, key: str, data: dict, metadata: dict)
       def generate_key(self, url: str, method: str, params: dict) -> str
       def get_snapshot_age(self, key: str) -> timedelta
   ```

2. **Create API Response Capturer**
   ```python
   class ApiResponseCapturer:
       def capture_response(self, response: httpx.Response) -> dict
       def should_capture(self, url: str) -> bool
       def normalize_response(self, response: dict) -> dict
   ```

3. **Basic Test Integration**
   - Implement pytest plugin framework
   - Create snapshot decorator for test functions
   - Add environment variable controls (SNAPSHOT_MODE)

#### Phase 2: API Client Integration (Week 2)

##### Step 2.1: EBI Client Integration (Days 1-2)

**2.1.1: Modify EBI Client (`src/drug_discovery_agent/core/ebi.py`)**
- [ ] Add `SnapshotManager` import and initialization
- [ ] Add `snapshot_mode` parameter to `__init__()` method
- [ ] Implement `_get_snapshot_key()` method for ontology search requests
- [ ] Modify `fetch_all_ontology_ids()` to check for snapshots before making API calls
- [ ] Add snapshot saving logic after successful API responses
- [ ] Implement fallback to real API if snapshot missing in "use" mode

**2.1.2: Create EBI Snapshot Fixtures**
```python
# tests/fixtures/ebi_snapshots.py
@pytest.fixture
def ebi_snapshot_client(snapshot_mode):
    return EBIClient(snapshot_mode=snapshot_mode)

@pytest.fixture  
def ebi_ontology_snapshots():
    return {
        "alzheimer": "snapshots/ebi/ontology_search_alzheimer.json",
        "covid19": "snapshots/ebi/ontology_search_covid19.json",
        "cancer": "snapshots/ebi/ontology_search_cancer.json"
    }
```

**2.1.3: Update EBI Test Files**
- [ ] Convert `test_fetch_all_ontology_ids_success()` to use snapshots
- [ ] Add snapshot validation tests for different disease queries
- [ ] Maintain mock-based tests as `test_*_mock()` variants
- [ ] Add integration test with real API for snapshot creation

**2.1.4: Generate Initial EBI Snapshots**
- [ ] Run tests in update mode to capture real API responses
- [ ] Validate snapshot file structure and metadata
- [ ] Commit initial EBI snapshots to repository

##### Step 2.2: OpenTargets Client Integration (Days 3-4)

**2.2.1: Modify OpenTargets Client (`src/drug_discovery_agent/core/opentarget.py`)**
- [ ] Add `SnapshotManager` integration to client initialization
- [ ] Implement snapshot key generation for GraphQL queries
- [ ] Modify `fetch_disease_details()` for snapshot support:
  - Check for existing snapshot before API call
  - Save response to snapshot after successful call
  - Handle GraphQL-specific response format
- [ ] Modify `fetch_disease_to_target_association()` for snapshot support
- [ ] Modify `fetch_target_details_info()` for snapshot support  
- [ ] Modify `fetch_drug_details_info()` for snapshot support
- [ ] Add snapshot support to `disease_target_knowndrug_pipeline()`

**2.2.2: Create OpenTargets Snapshot Fixtures**
```python
# tests/fixtures/opentargets_snapshots.py
@pytest.fixture
def opentargets_snapshot_client(snapshot_mode):
    return OpenTargetsClient(snapshot_mode=snapshot_mode)

@pytest.fixture
def opentargets_test_entities():
    return {
        "diseases": ["EFO_0000249", "EFO_0009636"],  # Alzheimer variants
        "targets": ["ENSG00000142192", "ENSG00000080815"],  # APP, PSEN1
        "drugs": ["CHEMBL123", "CHEMBL456"]
    }
```

**2.2.3: Update OpenTargets Test Files**
- [ ] Convert `test_fetch_disease_details_success()` to snapshot-based
- [ ] Convert `test_fetch_disease_to_target_association_success()` to snapshots
- [ ] Convert `test_fetch_target_details_info_success()` to snapshots
- [ ] Convert `test_fetch_drug_details_info_success()` to snapshots
- [ ] Update `test_disease_target_knowndrug_pipeline_success()` for snapshots
- [ ] Maintain error handling tests with mocks
- [ ] Add GraphQL response validation tests

**2.2.4: Generate Initial OpenTargets Snapshots**
- [ ] Create snapshots for key disease entities (Alzheimer's, COVID-19)
- [ ] Create snapshots for associated targets and drugs
- [ ] Validate GraphQL response structure in snapshots
- [ ] Test pipeline functionality with snapshot data

##### Step 2.3: UniProt Client Integration (Days 5-6)

**2.3.1: Modify UniProt Client (`src/drug_discovery_agent/core/uniprot.py`)**
- [ ] Add snapshot support to `get_fasta_sequence()`:
  - Generate snapshot key from protein ID
  - Handle text/FASTA response format
  - Save FASTA responses to `.fasta` files in snapshots
- [ ] Add snapshot support to `get_details()`:
  - Handle JSON response format
  - Generate consistent keys for protein detail queries
  - Preserve error handling for missing proteins
- [ ] Add snapshot support to `get_pdb_ids()`:
  - Snapshot cross-reference data
  - Handle list response normalization
  - Cache PDB ID lookups

**2.3.2: Create UniProt Snapshot Fixtures**
```python
# tests/fixtures/uniprot_snapshots.py
@pytest.fixture
def uniprot_snapshot_client(snapshot_mode):
    return UniProtClient(snapshot_mode=snapshot_mode)

@pytest.fixture
def uniprot_test_proteins():
    return {
        "spike_protein": "P0DTC2",  # SARS-CoV-2 spike
        "app_protein": "P05067",   # Amyloid precursor protein
        "invalid_id": "INVALID123"
    }

@pytest.fixture
def uniprot_expected_pdb_ids():
    return {
        "P0DTC2": ["6VSB", "6VXX", "6VYB"],
        "P05067": ["1AAP", "1AMB", "1AMC"]
    }
```

**2.3.3: Update UniProt Test Files**
- [ ] Convert `test_get_fasta_sequence_success()` to snapshot-based
- [ ] Convert `test_get_details_success()` to use snapshots
- [ ] Convert `test_get_pdb_ids_success()` to snapshot-based
- [ ] Handle FASTA text format in snapshot validation
- [ ] Maintain error scenario tests with mocks
- [ ] Add protein sequence validation tests

**2.3.4: Generate Initial UniProt Snapshots**
- [ ] Create FASTA sequence snapshots for key proteins
- [ ] Create protein detail snapshots with full metadata
- [ ] Create PDB cross-reference snapshots
- [ ] Validate text and JSON format handling

##### Step 2.4: PDB Client Integration (Days 7-8)

**2.4.1: Modify PDB Client (`src/drug_discovery_agent/core/pdb.py`)**
- [ ] Add snapshot support to structure information queries:
  - Implement snapshot keys for PDB entry requests
  - Handle complex nested JSON responses
  - Support multiple endpoint integration
- [ ] Add snapshot support to ligand information queries:
  - Generate keys for entity-specific requests
  - Handle ligand data normalization
  - Cache chemical component information
- [ ] Implement batch query snapshot support:
  - Handle multiple PDB IDs in single snapshot
  - Optimize for bulk operations
  - Support partial cache hits

**2.4.2: Create PDB Snapshot Fixtures**
```python
# tests/fixtures/pdb_snapshots.py
@pytest.fixture
def pdb_snapshot_client(snapshot_mode):
    return PDBClient(snapshot_mode=snapshot_mode)

@pytest.fixture
def pdb_test_structures():
    return {
        "covid_spike": "6VSB",      # SARS-CoV-2 spike
        "alzheimer_related": "1AAP", # Amyloid precursor
        "small_molecule": "1HTM",    # Drug-protein complex
        "invalid_id": "ZZZZ"
    }

@pytest.fixture
def pdb_expected_ligands():
    return {
        "6VSB": ["NAG", "MAN", "BMA"],  # Glycans
        "1HTM": ["HTM", "SO4"]          # Drug + sulfate
    }
```

**2.4.3: Update PDB Test Files**
- [ ] Convert structure information tests to snapshot-based
- [ ] Convert ligand query tests to use snapshots
- [ ] Convert batch operation tests to snapshots
- [ ] Handle complex nested JSON validation
- [ ] Maintain error handling with mocks
- [ ] Add structural data integrity tests

**2.4.4: Generate Initial PDB Snapshots**
- [ ] Create structure snapshots for diverse protein types
- [ ] Create ligand snapshots with chemical information
- [ ] Create experimental method and resolution snapshots
- [ ] Validate structural data completeness

##### Step 2.5: Test Infrastructure Updates (Days 9-10)

**2.5.1: Update Global Test Configuration**
- [ ] Add snapshot mode configuration to `conftest.py`:
```python
# tests/conftest.py
@pytest.fixture(scope="session")
def snapshot_mode():
    mode = os.getenv("SNAPSHOT_MODE", "use")
    if mode not in ["use", "update", "validate"]:
        raise ValueError(f"Invalid SNAPSHOT_MODE: {mode}")
    return mode

@pytest.fixture(autouse=True)
def setup_snapshot_environment(snapshot_mode):
    # Configure all clients for snapshot mode
    os.environ["SNAPSHOT_MODE"] = snapshot_mode
```

**2.5.2: Create Snapshot Test Utilities**
```python
# tests/utils/snapshot_helpers.py
class SnapshotTestHelper:
    @staticmethod
    def compare_api_responses(snapshot_data, live_data):
        """Compare snapshot with live API response"""
        
    @staticmethod  
    def validate_snapshot_freshness(snapshot_path, max_age_days=7):
        """Check if snapshot is within acceptable age"""
        
    @staticmethod
    def generate_snapshot_report():
        """Generate report of all snapshots and their status"""
```

**2.5.3: Update Pytest Configuration**
- [ ] Add snapshot-specific pytest markers:
```ini
# pytest.ini
[tool:pytest]
markers =
    snapshot: Tests that use API response snapshots
    snapshot_update: Tests that update snapshots
    snapshot_validate: Tests that validate snapshots
    mock_only: Tests that only use mocks (no snapshots)
```

**2.5.4: Create Snapshot Management Commands**
```python
# scripts/manage_snapshots.py
class SnapshotManager:
    def update_all_snapshots(self):
        """Update all API snapshots"""
        
    def validate_all_snapshots(self):  
        """Validate all snapshots against live APIs"""
        
    def clean_old_snapshots(self, max_age_days=30):
        """Remove outdated snapshots"""
        
    def generate_snapshot_report(self):
        """Create comprehensive snapshot status report"""
```

##### Step 2.6: Integration Testing & Validation (Days 11-12)

**2.6.1: Cross-Client Integration Tests**
- [ ] Test end-to-end workflows using snapshots across all clients
- [ ] Validate data consistency between related API calls
- [ ] Test pipeline operations (disease → targets → drugs → structures)
- [ ] Ensure snapshot data supports all existing use cases

**2.6.2: Performance Validation**
- [ ] Benchmark snapshot vs mock performance
- [ ] Validate memory usage with large snapshots
- [ ] Test concurrent snapshot access
- [ ] Optimize snapshot loading for frequently used data

**2.6.3: Backward Compatibility Testing**
- [ ] Ensure all existing tests still pass with mocks
- [ ] Validate gradual migration path
- [ ] Test fallback mechanisms when snapshots unavailable
- [ ] Verify no breaking changes to public APIs

**2.6.4: Documentation Updates**
- [ ] Update client documentation with snapshot usage
- [ ] Create snapshot testing guide for developers
- [ ] Document snapshot file organization
- [ ] Add troubleshooting guide for snapshot issues

##### Phase 2 Success Criteria

- [ ] All 4 API clients support snapshot mode
- [ ] Existing functionality preserved with mocks
- [ ] Initial snapshot data generated and validated
- [ ] Test execution time comparable to mocks
- [ ] No breaking changes to existing test APIs
- [ ] Comprehensive error handling maintained
- [ ] Documentation updated and complete

#### Phase 3: Automation & CI Integration (Week 3)

1. **GitHub Actions Workflow for Weekly Snapshot Updates**

Create `.github/workflows/update-snapshots.yml`:

```yaml
name: Update API Snapshots
on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2 AM UTC
  workflow_dispatch:  # Allow manual triggering
    inputs:
      api_filter:
        description: 'Specific API to update (ebi,opentargets,uniprot,pdb or "all")'
        required: false
        default: 'all'
        type: choice
        options:
          - all
          - ebi
          - opentargets
          - uniprot
          - pdb
      force_update:
        description: 'Force update even if snapshots are fresh'
        required: false
        default: false
        type: boolean

jobs:
  update-snapshots:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Configure Git
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          
      - name: Create snapshot update branch
        run: |
          BRANCH_NAME="automated-snapshot-update-$(date +%Y%m%d)"
          echo "BRANCH_NAME=$BRANCH_NAME" >> $GITHUB_ENV
          git checkout -b $BRANCH_NAME
          
      - name: Run snapshot updates
        id: update_snapshots
        env:
          SNAPSHOT_MODE: update
          API_FILTER: ${{ github.event.inputs.api_filter || 'all' }}
          FORCE_UPDATE: ${{ github.event.inputs.force_update || 'false' }}
        run: |
          echo "Starting snapshot update process..."
          
          # Set API-specific markers based on filter
          if [ "$API_FILTER" = "all" ]; then
            PYTEST_MARKERS=""
          else
            PYTEST_MARKERS="-m ${API_FILTER}_api"
          fi
          
          # Run snapshot updates with detailed output
          python -m pytest tests/ \
            --snapshot-mode=update \
            $PYTEST_MARKERS \
            --tb=short \
            -v \
            --snapshot-report=snapshot_update_report.json
            
          # Generate summary report
          python scripts/generate_snapshot_report.py \
            --input snapshot_update_report.json \
            --output snapshot_changes_summary.md
            
          # Check if any snapshots were updated
          if git diff --quiet snapshots/; then
            echo "changes_detected=false" >> $GITHUB_OUTPUT
            echo "No snapshot changes detected"
          else
            echo "changes_detected=true" >> $GITHUB_OUTPUT
            echo "Snapshot changes detected"
            
            # Count changed files
            CHANGED_FILES=$(git diff --name-only snapshots/ | wc -l)
            echo "changed_files_count=$CHANGED_FILES" >> $GITHUB_OUTPUT
            
            # Get list of changed APIs
            CHANGED_APIS=$(git diff --name-only snapshots/ | cut -d'/' -f2 | sort -u | tr '\n' ',' | sed 's/,$//')
            echo "changed_apis=$CHANGED_APIS" >> $GITHUB_OUTPUT
          fi
          
      - name: Commit snapshot changes
        if: steps.update_snapshots.outputs.changes_detected == 'true'
        run: |
          git add snapshots/
          git add snapshot_changes_summary.md
          git commit -m "🤖 Automated snapshot update - $(date +%Y-%m-%d)
          
          - Updated ${{ steps.update_snapshots.outputs.changed_files_count }} snapshot files
          - APIs affected: ${{ steps.update_snapshots.outputs.changed_apis }}
          - Generated by: Weekly automated snapshot update workflow
          
          Co-authored-by: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
          
      - name: Push changes
        if: steps.update_snapshots.outputs.changes_detected == 'true'
        run: |
          git push origin $BRANCH_NAME
          
      - name: Analyze changes for breaking changes
        if: steps.update_snapshots.outputs.changes_detected == 'true'
        id: analyze_changes
        run: |
          # Run breaking change analysis
          python scripts/analyze_snapshot_changes.py \
            --snapshot-dir snapshots/ \
            --output breaking_changes_report.json
            
          # Check if breaking changes detected
          if [ -f breaking_changes_report.json ]; then
            BREAKING_CHANGES=$(jq -r '.has_breaking_changes' breaking_changes_report.json)
            echo "breaking_changes=$BREAKING_CHANGES" >> $GITHUB_OUTPUT
            
            if [ "$BREAKING_CHANGES" = "true" ]; then
              echo "⚠️ Breaking changes detected in API snapshots!"
              BREAKING_COUNT=$(jq -r '.breaking_changes | length' breaking_changes_report.json)
              echo "breaking_count=$BREAKING_COUNT" >> $GITHUB_OUTPUT
            fi
          else
            echo "breaking_changes=false" >> $GITHUB_OUTPUT
          fi
          
      - name: Create Pull Request
        if: steps.update_snapshots.outputs.changes_detected == 'true'
        id: create_pr
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          branch: ${{ env.BRANCH_NAME }}
          title: "🤖 Automated API Snapshot Updates - ${{ steps.update_snapshots.outputs.changed_apis }}"
          body: |
            ## 📸 Automated Snapshot Updates
            
            This PR contains automated updates to API response snapshots.
            
            ### 📊 Summary
            - **Changed Files:** ${{ steps.update_snapshots.outputs.changed_files_count }}
            - **APIs Updated:** ${{ steps.update_snapshots.outputs.changed_apis }}
            - **Update Date:** $(date +%Y-%m-%d)
            - **Breaking Changes:** ${{ steps.analyze_changes.outputs.breaking_changes == 'true' && '⚠️ YES' || '✅ No' }}
            
            ### 🔍 What Changed
            
            The following API snapshots have been updated with the latest responses:
            
            ${{ steps.update_snapshots.outputs.changed_apis }}
            
            ### 📋 Detailed Changes
            
            See the attached `snapshot_changes_summary.md` file for detailed information about what changed in each snapshot.
            
            ${{ steps.analyze_changes.outputs.breaking_changes == 'true' && format('### ⚠️ Breaking Changes Detected\n\n{0} potential breaking changes were found. Please review carefully before merging.\n\nSee `breaking_changes_report.json` for details.', steps.analyze_changes.outputs.breaking_count) || '' }}
            
            ### ✅ Pre-merge Checklist
            
            - [ ] Review snapshot changes for accuracy
            - [ ] Verify no sensitive data is included in snapshots
            - [ ] Check that tests still pass with updated snapshots
            - [ ] Confirm API changes don't break existing functionality
            ${{ steps.analyze_changes.outputs.breaking_changes == 'true' && '- [ ] ⚠️ **IMPORTANT:** Review breaking changes report' || '' }}
            
            ### 🚀 Testing
            
            This PR was created by the automated snapshot update workflow. The snapshots have been generated from live API responses and should be thoroughly reviewed before merging.
            
            To test locally:
            ```bash
            git checkout ${{ env.BRANCH_NAME }}
            pytest tests/ --snapshot-mode=use
            ```
            
            ---
            
            *This PR was automatically created by [GitHub Actions](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})*
          labels: |
            automated
            snapshots
            api-updates
            ${{ steps.analyze_changes.outputs.breaking_changes == 'true' && 'breaking-changes' || '' }}
          reviewers: |
            # Add your team members here
            @team-lead
            @senior-dev
          draft: ${{ steps.analyze_changes.outputs.breaking_changes == 'true' }}
          
      - name: Add comment for breaking changes
        if: steps.update_snapshots.outputs.changes_detected == 'true' && steps.analyze_changes.outputs.breaking_changes == 'true'
        uses: peter-evans/create-or-update-comment@v3
        with:
          issue-number: ${{ steps.create_pr.outputs.pull-request-number }}
          body: |
            ## ⚠️ Breaking Changes Detected
            
            This PR contains ${{ steps.analyze_changes.outputs.breaking_count }} potential breaking changes in API snapshots.
            
            **This PR has been marked as DRAFT** to prevent accidental merging.
            
            Please:
            1. Review the `breaking_changes_report.json` file
            2. Test thoroughly with updated snapshots
            3. Update any affected code
            4. Mark as "Ready for Review" when safe to merge
            
            ---
            *Automated breaking change detection by snapshot update workflow*
            
          
      - name: Update workflow summary
        run: |
          echo "## 📸 Snapshot Update Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ "${{ steps.update_snapshots.outputs.changes_detected }}" = "true" ]; then
            echo "✅ **Changes Detected:** ${{ steps.update_snapshots.outputs.changed_files_count }} files updated" >> $GITHUB_STEP_SUMMARY
            echo "📊 **APIs Affected:** ${{ steps.update_snapshots.outputs.changed_apis }}" >> $GITHUB_STEP_SUMMARY
            echo "🔗 **Pull Request:** #${{ steps.create_pr.outputs.pull-request-number }}" >> $GITHUB_STEP_SUMMARY
            if [ "${{ steps.analyze_changes.outputs.breaking_changes }}" = "true" ]; then
              echo "⚠️ **Breaking Changes:** ${{ steps.analyze_changes.outputs.breaking_count }} detected" >> $GITHUB_STEP_SUMMARY
            else
              echo "✅ **Breaking Changes:** None detected" >> $GITHUB_STEP_SUMMARY
            fi
          else
            echo "ℹ️ **No Changes:** All snapshots are up to date" >> $GITHUB_STEP_SUMMARY
          fi

  cleanup-old-branches:
    runs-on: ubuntu-latest
    if: always()
    needs: update-snapshots
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Clean up old automated branches
        run: |
          # Delete automated snapshot update branches older than 30 days
          git fetch --all
          git for-each-ref --format="%(refname:short) %(committerdate)" refs/remotes/origin/automated-snapshot-update-* | \
            awk '$2 <= "'$(date -d '30 days ago' -I)'"' | \
            awk '{print $1}' | \
            sed 's/origin\///' | \
            xargs -r -I {} git push origin --delete {}
```

2. **Snapshot Validation Workflow**
   ```yaml
   name: Validate API Snapshots
   on:
     schedule:
       - cron: '0 6 * * *'  # Daily at 6 AM
   
   jobs:
     validate-snapshots:
       runs-on: ubuntu-latest
       steps:
         - name: Validate Snapshots
           run: pytest --snapshot-mode=validate
         - name: Report Changes
           # Send notifications if APIs have changed
   ```

## Implementation Details

### 1. Snapshot File Format

```json
{
  "metadata": {
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "url": "https://www.ebi.ac.uk/ols/api/search",
    "method": "GET",
    "params": {"q": "alzheimer", "ontology": "efo"},
    "status_code": 200,
    "content_type": "application/json",
    "api_version": "v1",
    "checksum": "sha256:abc123..."
  },
  "response": {
    "headers": {
      "content-type": "application/json",
      "x-api-version": "1.0"
    },
    "body": {
      // Actual API response data
    }
  }
}
```

### 2. Test Configuration

```python
# pytest.ini or conftest.py
SNAPSHOT_CONFIG = {
    "base_dir": "snapshots",
    "max_age_days": 7,
    "apis": {
        "ebi": {
            "base_url": "https://www.ebi.ac.uk/ols/api",
            "rate_limit": 10,  # requests per second
            "timeout": 30
        },
        "opentargets": {
            "base_url": "https://api.platform.opentargets.org/api/v4",
            "rate_limit": 5,
            "timeout": 60
        },
        "uniprot": {
            "base_url": "https://rest.uniprot.org",
            "rate_limit": 20,
            "timeout": 30
        },
        "pdb": {
            "base_url": "https://data.rcsb.org/rest/v1",
            "rate_limit": 15,
            "timeout": 30
        }
    }
}
```

### 3. Test Modes

1. **Use Snapshots Mode** (Default)
   - Load responses from snapshots
   - Fast test execution
   - No external API calls
   - Fail if snapshot missing

2. **Update Snapshots Mode**
   - Make real API calls
   - Save new snapshots
   - Update existing snapshots
   - Compare with previous versions

3. **Validate Snapshots Mode**
   - Make real API calls
   - Compare with existing snapshots
   - Report differences
   - Don't update snapshots

4. **Hybrid Mode**
   - Use snapshots for fast tests
   - Make real API calls for integration tests
   - Configurable per test or test class

### 4. Change Detection Logic

```python
class SnapshotValidator:
    def compare_responses(self, old: dict, new: dict) -> ChangeReport:
        """Compare two API responses and generate change report."""
        changes = []
        
        # Schema changes
        if self.schema_changed(old, new):
            changes.append(SchemaChange(...))
        
        # Data changes
        if self.data_changed(old, new):
            changes.append(DataChange(...))
        
        # Breaking changes
        if self.breaking_change(old, new):
            changes.append(BreakingChange(...))
            
        return ChangeReport(changes)
    
    def breaking_change(self, old: dict, new: dict) -> bool:
        """Detect if API changes would break existing code."""
        # Check for removed fields
        # Check for changed data types
        # Check for changed response structure
        pass
```
