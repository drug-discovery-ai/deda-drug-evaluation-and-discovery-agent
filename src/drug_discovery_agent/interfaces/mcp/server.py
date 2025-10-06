from typing import Any
import uvicorn
from fastmcp.prompts.prompt import Message
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import PromptMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .tools import (
    mcp,
    get_fasta_protein,
    get_virus_protein_details,
    analyze_protein_sequence_properties,
    get_top_pdb_ids_for_uniprot,
    get_experimental_structure_details,
    get_ligand_smiles_from_uniprot,
)


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
