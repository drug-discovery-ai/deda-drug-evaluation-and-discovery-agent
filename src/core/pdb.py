"""PDB-related bioinformatics functions."""
from typing import List, Dict, Any
import httpx
from ..utils.constants import RCSB_DB_ENDPOINT
from .uniprot import fetch_top_pdb_ids_for_uniprot


async def fetch_structure_details(pdb_id: str) -> Dict[str, Any]:
    """Get experimental structure details from RCSB PDB.
    
    Args:
        pdb_id: The 4-character PDB ID (e.g., '4HHB').

    Returns:
        dict: Metadata including structure title, method, resolution, and download link.
    """
    url = f"{RCSB_DB_ENDPOINT}/{pdb_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            entry = response.json()
    except httpx.HTTPStatusError:
        return {"error": f"No entry found for PDB ID: {pdb_id}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

    return {
        "pdb_id": pdb_id.upper(),
        "title": entry.get("struct", {}).get("title"),
        "method": entry.get("exptl", [{}])[0].get("method"),
        "resolution": next(iter(entry.get("rcsb_entry_info", {}).get("resolution_combined", [])), None),
        "deposited_atoms": entry.get("rcsb_entry_info", {}).get("deposited_atom_count"),
        "release_date": entry.get("rcsb_accession_info", {}).get("initial_release_date"),
        "keywords": entry.get("struct_keywords", {}).get("pdbx_keywords"),
        "structure_url": f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    }


async def fetch_ligand_smiles_from_uniprot(uniprot_id: str) -> List[Dict[str, Any]]:
    """Fetch ligands from PDB structures related to a UniProt ID.
    
    Args:
        uniprot_id: A valid UniProt accession (e.g., 'P0DTC2').

    Returns:
        list[dict]: Ligand metadata including ID, name, formula, and SMILES.
    """
    pdb_ids = await fetch_top_pdb_ids_for_uniprot(uniprot_id)

    ligands = []

    try:
        async with httpx.AsyncClient() as client:
            # For each PDB ID, extract ligand info from RCSB
            for pdb_id in pdb_ids:
                entry_url = f"{RCSB_DB_ENDPOINT}/{pdb_id}"

                entry_resp = await client.get(entry_url, timeout=10)
                if entry_resp.status_code != 200:
                    continue
                entry = entry_resp.json()
                entity_ids = entry.get("rcsb_entry_container_identifiers", {}).get("non_polymer_entity_ids", [])

                for eid in entity_ids:
                    ligand_url = f"https://data.rcsb.org/rest/v1/core/nonpolymer_entity/{pdb_id}/{eid}"
                    ligand_resp = await client.get(ligand_url, timeout=10)
                    if ligand_resp.status_code != 200:
                        continue
                    ligand_data = ligand_resp.json()

                    ligands.append(ligand_data)

        return ligands[:10]  # return top 10 ligands total

    except Exception as e:
        return [{"error": str(e)}]