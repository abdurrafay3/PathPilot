'use client'

import { useEffect, useRef, useState } from 'react'
import { decodePolyline, type LatLng } from '@/lib/polyline'
import { type FinalRoute, type AcceptedRoute } from '@/lib/api'

interface RouteMapProps {
  finalRoute: FinalRoute | null
  alternativeRoutes?: AcceptedRoute[]
}

export default function RouteMap({ finalRoute, alternativeRoutes = [] }: RouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!mapRef.current || !finalRoute) return

    const initializeMap = async () => {
      try {
        const L = await import('leaflet')
        
        // Initialize map
        if (mapInstanceRef.current) {
          mapInstanceRef.current.remove()
        }

        const map = L.map(mapRef.current).setView([22.3375, 114.263], 12)
        mapInstanceRef.current = map

        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors',
          maxZoom: 19,
        }).addTo(map)

        const allCoords: LatLng[] = []
        const bounds = L.latLngBounds([])

        // Decode and draw base route (bright blue) - origin to destination
        if (finalRoute.base_route?.polyline) {
          const baseCoords = decodePolyline(finalRoute.base_route.polyline)
          if (baseCoords.length > 0) {
            allCoords.push(...baseCoords)
            L.polyline(
              baseCoords.map(c => [c.lat, c.lng]),
              { color: '#0EA5E9', weight: 6, opacity: 0.9, lineCap: 'round', lineJoin: 'round' }
            ).addTo(map)
            baseCoords.forEach(c => bounds.extend([c.lat, c.lng]))
          }
        }

        // Decode and draw detour route (bright orange) - to the waypoint
        if (finalRoute.detour_route) {
          const detourCoords: LatLng[] = []
          
          if (finalRoute.detour_route.legs && Array.isArray(finalRoute.detour_route.legs)) {
            // Multiple legs
            finalRoute.detour_route.legs.forEach(leg => {
              if (leg.polyline) {
                const legCoords = decodePolyline(leg.polyline)
                detourCoords.push(...legCoords)
              }
            })
          } else if (finalRoute.detour_route.polyline) {
            // Single polyline (for non-transit routes)
            const coords = decodePolyline(finalRoute.detour_route.polyline)
            detourCoords.push(...coords)
          }

          if (detourCoords.length > 0) {
            allCoords.push(...detourCoords)
            L.polyline(
              detourCoords.map(c => [c.lat, c.lng]),
              { color: '#F59E0B', weight: 6, opacity: 0.9, lineCap: 'round', lineJoin: 'round' }
            ).addTo(map)
            detourCoords.forEach(c => bounds.extend([c.lat, c.lng]))
          }
        }

        // Add marker for waypoint
        if (finalRoute.waypoint) {
          // Try to find waypoint location from the detour route end
          const detourCoords: LatLng[] = []
          if (finalRoute.detour_route?.legs && Array.isArray(finalRoute.detour_route.legs)) {
            finalRoute.detour_route.legs.forEach(leg => {
              if (leg.polyline) {
                detourCoords.push(...decodePolyline(leg.polyline))
              }
            })
          } else if (finalRoute.detour_route?.polyline) {
            detourCoords.push(...decodePolyline(finalRoute.detour_route.polyline))
          }

          if (detourCoords.length > 0) {
            const lastCoord = detourCoords[detourCoords.length - 1]
            L.circleMarker([lastCoord.lat, lastCoord.lng], {
              radius: 8,
              fillColor: '#EF4444',
              color: '#991B1B',
              weight: 2,
              opacity: 1,
              fillOpacity: 0.8,
            })
              .bindPopup(finalRoute.waypoint.name)
              .addTo(map)
            bounds.extend([lastCoord.lat, lastCoord.lng])
          }
        }

        // Draw alternative routes lightly
        alternativeRoutes.slice(0, 3).forEach((route, idx) => {
          if (route.detour_route) {
            const altCoords: LatLng[] = []
            
            if (route.detour_route.legs && Array.isArray(route.detour_route.legs)) {
              route.detour_route.legs.forEach(leg => {
                if (leg.polyline) {
                  altCoords.push(...decodePolyline(leg.polyline))
                }
              })
            } else if (route.detour_route.polyline) {
              altCoords.push(...decodePolyline(route.detour_route.polyline))
            }

            if (altCoords.length > 0) {
              const colors = ['#10B981', '#8B5CF6', '#EF4444']
              L.polyline(
                altCoords.map(c => [c.lat, c.lng]),
                { color: colors[idx] || '#CCCCCC', weight: 5, opacity: 0.65, lineCap: 'round', lineJoin: 'round' }
              ).addTo(map)
              altCoords.forEach(c => bounds.extend([c.lat, c.lng]))
            }
          }
        })

        // Fit bounds
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [50, 50] })
        }
      } catch (err) {
        console.log('[v0] Error rendering map:', err)
        setError('Map could not be rendered. Route information is still available below.')
      }
    }

    initializeMap()

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
      }
    }
  }, [finalRoute, alternativeRoutes])

  if (!finalRoute) return null

  return (
    <div>
      {error ? (
        <div className="w-full bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6 rounded">
          <p className="text-sm text-yellow-700">{error}</p>
        </div>
      ) : (
        <div
          ref={mapRef}
          className="w-full h-96 rounded-lg border border-border shadow-md mb-6"
        />
      )}
    </div>
  )
}
