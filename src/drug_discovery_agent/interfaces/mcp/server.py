from typing import Any

import uvicorn
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Message
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import PromptMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient

uniprot_client = UniProtClient()
pdb_client = PDBClient(uniprot_client)
sequence_analyzer = SequenceAnalyzer(uniprot_client)

# Initialize FastMCP server for FASTA tools (SSE)
mcp = FastMCP("FASTA")


@mcp.tool(
    name="get_virus_protein_FASTA_format_sequence",
    description="Retrieves the amino acid sequence in FASTA format for a given viral protein using its UniProt accession code.",
)
async def get_fasta_protein(uniprot_code: str) -> str:
    """MCP wrapper that delegates to core function.

    Given a UniProt accession code for a virus protein, return its sequence in FASTA format.

    This tool retrieves the amino acid sequence of the specified viral protein using its UniProt code.

    Example:
        Input: "P0DTC2"
        Output: A string in FASTA format representing the spike protein of SARS-CoV-2.

    Args:
        uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

    Returns:
        A string containing the protein sequence in FASTA format.
    """
    return await uniprot_client.get_fasta_sequence(uniprot_code)


@mcp.tool(
    name="get_virus_protein_details",
    description="Retrieve virus protein metadata (organism, species, lineage, function) from UniProt given an accession code like 'P0DTC2'.",
)
async def get_virus_protein_details(uniprot_code: str) -> dict[str, Any]:
    """MCP wrapper that delegates to core function.

    Returns structured metadata about a viral protein from UniProt.

    Args:
        uniprot_code (str): UniProt accession code (e.g., P0DTC2).

    Returns:
        dict: Contains organism, scientific name, lineage, function, reference URL, RCSB structural details url etc.
    """
    return await uniprot_client.get_details(uniprot_code)


@mcp.tool(
    name="analyze_sequence_properties",
    description="Analyze length, molecular weight (kDa), isoelectric point (pI), and composition of a protein sequence. Use 'get_fasta_protein' to retrieve the sequence for a UniProt ID.",
)
async def analyze_protein_sequence_properties(uniprot_code: str) -> dict[str, Any]:
    """MCP wrapper that delegates to core function.

    Analyze properties of a protein sequence (raw or FASTA) for a viral protein by its UniProt accession code.

    Args:
        uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

    Returns:
        dict: {
            length: int,
            molecular_weight_kda: float,
            isoelectric_point: float,
            composition: dict
        }
    """
    return await sequence_analyzer.analyze_from_uniprot(uniprot_code)


@mcp.tool(
    name="compare_protein_variant",
    description=(
        "Compares a mutated protein (e.g., D614G) against the reference from UniProt. "
        "Returns changes in sequence, molecular weight, pI, and composition."
    ),
)
async def compare_variant_protein(uniprot_id: str, mutation: str) -> dict[str, Any]:
    """MCP wrapper that delegates to core function.

    Applies a mutation like D614G to a protein sequence from UniProt and compares
    basic properties between the wildtype and the variant.

    Args:
        uniprot_id (str): UniProt accession (e.g., "P0DTC2").
        mutation (str): Mutation string in format D614G.

    Returns:
        dict: Differences in molecular weight, charge, and other properties.
    """
    return await sequence_analyzer.compare_variant(uniprot_id, mutation)


@mcp.tool(
    name="get_top_pdb_ids_for_uniprot",
    description="Returns up to 10 representative PDB IDs for a given UniProt protein. Useful for fetching 3D structures without flooding the client.",
)
async def get_top_pdb_ids_for_uniprot(uniprot_id: str) -> list[str]:
    """MCP wrapper that delegates to core function.

    Fetches top 10 representative PDB entries from UniProt cross-references.
    Returned PDB entries help in identifying structural details of the protein from the RCSB Database.

    Args:
        uniprot_id (str): A valid UniProt accession (e.g., 'P0DTC2').

    Returns:
        list[str]: Up to 10 unique PDB IDs linked to the protein.
    """
    return await uniprot_client.get_pdb_ids(uniprot_id)


