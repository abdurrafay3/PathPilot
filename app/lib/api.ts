export interface Waypoint {
  name: string
  place_type?: string
  coordinates?: LocationCoords
  detour_minutes?: number
  score?: number
  base_route_duration?: number
  base_route_distance?: number
  rating?: number
  open_now?: boolean
}

export interface RoutePolylines {
  polyline: string
  legs?: Array<{
    polyline: string
    travel_mode?: string
  }>
}

export interface FinalRoute {
  waypoint: Waypoint
  base_route: RoutePolylines
  detour_route: RoutePolylines
}

export interface AcceptedRoute {
  waypoint: Waypoint
  base_route: RoutePolylines
  detour_route: RoutePolylines
}

export interface RouteResponse {
  final_route: FinalRoute | null
  accepted_routes: AcceptedRoute[]
  status?: string
}

export interface LocationCoords {
  lat: number
  lng: number
}

const API_ENDPOINT = process.env.NEXT_PUBLIC_PATHPILOT_BACKEND_URL ?? 'http://127.0.0.1:8000/plan_route'
const API_TIMEOUT = 600000 // 10 minutes

export async function planRoute(
  userInput: string,
  origin: LocationCoords
): Promise<RouteResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)

  try {
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        "ngrok-skip-browser-warning": "true"
      },
      body: JSON.stringify({
        user_input: userInput,
        origin,
      }),
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`)
    }

    const data = await response.json()

    // Handle "no_valid_route_found" status
    if (data.status === 'no_valid_route_found') {
      throw new Error('No valid route found for the given search. Try a different destination or location.')
    }

    // Validate response structure
    if (!data.final_route && (!data.accepted_routes || data.accepted_routes.length === 0)) {
      throw new Error('Unexpected response format from the server.')
    }

    return data
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request took too long (exceeded 10 minutes). The service may still be processing another request. Please try again in a moment.')
      }
      if (error.message.includes('Server error: 5')) {
        throw new Error('The route planning service encountered an error. This may be due to:\n• The location or destination being outside service coverage\n• Server overload (try again shortly)\n• Invalid location format')
      }
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Network error connecting to the route planning service. This may be a CORS issue or the service may be temporarily unavailable. Try again shortly.')
      }
      console.log('[v0] API Error:', error.message)
      throw error
    }
    throw new Error('Failed to connect to the server. Please check your internet connection.')
  } finally {
    clearTimeout(timeoutId)
  }
}
