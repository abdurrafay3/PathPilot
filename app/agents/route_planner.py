from agents import Agent, Runner
from app.agents.geocoder import get_region_context, get_coordinates_from_address, produce_origin_destination_tool
from app.agents.route_candidate import fetch_candidate_routes_tool
from app.agents.waypoint_finder import find_waypoint_candidates_tool
from app.schemas.agent_state import IntentOutput, RoutePlannerContext
from app.schemas.route_planner import RoutePlannerOutput
import logging

logger = logging.getLogger(__name__)

system_prompt = """
You are a route planning agent.

You must follow this exact tool order:

1. Call produce_origin_destination_tool.
2. Call fetch_candidate_routes_tool.
3. Call find_waypoint_candidates_tool if the user requested required stops.
4. Return RoutePlannerOutput.

Do not call the same tool twice unless the previous call failed.
Do not ask for more information unless origin or destination is missing.
After candidate routes and waypoint candidates are available, produce the final output.
"""

async def plan_route(ctx: RoutePlannerContext) -> RoutePlannerOutput:
    """
    Plans a route from the origin to the destination, considering any required stops, travel mode, and optimization goals.

    Returns:
        RoutePlannerOutput: A structured representation of the planned route.
    """
    logger.info(f"\033[92mPlanning route for user input\033[0m")

    user_prompt = f"User prompt: {ctx.intent_output.cleaned_prompt}\n\nPlease plan the route using the provided tools and return the output in the specified schema."
    tools = [produce_origin_destination_tool, fetch_candidate_routes_tool, find_waypoint_candidates_tool]
    route_planner = Agent(name="route_planner", instructions=system_prompt, model="gpt-4o-mini", output_type=RoutePlannerOutput, tools=tools)
    route_planner_runner = await Runner.run(starting_agent=route_planner, input=user_prompt, context=ctx)
    result = route_planner_runner.final_output
    return result