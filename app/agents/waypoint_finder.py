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
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(GOOGLE_NEARBY_PLACES_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data.get("places", [])
    except httpx.RequestError as e:
        logger.error(f"\033[91mAn error occurred while requesting the Google Nearby Places API: {e}, Error: {e.response.text}\033[0m")
        return []   
    except httpx.HTTPStatusError as e:
        logger.error(f"\033[91mNon-successful status code received from Google Nearby Places API: {e.response.status_code}, Error: {e.response.text}\033[0m")
        return []   


@function_tool
async def find_waypoint_candidates_tool(ctx : RunContextWrapper[RoutePlannerContext]) -> WaypointFinderAgentOutput:
    """
    This function identifies the unique waypoint candidates that lie on the provided route candidates. For example, if the user wants to go from A to B and wants a hospital on the way, this function will find all the hospitals that are on the route candidates and return them as unique waypoint candidates.
    Returns:
        CandidateRouteAgentOutput: An object containing the list of unique candidate routes.
    """
    logger.info(f"\033[94mFinding waypoint candidates based on route candidates and required stops\033[0m")
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
    logger.info(f"\033[94mCalculating Haversine distance between points\033[0m")

    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of Earth in meters
    return c * r

def get_sampled_coordinates(decoded_polyline, max_samples=5):
    """
    Samples coordinates from a decoded polyline to reduce the number of points for waypoint searching.
    Args:
        decoded_polyline (list): A list of (latitude, longitude) tuples representing the decoded polyline.
        max_samples (int): The maximum number of samples to take from the decoded polyline.
    Returns:
        list: A list of sampled (latitude, longitude) tuples.
    """
    logger.info(f"\033[94mSampling coordinates from decoded polyline\033[0m")
    step = max(1, len(decoded_polyline) // max_samples)
    sampled_coordinates = decoded_polyline[::step][:max_samples]
    # we will also round the coordinates to 3 decimal places to reduce the number of unique coordinates and avoid duplicates
    rounded_sampled_coordinates = [(round(lat, 3), round(lng, 3)) for lat, lng in sampled_coordinates]
    # now we remove duplicates from the rounded sampled coordinates
    seen_sampled_coordinates = set()
    unique_sampled_coordinates = []
    for lat, lng in rounded_sampled_coordinates:
        if (lat, lng) not in seen_sampled_coordinates:
            seen_sampled_coordinates.add((lat, lng))
            unique_sampled_coordinates.append((lat, lng))
    return unique_sampled_coordinates



async def find_waypoint_candidates(route_candidate_input: CandidateRouteAgentOutput, required_stops: list[RequiredStop]) -> WaypointFinderAgentOutput:
    """
    This function identifies the unique waypoint candidates that lie on the provided route candidates. For example, if the user wants to go from A to B and wants a hospital on the way, this function will find all the hospitals that are on the route candidates and return them as unique waypoint candidates.
    Returns:
        WaypointFinderAgentOutput: An object containing the list of unique waypoint candidates.
    """

    waypoint_candidates =WaypointFinderAgentOutput(route_waypoints=[])
    # first get the decoded polylines for each route candidate
    for route in route_candidate_input.candidate_routes:
        if route.polyline:
            logger.info(f"\033[95mProcessing route {route.route_id}\033[0m")
            decoded_polyline = polyline.decode(route.polyline)
            seen_waypoints = {}
            sampled_coordinates = get_sampled_coordinates(decoded_polyline)
            for required_stop in required_stops:
                for route_lat, route_lng in sampled_coordinates:
                    nearest_waypoints = await search_nearest_waypoints((route_lat, route_lng), required_stop.place_type)
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
                            place_type=required_stop.place_type,
                            coordinates=coordinates,
                            near_route_id=near_route_id,
                            distance_from_route_metres=distance_from_route_metres,
                            rating=rating,
                            open_now=open_now
                        )

                        key = (near_route_id, waypoint_id)
                        if key not in seen_waypoints:
                            seen_waypoints[key] = waypoint_candidate
                            logger.info(f"\033[95mWaypoint candidate found. Name : {waypoint_candidate.name}\033[0m")
                        else:
                            if seen_waypoints[key].distance_from_route_metres > distance_from_route_metres:
                                seen_waypoints[key] = waypoint_candidate
        waypoint_candidates.route_waypoints.append(RouteWaypointCandidate(route_id=route.route_id, candidates=list(seen_waypoints.values())))
        logger.info(f"\033[92mRoute {route.route_id} has {len(seen_waypoints)} unique waypoint candidates\033[0m")

    logger.info(f"Printing the final waypoint candidates for all routes:\n\n {waypoint_candidates.model_dump_json(indent=2)}")
    return waypoint_candidates








