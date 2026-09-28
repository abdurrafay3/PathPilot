from agents import Agent, Runner
from app.agents.geocoder import produce_origin_destination_tool, produce_origin_destination
from app.agents.route_candidate import fetch_candidate_routes_tool, fetch_candidate_routes
from app.agents.waypoint_finder import find_waypoint_candidates_tool, find_waypoint_candidates
from app.schemas.agent_state import  ConstraintValidatorAgentOutput, RoutePlannerContext
from app.schemas.route_planner import RoutePlannerOutput
from app.agents.detour_scorer import score_detours_tool, score_detours
from app.agents.constraint_validator import validate_constraints_tool, validate_constraints
import logging
from app.timing import timed
from app.mock.helper import MOCK, fake_latency, load_fixture


logger = logging.getLogger(__name__)

system_prompt = """
You are a route planning agent.

You must follow this exact tool order:

1. Call produce_origin_destination_tool.
2. Call fetch_candidate_routes_tool.
3. Call find_waypoint_candidates_tool if the user requested required stops.
4. Call score_detours_tool to evaluate potential detours.
5. Call validate_constraints_tool to ensure the selected route meets all constraints.


Do not call the same tool twice unless the previous call failed.
Do not ask for more information unless origin or destination is missing.
After candidate routes and waypoint candidates are available, produce the final output.
"""

async def plan_route(ctx: RoutePlannerContext) -> ConstraintValidatorAgentOutput:
    """
    Plans a route from the origin to the destination, considering any required stops, travel mode, and optimization goals.

    Returns:
        RoutePlannerOutput: A structured representation of the planned route.
    """
    logger.info(f"\033[92mPlanning route for user input\033[0m")

    user_prompt = f"""User prompt: {ctx.intent_output.cleaned_prompt}\n\nPlease plan the route using the provided tools and return the output in the specified schema.
    Call tools in this exact order:
    1. produce_origin_destination_tool exactly once
    2. fetch_candidate_routes_tool exactly once
    3. find_waypoint_candidates_tool exactly once if required stops exist
    4. score_detours_tool exactly once if waypoint candidates exist
    5. After score_detours_tool returns, call validate_constraints_tool exactly once to ensure the selected route meets all constraints.

    Never call fetch_candidate_routes_tool again after waypoint candidates or detour scores exist.
    Never call find_waypoint_candidates_tool again after detour scores exist.
    Never call the same tool more than once.
    
    """
    if MOCK:
        with timed("route_planner.plan_route", "agent_run_incl_tools", "openai"):
            await fake_latency(10, 20)   # the planner's own LLM turns
            ctx.geocoder_output = await produce_origin_destination(ctx.intent_output)
            ctx.candidate_route_output = await fetch_candidate_routes(ctx.geocoder_output, ctx.intent_output)
            if ctx.intent_output.required_stops:
                ctx.waypoint_finder_output = await find_waypoint_candidates(
                    ctx.candidate_route_output, ctx.intent_output.required_stops, ctx.intent_output
                )
                ctx.detour_scorer_output = await score_detours(
                    ctx.candidate_route_output, ctx.waypoint_finder_output, ctx.geocoder_output, ctx.intent_output
                )
            ctx.constraint_validator_output = await validate_constraints(
                ctx.detour_scorer_output, ctx.candidate_route_output
            )
        return ctx.constraint_validator_output

    tools = [produce_origin_destination_tool, fetch_candidate_routes_tool, find_waypoint_candidates_tool, score_detours_tool, validate_constraints_tool]
    route_planner = Agent(name="route_planner", instructions=system_prompt, model="gpt-4o-mini", output_type=RoutePlannerOutput, tools=tools)
    with timed("route_planner.plan_route", "agent_run_incl_tools", "openai"):
        route_planner_runner = await Runner.run(starting_agent=route_planner, input=user_prompt, context=ctx)
    result = route_planner_runner.final_output
    return result