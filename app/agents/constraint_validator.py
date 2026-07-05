from app.schemas.agent_state import ConstraintValidatorAgentOutput, DetourScorerOutput, RoutePlannerContext
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
    response = await validate_constraints(ctx.context.detour_scorer_output)
    ctx.context.constraint_validator_output = response
    return response

async def validate_constraints(detour_routes : DetourScorerOutput) -> ConstraintValidatorAgentOutput:
    """
    Validates the detour routes against specified constraints and returns the accepted and rejected routes.
    Arguments:
        detour_routes (DetourScorerOutput): The output from the detour scorer agent containing detour scores.
    Returns:    
        ConstraintValidatorAgentOutput: The output containing accepted and rejected routes along with the final selected route and status.
    """

    logger.info(f"{color.BRIGHT_MAGENTA}{color.BOLD}Running Constraint Validation tool...{color.RESET}")
    accepted_routes = []

    for detour_score in detour_routes.detour_scores:
        valid = True
        if detour_score.waypoint is None:
            valid = False
        if detour_score.detour_minutes > DETOUR_TIME_LIMIT_MINUTES:
            valid = False
        if detour_score.score < 20:
            valid = False
        if detour_score.waypoint.open_now is False:
            valid = False
        if valid:
            accepted_routes.append(detour_score)
    accepted_routes.sort(key=lambda x: x.score, reverse=True)
    final_route = accepted_routes[0] if accepted_routes else None
    status = "valid_route_found" if final_route else "no_valid_route_found"
    logger.info(f"{color.BRIGHT_MAGENTA}{color.BOLD}Constraint Validation completed. Status: {status}{color.RESET}")
    return ConstraintValidatorAgentOutput(
        accepted_routes=accepted_routes,
        final_route=final_route,
        status=status
    )


