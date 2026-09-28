from math import ceil
from agents import function_tool, RunContextWrapper
import httpx
from collections import defaultdict
from itertools import product
from app.schemas.agent_state import CandidateRoute, CandidateRouteAgentOutput, Coordinates, DetourRoute, DetourScorerOutput, GeocoderAgentOutput, IntentOutput, WayPointCandidate, WaypointFinderAgentOutput, RoutePlannerContext, DetourScore
import logging
from app.timing import timed
from app.mock.helper import record_fixture
from app.config import settings, color
from app.mock.helper import MOCK, load_fixture, fake_latency

logger = logging.getLogger(__name__)

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

PENALTY_PER_EXTRA_MINUTE = 5
MAX_CANDIDATES_PER_STOP = 3
MAX_COMBINATIONS_PER_ROUTE = 12


def candidate_priority(candidate: WayPointCandidate) -> tuple:
    distance = candidate.distance_from_route_metres if candidate.distance_from_route_metres is not None else float("inf")
    rating = candidate.rating if candidate.rating is not None else 0.0
    open_bonus = 0 if candidate.open_now is not False else 1
    sample_index = candidate.route_sample_index if candidate.route_sample_index is not None else 10**9
    return (distance, open_bonus, -rating, sample_index, candidate.name or "")


def waypoint_identity(candidate: WayPointCandidate) -> tuple:
    return (
        candidate.name,
        candidate.place_type,
        candidate.coordinates.lat,
        candidate.coordinates.lng,
        candidate.required_stop_index,
        candidate.route_sample_index,
    )


def order_waypoints(waypoints: list[WayPointCandidate]) -> list[WayPointCandidate]:
    return sorted(
        waypoints,
        key=lambda wp: (
            wp.route_sample_index if wp.route_sample_index is not None else 10**9,
            wp.required_stop_index if wp.required_stop_index is not None else 10**9,
            wp.distance_from_route_metres if wp.distance_from_route_metres is not None else float("inf"),
            wp.name or "",
        ),
    )

async def fetch_route(origin : Coordinates, destination : Coordinates, intent_output : IntentOutput) -> CandidateRoute | None:
    """
    Fetches a route from the Google Routes API based on the origin, destination, and travel mode.

    Args:
        origin (Coordinates): The origin coordinates for the route.
        destination (Coordinates): The destination coordinates for the route.
        travel_mode (str): The travel mode for the route, e.g., "DRIVE", "WALK", "BICYCLE", "TRANSIT".      
    """
    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin.lat,
                    "longitude": origin.lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination.lat,
                    "longitude": destination.lng
                }
            }
        },
        "travelMode": intent_output.travel_mode,
        "computeAlternativeRoutes": False,
        "routeModifiers": intent_output.routeModifiers.model_dump()
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            with timed("detour_scorer.fetch_route", "routes_compute", "google") as t:
                response = await client.post(GOOGLE_ROUTES_URL, json=body, headers=headers)
                t["status"] = response.status_code
            if response.status_code >= 400:
                logger.info(f"\033[91mGoogle Routes status: {response.status_code}\033[0m")
                logger.info(f"\033[91mGoogle Routes response: {response.text}\033[0m")
                try: 
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code")
                    error_message = error_data.get("error", {}).get("message")
                    logger.error(f"\033[91mError fetching route: {error_code} - {error_message}\033[0m")
                except Exception as e:
                    logger.error(f"\033[91mError fetching route: {response.status_code} - {response.text}\033[0m")
                return None  # Return None if there's an error in the response
            response.raise_for_status()
            data = response.json()
            record_fixture("routes_fetch", data)
            routes = data.get("routes", [])
            if not routes:
                logger.error(f"No route found in the response: {data}")
                return None  # Return None if no route is found
            route = routes[0]
            duration_seconds = float(route.get("duration", "").replace("s", ""))
            duration_minutes = ceil(duration_seconds / 60)
            distances_meters = route.get("distanceMeters", 0)
            polyline = route.get("polyline", {}).get("encodedPolyline", None)
            result = CandidateRoute(
                route_id=f"route_{origin.lat}_{origin.lng}_to_{destination.lat}_{destination.lng}",
                duration_minutes=duration_minutes,
                distance_metres=distances_meters,
                polyline=polyline
            )
            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching the route: {e.response.status_code} - {e.response.text}")
        return None

    except httpx.RequestError as e:
        logger.error(f"An error occurred while fetching the route: {str(e)}")
        return None


