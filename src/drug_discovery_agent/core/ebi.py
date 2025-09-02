from typing import Any

import httpx

from drug_discovery_agent.utils.constants import EBI_ENDPOINT


class EBIClient:
    def __init__(self, disease_name: str) -> None:
        """Initialize EBIClient with a disease name.

        Args:
            disease_name (str): The disease name to look up.
        """
        self.disease_name: str = disease_name
        self.ontology_matches: list[dict[str, Any]] = []  # store all matches

    async def fetch_all_ontology_ids(self) -> list[dict[str, Any]]:
        """Fetch all matching EFO ontology IDs for the given disease name.

        Returns:
            List[Dict[str, Any]]: List of ontology match dictionaries.
        """
        url = EBI_ENDPOINT
        params = {"q": self.disease_name, "ontology": "efo"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, timeout=10, params=params, follow_redirects=True
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error {e.response.status_code} for disease: {self.disease_name}"
            )
            return []
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return []

        data: dict[str, Any] = response.json()
        docs: list[dict[str, Any]] = data.get("response", {}).get("docs", [])
        if not docs:
            print(f"No EFO IDs found for {self.disease_name}")
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
