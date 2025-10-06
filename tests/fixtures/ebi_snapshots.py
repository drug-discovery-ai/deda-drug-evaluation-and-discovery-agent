"""EBI API snapshot fixtures and test data."""

from typing import Any

import pytest

from drug_discovery_agent.core.ebi import EBIClient


@pytest.fixture
def ebi_snapshot_client() -> EBIClient:
    """Create EBI client (HTTP interceptor handles snapshots automatically)."""
    return EBIClient()


@pytest.fixture
def ebi_test_diseases() -> dict[str, str]:
    """Test diseases for EBI API testing."""
    return {
        "alzheimer": "alzheimer disease",
        "covid19": "COVID-19",
        "cancer": "cancer",
        "diabetes": "diabetes mellitus",
        "parkinson": "Parkinson disease",
    }


@pytest.fixture
def ebi_ontology_snapshots() -> dict[str, str]:
    """EBI ontology snapshot file mappings."""
    return {
        "alzheimer": "ebi/ontology_search_alzheimer_disease.json",
        "covid19": "ebi/ontology_search_COVID-19.json",
        "cancer": "ebi/ontology_search_cancer.json",
        "diabetes": "ebi/ontology_search_diabetes_mellitus.json",
        "parkinson": "ebi/ontology_search_Parkinson_disease.json",
    }


@pytest.fixture
def ebi_expected_results() -> dict[str, dict[str, Any]]:
    """Expected results for EBI API calls."""
    return {
        "alzheimer": {
            "count": 2,
            "first_id": "EFO_0000249",
            "first_label": "Alzheimer disease",
            "contains_early_onset": True,
        },
        "covid19": {
            "count": 1,
            "first_id": "EFO_0009932",
            "first_label": "COVID-19",
            "contains_sars": False,
        },
        "cancer": {
            "min_count": 5,  # Cancer should have many results
            "contains_carcinoma": True,
        },
    }


@pytest.fixture
def ebi_mock_successful_response() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Mock successful EBI API response."""
    return {
        "response": {
            "docs": [
                {
                    "label": "Alzheimer disease",
                    "iri": "http://www.ebi.ac.uk/efo/EFO_0000249",
                    "ontology_name": "efo",
                    "short_form": "EFO_0000249",
                    "description": ["A neurodegenerative disease"],
                },
                {
                    "label": "Early-onset Alzheimer disease",
                    "iri": "http://www.ebi.ac.uk/efo/EFO_0009636",
                    "ontology_name": "efo",
                    "short_form": "EFO_0009636",
                    "description": ["Early onset form of Alzheimer disease"],
                },
            ]
        }
    }


@pytest.fixture
def ebi_mock_empty_response() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Mock empty EBI API response."""
    return {"response": {"docs": []}}


