import json, os
import asyncio, random
from pathlib import Path
from functools import cache

MOCK = os.getenv("MOCK_EXTERNAL") == "1"
FIXTURE_PATH =  Path(__file__).parents[0] / "fixtures"
def record_fixture(name: str, data):
    """
    This function saves the response of an example call in the app pipeline. It is going to record the responses of each and then those responses are going to be later used for load-testing with fake concurrent users. Only use this function for that purpose, if the shape of any of the functions change.
    """
    if os.getenv("RECORD_FIXTURES") != "1":
        return
    # check if the file already exists
    fixture_file = FIXTURE_PATH / f"{name}.json"
    if fixture_file.exists():
        return
    fixture_file.write_text(json.dumps(data, indent=2))

@cache
def load_fixture(name: str):
    return json.loads((FIXTURE_PATH / f"{name}.json").read_text())

async def fake_latency(lo : float, hi : float):
    await asyncio.sleep(random.uniform(lo, hi))



