'use client'

import { type Waypoint } from '@/lib/api'

interface WaypointDetailsProps {
  waypoint: Waypoint
  highlightScore?: boolean
}

export default function WaypointDetails({
  waypoint,
  highlightScore = false,
}: WaypointDetailsProps) {
  const formatDuration = (minutes: number): string => {
    if (minutes < 60) {
      return `${Math.round(minutes)} min`
    }
    const hours = Math.floor(minutes / 60)
    const mins = Math.round(minutes % 60)
    return `${hours}h ${mins}m`
  }

  const formatDistance = (km: number): string => {
    if (km < 1) {
      return `${Math.round(km * 1000)} m`
    }
    return `${km.toFixed(1)} km`
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {waypoint.score !== undefined && (
        <div className={`p-3 rounded-lg ${
          highlightScore ? 'bg-blue-50 border border-blue-200' : 'bg-muted'
        }`}>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Route Score
          </p>
          <p className={`text-2xl font-bold mt-1 ${
            highlightScore ? 'text-blue-700' : 'text-foreground'
          }`}>
            {(waypoint.score ?? 0).toFixed(1)}
          </p>
        </div>
      )}

      {waypoint.detour_minutes !== undefined && (
        <div className="p-3 rounded-lg bg-muted">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Detour
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatDuration(waypoint.detour_minutes ?? 0)}
          </p>
        </div>
      )}

      {waypoint.base_route_duration !== undefined && (
        <div className="p-3 rounded-lg bg-muted">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Base Duration
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatDuration(waypoint.base_route_duration ?? 0)}
          </p>
        </div>
      )}

      {waypoint.base_route_distance !== undefined && (
        <div className="p-3 rounded-lg bg-muted">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Distance
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatDistance(waypoint.base_route_distance ?? 0)}
          </p>
        </div>
      )}
    </div>
  )
}
