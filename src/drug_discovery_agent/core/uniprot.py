from typing import Any

import httpx

from drug_discovery_agent.utils.constants import VIRUS_UNIPROT_REST_API_BASE


class UniProtClient:
    """Client for UniProt database operations."""

    def __init__(self) -> None:
        """Initialize UniProt client."""
        pass

    async def _make_request(self, url: str, expected_format: str = "json") -> Any:
        """Make an HTTP request (HTTP interceptor handles snapshots/mocks transparently).

        Args:
            url: URL to request
            expected_format: Expected response format ("json" or "text")

        Returns:
            Response data or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)

                if response.status_code != 200:
                    if expected_format == "json":
                        return {
                            "error": f"Could not retrieve data from {url}",
                            "status_code": response.status_code,
                        }
                    else:
                        return ""

                response.raise_for_status()

                # Extract data based on format
                if expected_format == "text":
                    return response.text
                else:
                    return response.json()

        except Exception as e:
            print(f"Request failed for {url}: {e}")
            return "" if expected_format == "text" else {}

    async def get_fasta_sequence(self, uniprot_code: str) -> str:
        """Fetch FASTA sequence from UniProt.

        Args:
            uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

        Returns:
            A string containing the protein sequence in FASTA format.
        """
        url = f"{VIRUS_UNIPROT_REST_API_BASE}/{uniprot_code}.fasta"
        data = await self._make_request(url, expected_format="text")
        return data or ""

    async def get_details(self, uniprot_code: str) -> dict[str, Any]:
        """Fetch protein metadata from UniProt.

        Args:
            uniprot_code: UniProt accession code (e.g., P0DTC2).

        Returns:
            dict: Contains organism, scientific name, lineage, function, reference URL, etc.
        """
        url = f"{VIRUS_UNIPROT_REST_API_BASE}/{uniprot_code}.json"

        entry = await self._make_request(url, expected_format="json")

        # Handle error responses
        if isinstance(entry, dict) and "error" in entry:
            return entry

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

        data = await self._make_request(url, expected_format="json")

        # Handle error responses or empty data
        if not isinstance(data, dict) or "error" in data:
            return []

        pdb_ids = [
            xref["id"]
            for xref in data.get("uniProtKBCrossReferences", [])
            if xref.get("database") == "PDB"
        ]

        return sorted(set(pdb_ids))[:10]
