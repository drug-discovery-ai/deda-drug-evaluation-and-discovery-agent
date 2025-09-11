# import asyncio
# import hashlib
# import json
# import time
# from pathlib import Path

# import aiofiles  # async file I/O

# from drug_discovery_agent.core.ebi import EBIClient
# from drug_discovery_agent.core.opentarget import OpenTargetsClient
# from drug_discovery_agent.core.alphafold import AlphaFoldClient

# CACHE_DIR = Path("/tmp/opentarget_cache")
# CACHE_DIR.mkdir(parents=True, exist_ok=True)


# def make_hash(value: str) -> str:
#     """Create a short hash from ontology ID or other string."""
#     return hashlib.sha256(value.encode()).hexdigest()[:16]


# async def main():
#     disease = EBIClient()
#     ot_client = OpenTargetsClient()

#     # 1. Fetch ontology IDs
#     disease_result = await disease.fetch_all_ontology_ids("chicken pox")
#     if not disease_result:
#         print("No ontology IDs found.")
#         return None

#     # 2. Pick one (2nd element in this case)
#     chosen = disease_result[1]
#     ontology_id = chosen["ontology_id"]
#     print("Chosen ontology_id:", ontology_id)

#     # 3. Build cache path
#     cache_file = CACHE_DIR / f"{make_hash(ontology_id)}.json"

#     if cache_file.exists():
#         print(f"Cache hit: {cache_file}")
#         async with aiofiles.open(cache_file) as f:
#             data = await f.read()
#         return json.loads(data)

#     print("Cache miss, fetching from OpenTargets...")
#     result = await ot_client.disease_target_knowndrug_pipeline(ontology_id)

#     # Save to cache (async)
#     async with aiofiles.open(cache_file, "w") as f:
#         await f.write(json.dumps(result, indent=2))
#     print(f"Saved result to {cache_file}")

#     return result


# if __name__ == "__main__":
#     start = time.perf_counter()
#     result = asyncio.run(main())
#     end = time.perf_counter()

#     if result is not None:
#         # print(json.dumps(result, indent=2))
#         print("Total latency:", f"{end - start:.3f} seconds")
