# server.py
import uvicorn
from fastmcp.prompts.prompt import Message
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import PromptMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# Import new class-based tool container
from .tools import bio_tools, mcp

# ========= REST ENDPOINTS =========


async def rest_get_details_protein(request: Request) -> JSONResponse:
    try:
        uniprot_code = request.query_params["uniprot_code"]
        result = await bio_tools.get_virus_protein_details.fn(uniprot_code)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_analyze_sequence_properties(request: Request) -> JSONResponse:
    try:
        uniprot_code = request.query_params["uniprot_code"]
        result = await bio_tools.analyze_protein_sequence_properties.fn(uniprot_code)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_experimental_structure_details(request: Request) -> JSONResponse:
    try:
        pdb_id = request.query_params["pdb_id"]
        result = await bio_tools.get_experimental_structure_details.fn(pdb_id)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def rest_get_ligand_smiles_from_uniprot(request: Request) -> JSONResponse:
    try:
        uniprot_code = request.query_params["uniprot_code"]
        result = await bio_tools.get_ligand_smiles_from_uniprot.fn(uniprot_code)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ========= INITIAL PROMPTS =========
@mcp.prompt()
def get_initial_prompts() -> list[PromptMessage]:
    return [
        Message(
            "You are the DEDA Bioinformatics Assistant — a retrieval-augmented agent that navigates the Disease → Target → Drug → Structure pipeline. "
            "You intelligently infer user intent and call the most appropriate MCP tool to gather accurate biological information. "
            "When the input is a disease name, use `get_possible_diseases_list` to retrieve ontology matches (EFO terms) and ask the user to confirm one before proceeding. "
            "After an ontology ID is confirmed, call `get_disease_targets` to retrieve target proteins, genetic constraints, and known drugs from OpenTargets. "
            "For any UniProt protein accession, use `get_virus_protein_details` to obtain biological metadata and sequence information, or "
            "`analyze_sequence_properties` to calculate molecular weight, pI, and amino acid composition. "
            "When users ask about ligands, inhibitors, or binding partners, use `get_ligand_smiles_from_uniprot` to fetch co-crystallized small molecules and SMILES data. "
            "For structural or experimental metadata, use `get_experimental_structure_details` with a valid PDB ID. "
            "Always choose tools based on available identifiers (disease name, ontology ID, UniProt ID, or PDB ID) and inferred context — never guess. "
            "If the input is ambiguous, ask clarifying questions. "
            "If no valid data is found, respond with 'No data found' and do not fabricate results. "
            "Keep responses concise, factual, and scientifically clear, emphasizing how diseases, targets, drugs, and protein structures connect mechanistically.",
            role="user",
        )
    ]


# ========= STARLETTE APP CREATION =========
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE."""
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


# ========= MAIN ENTRY POINT =========
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

    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
