from typing import Any

import httpx

from drug_discovery_agent.utils.constants import ALPHAFOLD_ENDPOINT


class AlphaFoldClient:
    def __init__(self) -> None:
        pass

    async def fetch_alphafold_prediction(self, uniprot: str) -> list[dict[str, Any]]:
        """Fetch all matching EFO ontology IDs for the given disease name.

        Returns:
            List[Dict[str, Any]]: List of ontology match dictionaries.
        """
        url = ALPHAFOLD_ENDPOINT + "/" + uniprot
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10, follow_redirects=True)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code} for uniprot: {uniprot}")
            return []
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return []

        data: list[dict[str, Any]] = response.json()

        return data
