'use client'

import { type Waypoint } from '@/lib/api'
import WaypointDetails from './WaypointDetails'

interface AlternativeRouteCardProps {
  route: {
    waypoint: Waypoint
    route_polyline: string
  }
  index: number
}

export default function AlternativeRouteCard({
  route,
  index,
}: AlternativeRouteCardProps) {
  const { waypoint } = route

  return (
    <div className="bg-white border border-border rounded-lg overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-muted to-white p-4 border-b border-border">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Option {index + 1}
            </p>
            <h3 className="text-lg font-bold text-foreground mt-1 line-clamp-2">
              {waypoint.name}
            </h3>
            <p className="text-xs text-muted-foreground capitalize mt-1">
              {waypoint.place_type}
            </p>
          </div>
          {waypoint.rating > 0 && (
            <div className="flex items-center gap-1 bg-yellow-50 px-2 py-1 rounded-full flex-shrink-0">
              <span className="text-sm">⭐</span>
              <span className="text-xs font-semibold text-yellow-900">
                {waypoint.rating.toFixed(1)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col">
        <div className="mb-4">
          <WaypointDetails waypoint={waypoint} highlightScore={true} />
        </div>

        {/* Status */}
        <div className="mt-auto pt-4 border-t border-border flex items-center gap-2">
          {waypoint.open_now ? (
            <>
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-xs font-medium text-green-700">
                Open now
              </span>
            </>
          ) : (
            <>
              <div className="w-2 h-2 bg-gray-400 rounded-full" />
              <span className="text-xs font-medium text-gray-700">
                Closed
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
