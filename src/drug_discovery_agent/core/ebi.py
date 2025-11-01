from dataclasses import asdict, dataclass
from typing import Any

import httpx

from drug_discovery_agent.utils.constants import (
    EBI_ANTIGEN_REGION_DETAILS_TO_PDB,
    EBI_ENDPOINT,
)


@dataclass
class PDBMapping:
    pdb_id: str
    entity_id: int
    chain_id: str
    struct_asym_id: str
    method: str | None = None
    resolution: float | None = None
    uniprot_range: list[int] | None = None
    pdb_range: list[int] | None = None
    overlap: list[int] | None = None


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

    async def fetch_antigen_region_to_pdb_protein_data(
        self, antigen_uniprot_code: str
    ) -> list[dict[str, Any]] | None | None:
        """
        Fetch PDB mappings for a given UniProt antigen code.

        Returns a list of PDBMapping instances with entity, chain, and residue range details.
        """
        url = f"{EBI_ANTIGEN_REGION_DETAILS_TO_PDB}/{antigen_uniprot_code}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10, follow_redirects=True)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error {e.response.status_code} for UniProt: {antigen_uniprot_code}"
            )
            return []
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return []

        data: dict[str, Any] = response.json()
        pdb_data = data.get(antigen_uniprot_code, {}).get("PDB", {})
        results: list[PDBMapping] = []

        # PDBe returns a flat list of mappings per PDB ID
        for pdb_id, mappings in pdb_data.items():
            for seg in mappings:
                results.append(
                    PDBMapping(
                        pdb_id=pdb_id,
                        entity_id=seg.get("entity_id", 0),
                        chain_id=seg.get("chain_id", ""),
                        struct_asym_id=seg.get("struct_asym_id", ""),
                        uniprot_range=[seg.get("unp_start"), seg.get("unp_end")],
                        pdb_range=[
                            seg.get("start", {}).get("residue_number"),
                            seg.get("end", {}).get("residue_number"),
                        ],
                    )
                )

        return [asdict(entry) for entry in results]
