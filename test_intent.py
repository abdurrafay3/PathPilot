# test_intent.py

import asyncio
from dotenv import load_dotenv
from app.agents.route_planner import plan_route
from app.schemas.agent_state import Coordinates, RoutePlannerContext
import logging
from dotenv import load_dotenv
from app.agents.intent_normalizer import normalize_intent
from app.agents.geocoder import get_region_context  

logger = logging.getLogger(__name__)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.getLogger("openai").setLevel(logging.WARNING)
# dummy location for testing
current_location = Coordinates(
    lat=22.3375,
    lng=114.2630
)


context = RoutePlannerContext(
    intent_output=None,
    geocoder_output=None,
    candidate_route_output=None
)

async def main():
    region_context = await get_region_context(current_location)
    intent_output = await normalize_intent("take me to centrl with a hospitl on the way and don't walk too much and I want to take public transport only", current_location=current_location, region_context=region_context)
    context.intent_output = intent_output
    candidate_routes = await plan_route(context)
    logger.info(f"\033[92mCandidate routes are now fetched!\033[0m")


asyncio.run(main())