async def fetch_detour_route_transit(origin : Coordinates, destination : Coordinates , waypoints : list[WayPointCandidate], intent_output : IntentOutput, base_route_id : str) -> DetourRoute | None:
    """
    Fetches the detour route based on the base route and waypoint candidates for transit travel mode.

    Args:
        origin (Coordinates): The origin coordinates for the route.
        destination (Coordinates): The destination coordinates for the route.
        waypoint (list[WayPointCandidate]): The list of waypoint candidates for which the detour is being calculated.
        intent_output (IntentOutput): The intent output containing relevant information for route planning.
        base_route_id (str): The unique identifier of the base route.

    Returns:
        DetourRoute | None: The detour route that includes the waypoint, or None if an error occurs.
    """
    # first we get all waypoints in a list which contains their coordinates only
    waypoints_coordinates = [wp.coordinates for wp in waypoints]
    total_duration_minutes = 0
    total_distance_meters = 0
    legs = []
    for coordinates in waypoints_coordinates:
        logger.info(f"\033[94mWaypoint coordinates: {coordinates.lat}, {coordinates.lng}\033[0m")
        route = await fetch_route(origin, coordinates, intent_output)
        if route:
            total_duration_minutes += route.duration_minutes
            total_distance_meters += route.distance_metres
            legs.append(route)
        else:
            logger.error(f"\033[91mFailed to fetch route from origin to waypoint {coordinates.lat}, {coordinates.lng}\033[0m")
            return None  # Return None if any leg could not be fetched
        origin = coordinates  # Update origin to the last waypoint for the next leg
    final_leg = await fetch_route(origin, destination, intent_output)
    if final_leg:
        total_duration_minutes += final_leg.duration_minutes
        total_distance_meters += final_leg.distance_metres
        legs.append(final_leg)
    else:
        logger.error(f"\033[91mFailed to fetch route from last waypoint to destination\033[0m")
        return None  # Return None if the final leg could not be fetched
    return DetourRoute(
        route_id=f"{base_route_id}_via_{'_'.join([f'{wp.coordinates.lat}_{wp.coordinates.lng}' for wp in waypoints])}",
        duration_minutes=total_duration_minutes,
        distance_metres=total_distance_meters,
        polyline=None,  # Polyline is not applicable for transit routes
        legs=legs
    )

async def fetch_detour_route(origin : Coordinates, destination : Coordinates , waypoints : list[WayPointCandidate], intent_output : IntentOutput, base_route_id : str) -> DetourRoute | None:
    """
    Fetches the detour route based on the base route and waypoint candidates.

    Args:
        origin (Coordinates): The origin coordinates for the route.
        destination (Coordinates): The destination coordinates for the route.
        waypoints (list[WayPointCandidate]): The list of waypoint candidates for which the detour is being calculated.
        intent_output (IntentOutput): The intent output containing relevant information for route planning.
        base_route_id (str): The unique identifier of the base route.

    Returns:
        DetourRoute | None: The detour route that includes the waypoint, or None if an error occurs.
    """
    if intent_output.travel_mode == "TRANSIT":
        return await fetch_detour_route_transit(origin, destination, waypoints, intent_output, base_route_id)

    logger.info(f"\033[94mBeginning to fetch detour route for the base route\033[0m")
    intermediates = [
        {
            "location": {
                "latLng": {
                    "latitude": wp.coordinates.lat,
                    "longitude": wp.coordinates.lng
                }
            }
        }
        for wp in waypoints
    ]

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin.lat,
                    "longitude": origin.lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination.lat,
                    "longitude": destination.lng
                }
            }
        },
        "intermediates": intermediates,
        "travelMode": intent_output.travel_mode,
        "computeAlternativeRoutes": False,
        "routeModifiers": intent_output.routeModifiers.model_dump()
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    }

    try:
        if MOCK:
            data = load_fixture("routes_detour")
            await fake_latency(0.33, 0.3774)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                with timed("detour_scorer.fetch_detour_route", "routes_compute", "google") as t:
                    response = await client.post(GOOGLE_ROUTES_URL, json=body, headers=headers)
                    t["status"] = response.status_code
                if response.status_code >= 400:
                    logger.info(f"\033[91mGoogle Routes status: {response.status_code}\033[0m")
                    logger.info(f"\033[91mGoogle Routes response: {response.text}\033[0m")
                    try: 
                        error_data = response.json()
                        error_code = error_data.get("error", {}).get("code")
                        error_message = error_data.get("error", {}).get("message")
                        logger.error(f"\033[91mError fetching detour route: {error_code} - {error_message}\033[0m")
                    except Exception as e:
                        logger.error(f"\033[91mError fetching detour route: {response.status_code} - {response.text}\033[0m")
                    return None  # Return None if there's an error in the response
                response.raise_for_status()
                data = response.json()
        record_fixture("routes_detour", data)
        routes = data.get("routes", [])
        if not routes:
            logger.error(f"No route found in the response: {data}")
            return None  # Return None if no route is found
        route = routes[0]
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching detour route: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"An error occurred while fetching detour route: {str(e)}")
        return None
    duration_seconds = float(route.get("duration", "").replace("s", ""))
    duration_minutes = ceil(duration_seconds / 60)
    distances_meters = route.get("distanceMeters", 0)
    polyline = route.get("polyline", {}).get("encodedPolyline", None)
    waypoints_name = "_".join((wp.name or "waypoint").replace(" ", "_") for wp in waypoints)
    result = DetourRoute(
        route_id=f"{base_route_id}_via_{waypoints_name}",
        duration_minutes=duration_minutes,
        distance_metres=distances_meters,
        polyline=polyline,
        legs=[]
    )
    
    return result

