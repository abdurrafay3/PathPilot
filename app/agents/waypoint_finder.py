import httpx

from app.schemas.agent_state import CandidateRouteAgentOutput, RoutePlannerContext, WaypointFinderAgentOutput, RequiredStop
import polyline
import logging
from agents import RunContextWrapper, function_tool
from app.config import settings


logger = logging.getLogger(__name__)

GOOGLE_NEARBY_PLACES_URL="https://places.googleapis.com/v1/places:searchNearby"

async def search_nearest_waypoints(coordinates: tuple, waypoint_type: str) -> list:
    """
    This function searches for the nearest waypoints of a given type (e.g., hospital, gas station) to the provided coordinate.
    Args:
        coordinate (tuple): A tuple containing the latitude and longitude of the point to search from.
        waypoint_type (str): The type of waypoint to search for (e.g., "hospital", "gas_station").
    Returns:
        list: A list of waypoints found near the provided coordinate.
    """

    logger.info(f"\033[92mSearching for nearest waypoints of type '{waypoint_type}' near coordinates: {coordinates}\033[0m")
    # we can just call the Nearby Places api here to find the nearest waypoints of the given type to the provided coordinate
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.userRatingCount,places.types"
    }

    body = {
        "includedTypes" : [waypoint_type],
        "maxResultCount" : 3,
        "locationRestriction" : {
            "circle" : {
                "center" : {
                    "latitude" : coordinates[0],
                    "longitude" : coordinates[1]
                },
                "radius" : 500.0
                }
            }
        }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_NEARBY_PLACES_URL, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        
        
    return data.get("places", [])


@function_tool
async def find_waypoint_candidates_tool(ctx : RunContextWrapper[RoutePlannerContext]) -> WaypointFinderAgentOutput:
    """
    This function identifies the unique waypoint candidates that lie on the provided route candidates. For example, if the user wants to go from A to B and wants a hospital on the way, this function will find all the hospitals that are on the route candidates and return them as unique waypoint candidates.
    Returns:
        CandidateRouteAgentOutput: An object containing the list of unique candidate routes.
    """
    route_candidate_input = ctx.context.candidate_route_output
    required_stops = ctx.context.intent_output.required_stops
    return await find_waypoint_candidates(route_candidate_input, required_stops)
    

async def find_waypoint_candidates(route_candidate_input: CandidateRouteAgentOutput, required_stops: list[RequiredStop]) -> CandidateRouteAgentOutput:
    """
    This function identifies the unique waypoint candidates that lie on the provided route candidates. For example, if the user wants to go from A to B and wants a hospital on the way, this function will find all the hospitals that are on the route candidates and return them as unique waypoint candidates.
    Returns:
        CandidateRouteAgentOutput: An object containing the list of unique candidate routes.
    """
    # first get the decoded polylines for each route candidate
    for route in route_candidate_input.candidate_routes:
        if route.polyline:
            decoded_polyline = polyline.decode(route.polyline)
            sampled_coordinates = decoded_polyline[::10]  # sample every 10th coordinate to reduce the number of points to check for waypoints
            for required_stop in required_stops:
                for lat, lng in sampled_coordinates:
                    nearest_waypoints = await search_nearest_waypoints((lat, lng), required_stop.type)
                    logger.info(f"\033[94m Sampled coordinate: ({lat}, {lng})\033[0m")

