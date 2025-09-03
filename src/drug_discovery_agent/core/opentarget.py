from typing import Any, cast

import httpx


class OpenTargetsClient:
    BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

    def __init__(self, ontology_id: str, limit: int = 100) -> None:
        self.ontology_id = ontology_id
        self.limit = limit

    async def fetch_target_associated_drugs(
        self, target_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch drugs linked to a given target (via mechanisms of action)."""
        query = """
        query targetDrugs($ensemblId: String!, $size: Int!) {
          target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            drugs(page: {size: $size, index: 0}) {
              rows {
                drug {
                  id
                  name
                }
                mechanismOfAction
                phase
              }
            }
          }
        }
        """
        variables = {"ensemblId": target_id, "size": limit}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.BASE_URL,
                json={"query": query, "variables": variables},
                timeout=15.0,
            )
            response.raise_for_status()
            raw: dict[str, Any] = response.json()
            rows = raw["data"]["target"]["drugs"]["rows"]

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "drug_id": row["drug"]["id"],
                    "drug_name": row["drug"]["name"],
                    "mechanism": row.get("mechanismOfAction"),
                    "phase": row.get("phase"),
                }
            )
        return results

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
        data: dict[
            str, Any
        ] = await self.fetch_target_disease_association_for_opentarget()
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
        data: dict[
            str, Any
        ] = await self.fetch_target_disease_association_for_opentarget()
        disease_meta = {
            "id": data["disease"]["id"],
            "name": data["disease"]["name"],
            "description": data["disease"]["description"],
        }

        targets = await self.fetch_disease_associated_target()
        return {"disease": disease_meta, "targets": targets}

    async def disease_pipeline(self, efo_id: str, limit: int = 20) -> dict[str, Any]:
        """Disease → Targets → Drugs"""
        disease = await self.fetch_target_attributes_for_opentarget()
        targets = await self.fetch_disease_associated_target()
        enriched = []
        for t in targets:
            drugs = await self.fetch_target_associated_drugs(
                t["target_id"], limit=limit
            )
            enriched.append({**t, "drugs": drugs})
        return {"disease": disease["disease"], "targets": enriched}

    async def drug_pipeline(self, chembl_id: str, limit: int = 20) -> dict[str, Any]:
        """Drug → Targets → Diseases"""
        drug = await self.fetch_drug_associated_targets(chembl_id, limit=limit)
        enriched = []
        for m in drug["mechanisms"]:
            target_id = m["targetId"]
            diseases = await self.fetch_target_associated_diseases(
                target_id, limit=limit
            )
            enriched.append({**m, "diseases": diseases})
        return {
            "drug": {"id": drug["drug_id"], "name": drug["drug_name"]},
            "targets": enriched,
        }

    async def target_pipeline(self, ensembl_id: str, limit: int = 20) -> dict[str, Any]:
        """Target → Diseases → Drugs"""
        diseases = await self.fetch_target_associated_diseases(ensembl_id, limit=limit)
        drugs = await self.fetch_target_associated_drugs(ensembl_id, limit=limit)
        return {"target": ensembl_id, "diseases": diseases, "drugs": drugs}