@pytest.fixture
def ebi_mock_filtered_response() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Mock EBI response with mixed ontologies (testing filtering)."""
    return {
        "response": {
            "docs": [
                {
                    "label": "EFO term",
                    "iri": "http://www.ebi.ac.uk/efo/EFO_0000001",
                    "ontology_name": "efo",
                    "short_form": "EFO_0000001",
                    "description": ["An EFO term"],
                },
                {
                    "label": "MONDO term",
                    "iri": "http://purl.obolibrary.org/obo/MONDO_0000001",
                    "ontology_name": "mondo",
                    "short_form": "MONDO_0000001",
                    "description": ["A MONDO term"],
                },
                {
                    "label": "DOID term",
                    "iri": "http://purl.obolibrary.org/obo/DOID_0000001",
                    "ontology_name": "doid",
                    "short_form": "DOID_0000001",
                    "description": ["A DOID term"],
                },
            ]
        }
    }


@pytest.fixture
def create_ebi_snapshot_from_mock() -> Any:
    """Helper function to create snapshots from mock data."""

    def _create_snapshot(
        disease_name: str,
        mock_data: dict[str, Any],
        snapshot_manager: Any | None = None,
    ) -> str:
        """Create a snapshot from mock data.

        Args:
            disease_name: Disease name for the snapshot
            mock_data: Mock response data
            snapshot_manager: Optional snapshot manager instance
        """
        if not snapshot_manager:
            from snapshots.pytest_plugin import create_snapshot_from_mock

            from drug_discovery_agent.utils.constants import EBI_ENDPOINT

            params = {"q": disease_name, "ontology": "efo"}
            return create_snapshot_from_mock(  # type: ignore[no-any-return]
                url=EBI_ENDPOINT, method="GET", params=params, mock_data=mock_data
            )

        # Use provided snapshot manager
        from drug_discovery_agent.utils.constants import EBI_ENDPOINT

        params = {"q": disease_name, "ontology": "efo"}
        key = snapshot_manager.generate_key(EBI_ENDPOINT, "GET", params)

        metadata = {
            "url": EBI_ENDPOINT,
            "method": "GET",
            "request_params": params,
            "status_code": 200,
            "content_type": "application/json",
        }

        snapshot_manager.save_snapshot(key, mock_data, metadata)
        return key  # type: ignore[no-any-return]

    return _create_snapshot


# Integration test fixtures
@pytest.fixture
def ebi_integration_test_data() -> dict[str, Any]:
    """Test data for EBI integration tests."""
    return {
        "diseases_to_test": ["alzheimer disease", "COVID-19", "diabetes mellitus"],
        "min_results_expected": {
            "alzheimer disease": 1,
            "COVID-19": 1,
            "diabetes mellitus": 3,
        },
        "required_fields": ["label", "iri", "ontology", "ontology_id"],
    }


@pytest.fixture
def ebi_snapshot_validation_helper() -> Any:
    """Helper for validating EBI snapshots."""

    def _validate_snapshot(snapshot_data: dict[str, Any]) -> bool:
        """Validate EBI snapshot structure and content.

        Args:
            snapshot_data: Snapshot data to validate

        Returns:
            True if valid, False otherwise
        """
        # Check basic structure
        if "response" not in snapshot_data:
            return False

        response = snapshot_data["response"]
        if not isinstance(response, dict) or "docs" not in response:
            return False

        docs = response["docs"]
        if not isinstance(docs, list):
            return False

        # Validate each document
        required_fields = ["label", "iri", "ontology_name", "short_form"]
        for doc in docs:
            if not isinstance(doc, dict):
                return False

            # Check required fields exist
            for field in required_fields:
                if field not in doc:
                    return False

            # If it's an EFO term, validate the format
            short_form = doc.get("short_form", "")
            if short_form.startswith("EFO"):
                if not short_form.startswith("EFO_"):
                    return False

                iri = doc.get("iri", "")
                if "ebi.ac.uk/efo/" not in iri:
                    return False

        return True

    return _validate_snapshot


# Mock data for snapshot creation
@pytest.fixture
def ebi_comprehensive_mock_data() -> dict[
    str, dict[str, dict[str, list[dict[str, Any]]]]
]:
    """Comprehensive mock data for creating diverse snapshots."""
    return {
        "alzheimer_disease": {
            "response": {
                "docs": [
                    {
                        "label": "Alzheimer disease",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000249",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000249",
                        "description": [
                            "A neurodegenerative disease characterized by progressive dementia"
                        ],
                    },
                    {
                        "label": "Early-onset Alzheimer disease",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0009636",
                        "ontology_name": "efo",
                        "short_form": "EFO_0009636",
                        "description": ["Alzheimer disease with onset before age 65"],
                    },
                ]
            }
        },
        "covid19": {
            "response": {
                "docs": [
                    {
                        "label": "COVID-19",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0009932",
                        "ontology_name": "efo",
                        "short_form": "EFO_0009932",
                        "description": ["Coronavirus disease 2019"],
                    }
                ]
            }
        },
        "cancer": {
            "response": {
                "docs": [
                    {
                        "label": "cancer",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000311",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000311",
                        "description": ["A disease of cellular proliferation"],
                    },
                    {
                        "label": "carcinoma",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000313",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000313",
                        "description": ["A malignant neoplasm"],
                    },
                    {
                        "label": "adenocarcinoma",
                        "iri": "http://www.ebi.ac.uk/efo/EFO_0000305",
                        "ontology_name": "efo",
                        "short_form": "EFO_0000305",
                        "description": [
                            "A carcinoma that arises from glandular tissue"
                        ],
                    },
                ]
            }
        },
    }
