from typing import Any

import httpx

from drug_discovery_agent.utils.constants import EBI_ENDPOINT


class EBIClient:
    def __init__(self) -> None:
        self.ontology_matches: list[dict[str, Any]] = []  # store all matches

    async def fetch_all_ontology_ids(self, disease_name: str) -> list[dict[str, Any]]:
        """Fetch all matching EFO ontology IDs for the given disease name.

        Returns:
            List[Dict[str, Any]]: List of ontology match dictionaries.
        """
        url = EBI_ENDPOINT
        params = {"q": disease_name, "ontology": "efo"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, timeout=10, params=params, follow_redirects=True
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code} for disease: {disease_name}")
            return []
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return []

        data: dict[str, Any] = response.json()
        return self._process_response_data(data, disease_name)

    def _process_response_data(
        self, data: dict[str, Any], disease_name: str
    ) -> list[dict[str, Any]]:
        """Process API response data and extract ontology matches.

        Args:
            data: Raw API response data
            disease_name: Disease name for logging

        Returns:
            List of processed ontology matches
        """
        docs: list[dict[str, Any]] = data.get("response", {}).get("docs", [])
        if not docs:
            print(f"No EFO IDs found for {disease_name}")
            return []

        # Save all matches, but only keep those where short_form starts with "EFO"
        self.ontology_matches = [
            {
                "label": doc.get("label"),
                "iri": doc.get("iri"),
                "ontology": doc.get("ontology_name"),
                "ontology_id": doc.get("short_form"),
                "description": doc.get("description", None),
            }
            for doc in docs
            if doc.get("short_form", "").startswith("EFO")
        ]

        return self.ontology_matches
