export interface Waypoint {
  name: string
  place_type: string
  detour_minutes: number
  score: number
  base_route_duration: number
  base_route_distance: number
  rating: number
  open_now: boolean
}

export interface RouteResponse {
  final_route: {
    waypoint: Waypoint
    route_polyline: string
  }
  accepted_routes: Array<{
    waypoint: Waypoint
    route_polyline: string
  }>
}

export interface LocationCoords {
  lat: number
  lng: number
}

const API_ENDPOINT = 'https://pathpilot-bruu.onrender.com/plan_route'
const API_TIMEOUT = 60000 // 60 seconds

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

    return response.json()
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.')
      }
      throw error
    }
    throw new Error('Failed to connect to the server')
  } finally {
    clearTimeout(timeoutId)
  }
}
