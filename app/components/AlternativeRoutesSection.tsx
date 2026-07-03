'use client'

import { type Waypoint } from '@/lib/api'
import AlternativeRouteCard from './AlternativeRouteCard'

interface AlternativeRoutesSectionProps {
  routes: Array<{
    waypoint: Waypoint
    route_polyline: string
  }>
}

export default function AlternativeRoutesSection({
  routes,
}: AlternativeRoutesSectionProps) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-foreground mb-4">
        Alternative Routes
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {routes.map((route, index) => (
          <AlternativeRouteCard
            key={index}
            route={route}
            index={index}
          />
        ))}
      </div>
    </div>
  )
}
