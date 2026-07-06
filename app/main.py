from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agents.geocoder import get_region_context
from app.agents.intent_normalizer import normalize_intent
from app.schemas.agent_state import Coordinates, RoutePlannerContext
from app.agents.route_planner import plan_route
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.getLogger("openai").setLevel(logging.WARNING)

class PlanRouteRequest(BaseModel):
    user_input: str
    origin: Coordinates


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def health_check() -> dict:
    """
    Health check endpoint for the FastAPI application.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "healthy"}


@app.post("/plan_route")
async def plan_route_api(request: PlanRouteRequest):
    result = await run_route_planner(request)
    return result


async def run_route_planner(request: PlanRouteRequest):
    context = RoutePlannerContext(
        intent_output=None,
        geocoder_output=None,
        candidate_route_output=None,
        waypoint_finder_output=None,
        detour_scorer_output=None,
        constraint_validator_output=None,
    )
    region_context = await get_region_context(request.origin)
    intent_output = await normalize_intent(
        request.user_input,
        current_location=request.origin,
        region_context=region_context,
    )
    context.intent_output = intent_output
    result = await plan_route(context)
    logger.info(f"\033[92mCandidate routes are now fetched!\033[0m")
    return context.constraint_validator_output
