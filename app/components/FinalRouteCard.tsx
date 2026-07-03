'use client'

import { type Waypoint } from '@/lib/api'
import WaypointDetails from './WaypointDetails'

interface FinalRouteCardProps {
  route: {
    waypoint: Waypoint
    route_polyline: string
  }
}

export default function FinalRouteCard({ route }: FinalRouteCardProps) {
  const { waypoint, route_polyline } = route

  return (
    <div className="rounded-xl shadow-lg overflow-hidden border border-border bg-white hover:shadow-xl transition-shadow">
      {/* Header with gradient */}
      <div className="bg-gradient-to-r from-primary via-accent to-secondary p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-3xl font-bold text-white mb-2">
              {waypoint.name}
            </h3>
            <p className="text-blue-100 capitalize font-medium">
              {waypoint.place_type}
            </p>
          </div>
          {waypoint.rating > 0 && (
            <div className="flex items-center gap-2 bg-white bg-opacity-20 backdrop-blur-sm px-3 py-2 rounded-lg flex-shrink-0">
              <span className="text-2xl">⭐</span>
              <span className="font-bold text-white text-lg">
                {waypoint.rating.toFixed(1)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="p-8">
        <WaypointDetails waypoint={waypoint} />

        {/* Status Badge */}
        <div className="mt-8 pt-8 border-t border-border flex items-center gap-3">
          {waypoint.open_now ? (
            <>
              <div className="w-3 h-3 bg-emerald-500 rounded-full" />
              <span className="text-sm font-semibold text-emerald-700">
                Open now
              </span>
            </>
          ) : (
            <>
              <div className="w-3 h-3 bg-slate-400 rounded-full" />
              <span className="text-sm font-semibold text-slate-600">
                Currently closed
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
