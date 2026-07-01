from pydantic import BaseModel, Field
from typing import Literal
from app.schemas.route_request import RouteModifiers
from dataclasses import dataclass


class Coordinates(BaseModel):
    lat: float = Field(description="The latitude of the location.")
    lng: float = Field(description="The longitude of the location.")

class Location(BaseModel):
    location_type: str = Field(description="The type of the location, e.g., restaurant.")
    value: str | None = Field(default=None, description="The address itself, e.g., Central, Hong Kong.")
    confidence : float | None = Field(default=None, description="The confidence score of the location extraction, ranging from 0 to 1.")
    coordinates : Coordinates | None = Field(default=None, description="The coordinates of the location, if available.")

class RequiredStop(BaseModel):
    place_type : str = Field(description="The type of the required stop, e.g., gas station, restaurant.")
    position : str = Field(description="The position of the required stop in the route, e.g., before or after the destination or along the route.")
    constraint_type : str = Field(description="The type of constraint for the required stop, e.g., must visit, optional. Labelled either hard or soft constraint. Hard constraints must be satisfied, while soft constraints can be violated if necessary.")
    max_detour_minutes : int | None = Field(default=None, description="The maximum detour time in minutes for the required stop, if applicable.")
    open_now : bool | None = Field(default=None, description="Indicates whether the required stop should be open now or not, if applicable.")

class CandidateRoute(BaseModel):
    # route id, summary, duration_minutes, distance_metres, walking_minutes, transfers, polyline
    route_id : str = Field(description="The unique identifier for the route candidate.")
    duration_minutes : int = Field(description="The estimated duration of the route candidate in minutes.")
    distance_metres : float | None = Field(default=None, description="The estimated distance of the route candidate in meters.")
    polyline : str | None = Field(default=None, description="The encoded polyline representing the route candidate's path on a map.")

class WayPointCandidate(BaseModel):
    name : str = Field(description="The name of the waypoint candidate.")
    place_type : str = Field(description="The type of the waypoint candidate, e.g., restaurant, gas station.")
    coordinates : Coordinates = Field(description="The coordinates of the waypoint candidate.")
    near_route_id : str | None = Field(default=None, description="The route ID of the route near which the waypoint candidate is located, if applicable.")
    distance_from_route_metres : float | None = Field(default=None, description="The distance in meters from the waypoint candidate to the nearest route, if applicable.")
    rating : float | None = Field(default=None, description="The rating of the waypoint candidate, if applicable.")
    open_now : bool | None = Field(default=None, description="Indicates whether the waypoint candidate is currently open or not, if applicable.")
# ===========================
# INTENT NORMALIZATION SCHEMA
# ===========================

class IntentOutput(BaseModel):
    cleaned_prompt: str = Field(description="The cleaned prompt after processing the user's input.")
    origin : Location = Field(description="The origin location extracted from the user's input.")
    destination : Location = Field(description="The destination location extracted from the user's input.")
    travel_mode : Literal["DRIVE", "WALK", "BICYCLE", "TRANSIT"] | None = Field(default=None, description="The travel mode extracted from the user's input, e.g., driving, walking, etc.")
    required_stops : list[RequiredStop] = Field(default_factory=list, description="A list of required stops extracted from the user's input, if any.")
    max_walking_minutes : int | None = Field(default=None, description="The maximum walking time in minutes extracted from the user's input, if any.")
    optimization_goal : str | None = Field(default=None, description="The optimization goal extracted from the user's input, if any, e.g., minimize time, minimize distance, etc.")
    assumptions : list[str] = Field(default_factory=list, description="A list of assumptions made during the processing of the user's input, if any.")
    status : Literal["ready_for_geocoding", "not_ready_for_geocoding"] = Field(description="The status of the intent extraction process, e.g., success, failure, ready for geocoding etc.")
    routeModifiers : RouteModifiers = Field(default_factory=RouteModifiers, description="The route modifiers extracted from the user's input, if any, e.g., avoid tolls, avoid highways, etc.")

# ===========================
# GEOCODER AGENT
# ===========================
class GeocodedLocation(BaseModel):
    formatted_address: str = Field(description="The formatted address of the geocoded location.")
    coordinates: Coordinates = Field(description="The coordinates of the geocoded location.")
    confidence: float = Field(description="The confidence score of the geocoding result, ranging from 0 to 1.")

class GeocoderAgentOutput(BaseModel):
    origin : GeocodedLocation | None = Field(default=None, description="The geocoded origin location, if available.")
    destination : GeocodedLocation | None = Field(default=None, description="The geocoded destination location, if available.")
# ===========================
# ROUTE CANDIDATE AGENT
# ===========================
class CandidateRouteAgentOutput(BaseModel):
    candidate_routes : list[CandidateRoute] = Field(description="A list of candidate routes generated by the route candidate agent.")

# ===========================
# WAYPOINT FINDER AGENT
# ===========================
class RouteWaypointCandidate(BaseModel):
    route_id: str = Field(description="The unique identifier for the route associated with the waypoint candidate.")
    candidates : list[WayPointCandidate] = Field(description="A list of waypoint candidates associated with the route.")

class WaypointFinderAgentOutput(BaseModel):
    route_waypoints : list[RouteWaypointCandidate] = Field(description="A list of candidate waypoints grouped by routes generated by the waypoint finder agent.")

# ===========================
# DETOUR SCORER AGENT
# ===========================
class DetourScore(BaseModel):
    base_route: CandidateRoute = Field(description="The base route against which the detour score is calculated.")
    waypoint : WayPointCandidate = Field(description="The waypoint for which the detour score is calculated.")
    detour_route: CandidateRoute = Field(description="The detour route that includes the waypoint.")
    detour_minutes : int = Field(description="The additional time in minutes added to the base route due to the detour.")
    score : float = Field(description="The score assigned to the detour, which can be used for ranking or comparison purposes.")

class DetourScorerOutput(BaseModel):
    detour_scores : list[DetourScore] = Field(description="A list of detour scores generated by the detour scorer agent.")

# ===========================
# CONSTRAINT VALIDATOR AGENT
# ===========================

class ConstraintValidatorAgentOutput(BaseModel):
    accepted_routes : list[DetourScore] = Field(description="A list of accepted routes that meet the specified constraints.")
    rejected_routes : list[DetourScore] = Field(description="A list of rejected routes that do not meet the specified constraints.")
    final_route : DetourScore | None = Field(default=None, description="The final selected route after constraint validation, if applicable.")
    status : Literal["valid_route_found", "no_valid_route_found"] = Field(description="The status of the constraint validation process, indicating whether a valid route was selected or not.")


# ===========================
# FINAL ROUTE SELECTOR AGENT
# ===========================

class FinalRouteSelectorAgentOutput(BaseModel):
    selected_route : DetourScore = Field(description="The final selected route after all processing and validation.")
    status : Literal["route_selected", "no_valid_route_found"] = Field(description="The status of the final route selection process, indicating whether a valid route was selected or not.")
    explanations : str = Field(default="", description="An explanation or reason for the final route selection, if any.")

@dataclass
class RoutePlannerContext:
    intent_output: IntentOutput
    geocoder_output: GeocoderAgentOutput
    candidate_route_output: CandidateRouteAgentOutput
