from app.schemas.agent_state import (
    CandidateRouteAgentOutput,
    ConstraintValidatorAgentOutput,
    DetourRoute,
    DetourScore,
    DetourScorerOutput,
    RoutePlannerContext,
)
from agents import RunContextWrapper, function_tool
import logging
from app.config import color

logger = logging.getLogger(__name__)

DETOUR_TIME_LIMIT_MINUTES = 30  # Example constraint: maximum allowed detour time in minutes

@function_tool
async def validate_constraints_tool(ctx : RunContextWrapper[RoutePlannerContext]):
    if ctx.context.constraint_validator_output is not None:
        logger.info(f"{color.RED}{color.BOLD}Constraint validation already performed. Skipping.{color.RESET}")
        return ctx.context.constraint_validator_output
    response = await validate_constraints(ctx.context.detour_scorer_output, ctx.context.candidate_route_output)
    ctx.context.constraint_validator_output = response
    return response

async def validate_constraints(
    detour_routes: DetourScorerOutput | None,
    candidate_routes: CandidateRouteAgentOutput | None = None,
) -> ConstraintValidatorAgentOutput:
    """
    Validates the detour routes against specified constraints and returns the accepted and rejected routes.
    Arguments:
        detour_routes (DetourScorerOutput): The output from the detour scorer agent containing detour scores, if any required stops were requested.
        candidate_routes (CandidateRouteAgentOutput): The base candidate routes, used as a fallback when there were no required stops to score detours for.
    Returns:
        ConstraintValidatorAgentOutput: The output containing accepted and rejected routes along with the final selected route and status.
    """

    logger.info(f"{color.BRIGHT_MAGENTA}{color.BOLD}Running Constraint Validation tool...{color.RESET}")
    accepted_routes = []

    detour_scores = detour_routes.detour_scores if detour_routes else []

    for detour_score in detour_scores:
        valid = True
        waypoints = detour_score.waypoints or ([detour_score.waypoint] if detour_score.waypoint else [])
        if not waypoints:
            valid = False
        if detour_score.detour_minutes > DETOUR_TIME_LIMIT_MINUTES:
            valid = False
        if detour_score.score < 20:
            valid = False
        for waypoint in waypoints:
            if waypoint.open_now is False:
                valid = False
        if valid:
            accepted_routes.append(detour_score)
    accepted_routes.sort(key=lambda x: x.score, reverse=True)
    final_route = accepted_routes[0] if accepted_routes else None

    # No required stops means score_detours_tool never ran, so detour_scores is
    # always empty here. Fall back to the fastest base candidate route instead
    # of reporting no_valid_route_found for a route that never needed a detour.
    if final_route is None and not detour_scores and candidate_routes and candidate_routes.candidate_routes:
        base_route = min(candidate_routes.candidate_routes, key=lambda r: r.duration_minutes)
        final_route = DetourScore(
            base_route=base_route,
            waypoint=None,
            waypoints=[],
            detour_route=DetourRoute(
                route_id=base_route.route_id,
                duration_minutes=base_route.duration_minutes,
                distance_metres=base_route.distance_metres,
                polyline=base_route.polyline,
            ),
            detour_minutes=0,
            score=100.0,
        )
        accepted_routes = [final_route]

    status = "valid_route_found" if final_route else "no_valid_route_found"
    return ConstraintValidatorAgentOutput(
        accepted_routes=accepted_routes,
        final_route=final_route,
        status=status
    )