@mcp.tool(
    name="get_experimental_structure_details",
    description="Fetches experimental structure metadata from RCSB PDB using a valid PDB ID (e.g., '4HHB'). Useful for grounding structure-related queries with resolution, method, and official description.",
)
async def get_experimental_structure_details(pdb_id: str) -> dict[str, Any]:
    """MCP wrapper that delegates to core function.

    Given a PDB ID, returns curated structure metadata from RCSB PDB.

    Args:
        pdb_id (str): The 4-character PDB ID (e.g., '4HHB').

    Returns:
        dict: Metadata including structure title, method, resolution, and download link.
    """
    return await pdb_client.get_structure_details(pdb_id)


@mcp.tool(
    name="get_ligand_smiles_from_uniprot",
    description=(
        "Fetches up to 10 ligands (non-polymer entities) co-crystallized with PDB structures related to a UniProt ID. "
        "Returns each ligand's SMILES, formula, and name. Useful for grounding small molecule binding partners of a protein."
    ),
)
async def get_ligand_smiles_from_uniprot(uniprot_id: str) -> list[dict[str, Any]]:
    """MCP wrapper that delegates to core function.

    Given a UniProt ID, returns ligand details (SMILES, formula) from top related PDB structures.

    Args:
        uniprot_id (str): A valid UniProt accession (e.g., 'P0DTC2').

    Returns:
        list[dict]: Ligand metadata including ID, name, formula, and SMILES.
    """
    return await pdb_client.get_ligands_for_uniprot(uniprot_id)


# REST-style endpoints that wrap MCP tools
async def rest_get_fasta_protein(request: Request) -> JSONResponse:
    try:
        state = request.query_params["uniprot_code"]
        result = await get_fasta_protein.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_details_protein(request: Request) -> JSONResponse:
    try:
        state = request.query_params["uniprot_code"]
        result = await get_virus_protein_details.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_analyze_sequence_properties(request: Request) -> JSONResponse:
    try:
        state = request.query_params["uniprot_code"]
        result = await analyze_protein_sequence_properties.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_top_pdb_ids_for_uniprot(request: Request) -> JSONResponse:
    try:
        state = request.query_params["uniprot_code"]
        result = await get_top_pdb_ids_for_uniprot.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_experimental_structure_details(request: Request) -> JSONResponse:
    try:
        state = request.query_params["pdb_id"]
        result = await get_experimental_structure_details.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_ligand_smiles_from_uniprot(request: Request) -> JSONResponse:
    try:
        state = request.query_params["uniprot_code"]
        result = await get_ligand_smiles_from_uniprot.fn(state)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@mcp.prompt()
def get_initial_prompts() -> list[PromptMessage]:
    return [
        Message(
            "You are a knowledgeable bioinformatics assistant. "
            "You help users prepare molecular inputs for docking and drug discovery workflows, particularly for the Boltz system. "
            "You can fetch protein information from UniProt, download FASTA or PDB data, explain virus protein structures, and guide users on formatting inputs. "
            "When needed, you call the appropriate tools to fetch sequence data, provide metadata, or guide formatting. "
            "Always ask clarifying questions if input is ambiguous. "
            "Keep your responses concise, scientific, and user-friendly.",
            role="user",
        )
    ]


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/rest/get_fasta", endpoint=rest_get_fasta_protein, methods=["GET"]),
            Route(
                "/rest/get_protein_details",
                endpoint=rest_get_details_protein,
                methods=["GET"],
            ),
            Route(
                "/rest/analyze_sequence_properties",
                endpoint=rest_analyze_sequence_properties,
                methods=["GET"],
            ),
            Route(
                "/rest/top_pdb_ids",
                endpoint=rest_get_top_pdb_ids_for_uniprot,
                methods=["GET"],
            ),
            Route(
                "/rest/get_experimental_structure_details",
                endpoint=rest_get_experimental_structure_details,
                methods=["GET"],
            ),
            Route(
                "/rest/get_ligand_smiles_from_uniprot",
                endpoint=rest_get_ligand_smiles_from_uniprot,
                methods=["GET"],
            ),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def main() -> None:
    """Main entry point for the MCP server."""
    mcp_server = mcp._mcp_server

    import argparse

    from ...config import BACKEND_HOST, BACKEND_PORT

    parser = argparse.ArgumentParser(description="Run MCP SSE-based server")
    parser.add_argument("--host", default=BACKEND_HOST, help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=BACKEND_PORT, help="Port to listen on"
    )
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
