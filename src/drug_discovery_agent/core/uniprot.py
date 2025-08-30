from typing import Any

import httpx

from drug_discovery_agent.utils.constants import VIRUS_UNIPROT_REST_API_BASE
from drug_discovery_agent.utils.http_client import make_fasta_request


class UniProtClient:
    """Client for UniProt database operations."""

    async def get_fasta_sequence(self, uniprot_code: str) -> str:
        """Fetch FASTA sequence from UniProt.

        Args:
            uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

        Returns:
            A string containing the protein sequence in FASTA format.
        """
        url = f"{VIRUS_UNIPROT_REST_API_BASE}/{uniprot_code}.fasta"
        data = await make_fasta_request(url)
        return data or ""

    async def get_details(self, uniprot_code: str) -> dict[str, Any]:
        """Fetch protein metadata from UniProt.

        Args:
            uniprot_code: UniProt accession code (e.g., P0DTC2).

        Returns:
            dict: Contains organism, scientific name, lineage, function, reference URL, etc.
        """
        url = f"{VIRUS_UNIPROT_REST_API_BASE}/{uniprot_code}.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code != 200:
            return {
                "error": f"Could not retrieve data for UniProt code '{uniprot_code}'.",
                "status_code": response.status_code,
            }

        entry = response.json()

        # Extract useful details
        result = {
            "accession": entry.get("primaryAccession", "UNKNOWN"),
            "organism": entry.get("organism", {}).get("scientificName"),
            "lineage": " → ".join(entry.get("organism", {}).get("lineage", [])),
            "taxonomy_id": entry.get("organism", {}).get("taxonId", "NONE"),
        }

        # Affected hosts
        hosts = []
        for host in entry.get("organismHosts", []):
            if "scientificName" in host:
                hosts.append(host["scientificName"] + "(" + host["commonName"] + ")")
        result["hosts"] = ",".join(hosts)

        # Functionality of this virus in Plaintext
        comments = entry.get("comments", [])
        for comment in comments:
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts and isinstance(texts, list):
                    result["function"] = texts[0].get("value")
                break

        # Parse protein name safely
        protein_name = "Unknown"
        try:
            protein_section = entry.get("proteinDescription", {})
            recommended = protein_section.get("recommendedName") or {}
            if isinstance(recommended, list):
                recommended = recommended[0]
            full_name = recommended.get("fullName")
            if isinstance(full_name, dict):
                protein_name = full_name.get("value", "Unknown")
            elif isinstance(full_name, str):
                protein_name = full_name
        except Exception:
            protein_name = "Unknown"

        result["virus_protein_name"] = protein_name

        # Extract sequence
        sequence = entry.get("sequence", {}).get("value")

        # Compile result
        result["virus_protein_sequence"] = sequence

        # Reference url
        reference = VIRUS_UNIPROT_REST_API_BASE + "/" + uniprot_code
        result["Reference"] = reference
        return result

    async def get_pdb_ids(self, uniprot_id: str) -> list[str]:
        """Fetch top 10 representative PDB entries from UniProt cross-references.

        Args:
            uniprot_id: A valid UniProt accession (e.g., 'P0DTC2').

        Returns:
            list[str]: Up to 10 unique PDB IDs linked to the protein.
        """
        url = f"{VIRUS_UNIPROT_REST_API_BASE}/{uniprot_id}.json"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        pdb_ids = [
            xref["id"]
            for xref in data.get("uniProtKBCrossReferences", [])
            if xref.get("database") == "PDB"
        ]

        return sorted(set(pdb_ids))[:10]
