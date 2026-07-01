import httpx
from app.schemas.agent_state import CandidateRouteAgentOutput, RoutePlannerContext, RouteWaypointCandidate, WaypointFinderAgentOutput, RequiredStop, WayPointCandidate, Coordinates
import polyline
import logging
from agents import RunContextWrapper, function_tool
from app.config import settings
from math import radians, cos, sin, asin, sqrt

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
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.userRatingCount,places.types,places.rating,places.currentOpeningHours"
    }

    body = {
        "includedTypes" : [waypoint_type],
        "maxResultCount" : 3,
        "rankPreference" : "DISTANCE",
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
    output = await find_waypoint_candidates(route_candidate_input, required_stops)
    ctx.context.waypoint_finder_output = output
    return output

def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    Args:
        lat1, lng1: Latitude and longitude of the first point in decimal degrees.
        lat2, lng2: Latitude and longitude of the second point in decimal degrees.
    Returns:
        Distance in meters between the two points.
    """
    # Convert decimal degrees to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of Earth in meters
    return c * r

async def find_waypoint_candidates(route_candidate_input: CandidateRouteAgentOutput, required_stops: list[RequiredStop]) -> WaypointFinderAgentOutput:
    """
    This function identifies the unique waypoint candidates that lie on the provided route candidates. For example, if the user wants to go from A to B and wants a hospital on the way, this function will find all the hospitals that are on the route candidates and return them as unique waypoint candidates.
    Returns:
        WaypointFinderAgentOutput: An object containing the list of unique waypoint candidates.
    """

    waypoint_candidates = []
    # first get the decoded polylines for each route candidate
    for route in route_candidate_input.candidate_routes:
        if route.polyline:
            decoded_polyline = polyline.decode(route.polyline)
            seen_waypoints = {}
            sampled_coordinates = decoded_polyline[::10]  # sample every 10th coordinate to reduce the number of points to check for waypoints
            for required_stop in required_stops:
                for route_lat, route_lng in sampled_coordinates:
                    nearest_waypoints = await search_nearest_waypoints((route_lat, route_lng), required_stop.type)
                    logger.info(f"\033[94m Sampled coordinate: ({route_lat}, {route_lng})\033[0m")
                    for waypoint in nearest_waypoints:
                        waypoint_id = waypoint.get("id")
                        name = waypoint.get("displayName", {}).get("text")
                        lat = waypoint.get("location", {}).get("latitude")
                        lng = waypoint.get("location", {}).get("longitude")
                        coordinates = Coordinates(lat=lat, lng=lng)
                        near_route_id = route.route_id
                        distance_from_route_metres = haversine_distance(lat, lng, route_lat, route_lng)
                        rating = waypoint.get("rating")
                        open_now = waypoint.get("currentOpeningHours", {}).get("openNow")
                        waypoint_candidate = WayPointCandidate(
                            name=name,
                            place_type=required_stop.type,
                            coordinates=coordinates,
                            near_route_id=near_route_id,
                            distance_from_route_metres=distance_from_route_metres,
                            rating=rating,
                            open_now=open_now
                        )

                        key = (near_route_id, waypoint_id)
                        if key not in seen_waypoints:
                            seen_waypoints[key] = waypoint_candidate
                        else:
                            if seen_waypoints[key].distance_from_route_metres > distance_from_route_metres:
                                seen_waypoints[key] = waypoint_candidate
                        waypoint_candidates.append(RouteWaypointCandidate(route_id=route.route_id, candidates=list(seen_waypoints.values())))

    return waypoint_candidates








