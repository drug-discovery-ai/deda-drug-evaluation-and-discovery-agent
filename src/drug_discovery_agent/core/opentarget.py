import json
from pathlib import Path
from typing import Any, cast

import aiofiles  # type: ignore
import httpx

from drug_discovery_agent.core.common import make_hash
from drug_discovery_agent.utils.constants import (
    OPENTARGET_CACHE_DIR,
    OPENTARGET_ENDPOINT,
)


class OpenTargetsClient:
    BASE_URL = OPENTARGET_ENDPOINT

    CACHE_DIR = Path(OPENTARGET_CACHE_DIR)

    def __init__(self) -> None:
        self.limit = 10
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def _make_graphql_request(
        self, query: str, variables: dict
    ) -> dict[str, Any] | None:
        """Make a GraphQL request."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.BASE_URL,
                    json={"query": query, "variables": variables},
                    timeout=15.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data

            except Exception as e:
                print(f"Request failed: {e}")
                return None

    # Disease
    async def fetch_disease_details(self, ontology_id: str) -> dict[str, Any] | None:
        """Fetch Disease metadata from OpenTargets GraphQL API."""

        query = """
        query diseaseTargets($efoId: String!) {
          disease(efoId: $efoId) {
            id
            name
            description
          }
        }
        """
        variables = {"efoId": ontology_id, "size": self.limit}

        raw = await self._make_graphql_request(query, variables)
        if raw and "data" in raw:
            return cast(dict[str, Any], raw["data"])
        return None

    async def fetch_disease_to_target_association(
        self, ontology_id: str
    ) -> dict[str, Any] | None:
        """Find the targets on human body associated with the disease (ontology_id) from OpenTargets GraphQL API."""
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
        variables = {"efoId": ontology_id, "size": self.limit}

        raw = await self._make_graphql_request(query, variables)
        if raw and "data" in raw:
            return cast(dict[str, Any], raw["data"])
        return None

    async def fetch_disease_associated_target_details(
        self, ontology_id: str
    ) -> list[dict[str, Any]]:
        """Extract clean target info for given disease ontology_id."""

        data: dict[str, Any] | None = await self.fetch_disease_to_target_association(
            ontology_id
        )

        if data is None:
            return []
        rows = data["disease"]["associatedTargets"]["rows"]

        results: list[dict[str, Any]] = []
        for row in rows:
            # Fetch details for Target

            target_info = await self.fetch_target_details_info(row["target"]["id"])
            results.append(
                {
                    "approved_symbol": row["target"]["approvedSymbol"],
                    "target_id": row["target"]["id"],
                    "description": row["target"]["functionDescriptions"],
                    "score": row["score"],
                    "target_details": target_info,
                }
            )

        return results

    # Target, input target_id, retrieved from fetch_disease_associated_target_details/fetch_disease_to_target_association
    async def fetch_target_details_info(self, target_id: str) -> dict[str, Any] | None:
        """
        Fetch basic information for a target using Ensembl ID.
        """
        query = """
        query targetInfo($ensemblId: String!) {
          target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            approvedName
            biotype
            functionDescriptions
            geneticConstraint{
                exp
                constraintType
                oeLower
                upperBin6
                score
                obs
                upperRank
            }
            tractability{
                modality
                label
                value
            }
            proteinIds{
                source
                id
            }
            knownDrugs{
                count
                rows{
                    targetId
                    drugId
                    drugType
                    approvedName
                }
            }
          }
        }
        """
        variables = {"ensemblId": target_id}

        raw = await self._make_graphql_request(query, variables)
        if not raw:
            return None

        if "errors" in raw:
            print(f"GraphQL error: {raw['errors']}")
            return None

        target = raw.get("data", {}).get("target")
        return target if target else None

    # Drug , takes input drugID, retrieved from fetch_target_details_info
    async def fetch_drug_details_info(self, drug_id: str) -> dict[str, Any] | None:
        """
        Fetch basic information for a drug using its ChEMBL ID.
        """
        query = """
        query drugInfo($chemblId: String!) {
          drug(chemblId: $chemblId) {
            description
            drugType
            isApproved
            crossReferences{
                ids
                source
            }
          }
        }
        """
        variables = {"chemblId": drug_id}

        raw = await self._make_graphql_request(query, variables)
        if not raw:
            return None

        if "errors" in raw:
            print(f"GraphQL error for drug {drug_id}: {raw['errors']}")
            return None

        drug = raw.get("data", {}).get("drug")
        return drug if drug else None

    ############### Pipelines ############################

    # Disease -> Target -> knownDrugs
    async def disease_target_knowndrug_pipeline(
        self, ontology_id: str
    ) -> dict[str, Any]:
        """Return a merged object: disease metadata + all associated targets details"""

        # First check if cache hit

        cache_file = self.CACHE_DIR / f"{make_hash(ontology_id)}.json"

        if cache_file.exists():
            print(f"Cache hit: {cache_file}")
            async with aiofiles.open(cache_file) as f:
                data_cache = await f.read()
                return cast(dict[str, Any], json.loads(data_cache))

        data: dict[str, Any] | None = await self.fetch_disease_details(ontology_id)

        if data is None or data.get("disease") is None:
            return {}
        disease_data = data["disease"]
        disease_meta = {
            "id": disease_data["id"],
            "name": disease_data["name"],
            "description": disease_data["description"],
        }

        # target details
        targets = await self.fetch_disease_associated_target_details(ontology_id)

        result: dict[str, Any] = {}

        result["disease"] = disease_meta
        result["targets"] = targets

        # Save to cache (async)
        async with aiofiles.open(cache_file, "w") as f:
            await f.write(json.dumps(result, indent=2))
        print(f"Saved result to {cache_file}")

        return result
