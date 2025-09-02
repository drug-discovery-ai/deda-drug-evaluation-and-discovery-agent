import asyncio
import json

from drug_discovery_agent.core.ebi import EBIClient
from drug_discovery_agent.core.opentarget import OpenTargetsClient


async def main() -> None:
    disease = EBIClient(disease_name="chicken pox")
    disease_result = await disease.fetch_all_ontology_ids()
    # choose one candidate randomly
    ot_client = OpenTargetsClient(
        disease_result[0]["ontology_id"], limit=5
    )  # chicken pox
    result = await ot_client.disease_with_targets()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
