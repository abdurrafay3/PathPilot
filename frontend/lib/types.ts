export interface Coordinates {
  lat: number;
  lng: number;
}

export interface WayPointCandidate {
  name: string;
  place_type: string;
  coordinates: Coordinates;
  near_route_id?: string | null;
  distance_from_route_metres?: number | null;
  rating?: number | null;
  open_now?: boolean | null;
}

export interface CandidateRoute {
  route_id: string;
  duration_minutes: number;
  distance_metres?: number | null;
  polyline?: string | null;
}

export interface DetourRoute {
  route_id: string;
  duration_minutes: number;
  distance_metres?: number | null;
  polyline?: string | null;
  legs: CandidateRoute[];
}

export interface DetourScore {
  base_route: CandidateRoute;
  waypoint: WayPointCandidate;
  waypoints?: WayPointCandidate[];
  detour_route: DetourRoute;
  detour_minutes: number;
  score: number;
}

export interface ConstraintValidatorAgentOutput {
  accepted_routes: DetourScore[];
  final_route: DetourScore | null;
  status: "valid_route_found" | "no_valid_route_found";
}

export interface RouteHistoryItem {
  id: number;
  prompt: string;
  status: string;
  duration_minutes: number | null;
  waypoint_name: string | null;
  created_at: string;
}
