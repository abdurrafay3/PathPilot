'use client'

import { type RouteResponse, type LocationCoords } from '@/lib/api'
import FinalRouteCard from './FinalRouteCard'
import AlternativeRoutesSection from './AlternativeRoutesSection'
import RouteMap from './RouteMap'

interface RouteResultsProps {
  result: RouteResponse
  origin: LocationCoords | null
}

export default function RouteResults({ result, origin }: RouteResultsProps) {
  return (
    <div className="space-y-8">
      {/* Map */}
      <RouteMap 
        finalRoute={result.final_route} 
        alternativeRoutes={result.accepted_routes?.slice(0, 3)}
      />

      {/* Final Route Section */}
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-4">
          Recommended Route
        </h2>
        <FinalRouteCard route={result.final_route} />
      </div>

      {/* Alternative Routes Section */}
      {result.accepted_routes && result.accepted_routes.length > 0 && (
        <AlternativeRoutesSection routes={result.accepted_routes.slice(0, 3)} />
      )}
    </div>
  )
}
