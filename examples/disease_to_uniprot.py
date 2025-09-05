import asyncio
import json

from drug_discovery_agent.core.ebi import EBIClient
from drug_discovery_agent.core.opentarget import OpenTargetsClient


async def main() -> None:
    disease = EBIClient()
    disease_result = await disease.fetch_all_ontology_ids("chcicken pox")

    print(disease_result[0]["ontology_id"])

    # choose one candidate randomly

    ot_client = OpenTargetsClient()

    result = await ot_client.disease_target_knowndrug_pipeline(
        disease_result[0]["ontology_id"]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
