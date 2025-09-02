from typing import Any, cast

import httpx


class OpenTargetsClient:
    BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

    def __init__(self, ontology_id: str, limit: int = 100) -> None:
        self.ontology_id = ontology_id
        self.limit = limit

    async def fetch_target_disease_association_for_opentarget(self) -> dict[str, Any]:
        """Fetch raw disease + target data from OpenTargets GraphQL API."""
        query = """
        query diseaseTargets($efoId: String!, $size: Int!) {
          disease(efoId: $efoId) {
            id
            name
            description
            associatedTargets(page: {size: $size, index: 0}) {
              rows {
                target {
                  approvedSymbol
                  id
                  functionDescriptions
                }
                score
              }
            }
          }
        }
        """
        variables = {"efoId": self.ontology_id, "size": self.limit}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.BASE_URL,
                json={"query": query, "variables": variables},
                timeout=15.0,
            )
            response.raise_for_status()
            raw: dict[str, Any] = response.json()
            return cast(dict[str, Any], raw["data"])

    async def fetch_disease_associated_target(self) -> list[dict[str, Any]]:
        """Extract clean target info for given disease ontology_id."""
        data: dict[str, Any] = await self.fetch_target_disease_association_for_opentarget()
        rows = data["disease"]["associatedTargets"]["rows"]

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "approved_symbol": row["target"]["approvedSymbol"],
                    "target_id": row["target"]["id"],
                    "description": row["target"]["functionDescriptions"],
                    "score": row["score"],
                }
            )
        return results

    async def disease_with_targets(self) -> dict[str, Any]:
        """Return a merged object: disease metadata + all associated targets."""
        data: dict[str, Any] = await self.fetch_target_disease_association_for_opentarget()
        disease_meta = {
            "id": data["disease"]["id"],
            "name": data["disease"]["name"],
            "description": data["disease"]["description"],
        }

        targets = await self.fetch_disease_associated_target()
        return {"disease": disease_meta, "targets": targets}
