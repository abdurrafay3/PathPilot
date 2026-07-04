import polyline from '@mapbox/polyline'

export interface LatLng {
  lat: number
  lng: number
}

export function decodePolyline(encoded: string): LatLng[] {
  try {
    const coords = polyline.decode(encoded)
    return coords.map(([lat, lng]) => ({ lat, lng }))
  } catch (error) {
    console.log('[v0] Error decoding polyline:', error)
    return []
  }
}

export function decodeMultiplePolylines(polylines: string[]): LatLng[][] {
  return polylines
    .map(p => decodePolyline(p))
    .filter(coords => coords.length > 0)
}
