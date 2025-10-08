from typing import Any

import httpx

from drug_discovery_agent.core.uniprot import UniProtClient
from drug_discovery_agent.utils.constants import RCSB_DB_ENDPOINT


class PDBClient:
    """Client for PDB database operations."""

    def __init__(self, uniprot_client: UniProtClient | None = None):
        """Initialize PDB client with optional UniProt client.

        Args:
            uniprot_client: UniProt client instance. If None, creates a new one.
        """
        self.uniprot_client = uniprot_client or UniProtClient()

    async def _make_request(self, url: str) -> dict[str, Any]:
        """Make an HTTP request (HTTP interceptor handles snapshots/mocks transparently)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Extract PDB ID from URL for user-friendly error message
                pdb_id = url.split("/")[-1] if "/" in url else "unknown"
                return {"error": f"No entry found for PDB ID: {pdb_id}"}
            else:
                return {"error": f"HTTP {e.response.status_code} error for {url}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    async def get_structure_details(self, pdb_id: str) -> dict[str, Any]:
        """Get experimental structure details from RCSB PDB.

        Args:
            pdb_id: The 4-character PDB ID (e.g., '4HHB').

        Returns:
            dict: Metadata including structure title, method, resolution, and download link.
        """
        url = f"{RCSB_DB_ENDPOINT}/{pdb_id}"

        entry = await self._make_request(url)

        # Handle error responses
        if "error" in entry:
            return entry

        return {
            "pdb_id": pdb_id.upper(),
            "title": entry.get("struct", {}).get("title"),
            "method": entry.get("exptl", [{}])[0].get("method"),
            "resolution": next(
                iter(entry.get("rcsb_entry_info", {}).get("resolution_combined", [])),
                None,
            ),
            "deposited_atoms": entry.get("rcsb_entry_info", {}).get(
                "deposited_atom_count"
            ),
            "release_date": entry.get("rcsb_accession_info", {}).get(
                "initial_release_date"
            ),
            "keywords": entry.get("struct_keywords", {}).get("pdbx_keywords"),
            "structure_url": f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb",
        }

    async def get_ligands_for_uniprot(self, uniprot_id: str) -> list[dict[str, Any]]:
        """Fetch ligands from PDB structures related to a UniProt ID.

        Args:
            uniprot_id: A valid UniProt accession (e.g., 'P0DTC2').

        Returns:
            list[dict]: Ligand metadata including ID, name, formula, and SMILES.
        """
        try:
            pdb_ids = await self.uniprot_client.get_pdb_ids(uniprot_id)

            ligands = []

            async with httpx.AsyncClient() as client:
                # For each PDB ID, extract ligand info from RCSB
                for pdb_id in pdb_ids:
                    entry_url = f"{RCSB_DB_ENDPOINT}/{pdb_id}"

                    entry_resp = await client.get(entry_url, timeout=10)
                    if entry_resp.status_code != 200:
                        continue
                    entry = entry_resp.json()
                    entity_ids = entry.get("rcsb_entry_container_identifiers", {}).get(
                        "non_polymer_entity_ids", []
                    )

                    for eid in entity_ids:
                        ligand_url = f"https://data.rcsb.org/rest/v1/core/nonpolymer_entity/{pdb_id}/{eid}"
                        ligand_resp = await client.get(ligand_url, timeout=10)
                        if ligand_resp.status_code != 200:
                            continue
                        ligand_data = ligand_resp.json()

                        ligands.append(ligand_data)

            return ligands

        except Exception as e:
            return [{"error": str(e)}]