@function_tool
async def score_detours_tool(ctx : RunContextWrapper[RoutePlannerContext]) -> DetourScorerOutput:
    """
    Scores the detours based on the candidate routes and waypoint candidates.

    Args:
        ctx (RunContextWrapper[RoutePlannerContext]): The context containing the candidate route output and waypoint finder output.

    Returns:
        DetourScorerOutput: A list of scored detours generated by the detour scorer agent.
    """
    logger.info(f"{color.BOLD}{color.BRIGHT_BLUE}Running Score Detour Tool{color.RESET}")
    candidate_route_output = ctx.context.candidate_route_output
    waypoint_finder_output = ctx.context.waypoint_finder_output
    if ctx.context.detour_scorer_output is not None:
        logger.info(f"{color.BOLD}{color.BRIGHT_GREEN}Detour Score Tool has already been run. Returning cached output.{color.RESET}")
        return ctx.context.detour_scorer_output
    output = await score_detours(candidate_route_output, waypoint_finder_output, ctx.context.geocoder_output, ctx.context.intent_output)
    ctx.context.detour_scorer_output = output
    return output

async def score_detours(candidate_route_output : CandidateRouteAgentOutput, waypoint_finder_output : WaypointFinderAgentOutput, geocoder_output : GeocoderAgentOutput, intent_output : IntentOutput) -> DetourScorerOutput:
    """
    Scores the detours based on the candidate routes and waypoint candidates.

    Args:
        candidate_route_output (CandidateRouteAgentOutput): The output from the candidate route agent containing candidate routes.
        waypoint_finder_output (WaypointFinderAgentOutput): The output from the waypoint finder agent containing waypoint candidates.
        geocoder_output (GeocoderAgentOutput): The output from the geocoder agent containing geocoded locations.
        intent_output (IntentOutput): The output from the intent agent containing the processed user input.

    Returns:
        DetourScorerOutput: A list of scored detours generated by the detour scorer agent.
    """

    base_routes = {
        route.route_id : route for route in candidate_route_output.candidate_routes
    }
    detour_scores = []
    logger.info(f"\033[92m Scoring waypoints for each candidate route\033[0m")
    # this will allow O(1) lookup of the base route for each detour
    for route in waypoint_finder_output.route_waypoints:
        base_route = base_routes.get(route.route_id)
        if base_route is None:
            logger.warning(f"Base route with ID {route.route_id} not found in candidate routes. Skipping scoring for this route.")
            continue  
        grouped_candidates = defaultdict(list)
        for waypoint_candidate in route.candidates:
            stop_index = waypoint_candidate.required_stop_index if waypoint_candidate.required_stop_index is not None else 0
            grouped_candidates[stop_index].append(waypoint_candidate)

        stop_groups = [
            sorted(candidates, key=candidate_priority)[:MAX_CANDIDATES_PER_STOP]
            for _, candidates in sorted(grouped_candidates.items(), key=lambda item: item[0])
        ]

        if not stop_groups:
            continue

        if len(stop_groups) < len(intent_output.required_stops):
            logger.warning(
                f"Route {route.route_id} does not have candidates for all required stops. Skipping this route."
            )
            continue

        if len(stop_groups) == 1:
            combinations = [(candidate,) for candidate in stop_groups[0]]
        else:
            combinations = list(product(*stop_groups))[:MAX_COMBINATIONS_PER_ROUTE]

        seen_combination_keys = set()
        for combination in combinations:
            ordered_waypoints = order_waypoints(list(combination))
            combination_key = tuple(waypoint_identity(candidate) for candidate in ordered_waypoints)
            if combination_key in seen_combination_keys:
                continue
            seen_combination_keys.add(combination_key)

            detour_route = await fetch_detour_route(
                origin=geocoder_output.origin.coordinates,
                destination=geocoder_output.destination.coordinates,
                waypoints=ordered_waypoints,
                intent_output=intent_output,
                base_route_id=base_route.route_id
            )
            if detour_route is None:
                logger.warning(f"Detour route could not be fetched for waypoint combination {[wp.name for wp in ordered_waypoints]} on base route {base_route.route_id}. Skipping this detour.")
                continue  # Skip this detour if the route could not be fetched
            detour_minutes = max(0, detour_route.duration_minutes - base_route.duration_minutes)
            score = max(0, 100 - PENALTY_PER_EXTRA_MINUTE * detour_minutes)
            logger.info(f"\033[92mDetour for waypoint combination {[wp.name for wp in ordered_waypoints]} on base route {base_route.route_id} has a score of {score}\033[0m")
            detour_score = DetourScore(
                base_route=base_route,
                waypoint=ordered_waypoints[0],
                waypoints=ordered_waypoints,
                detour_route=detour_route,
                detour_minutes=detour_minutes,
                score=score
            )
            detour_scores.append(detour_score)
    return DetourScorerOutput(detour_scores=detour_scores)




            

