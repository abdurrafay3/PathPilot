import { LocationCoords } from './api'

const DEFAULT_LOCATION: LocationCoords = {
  lat: 22.3375,
  lng: 114.263,
}

export function getDefaultLocation(): LocationCoords {
  return { ...DEFAULT_LOCATION }
}

export function requestUserLocation(): Promise<LocationCoords> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      console.log('[v0] Geolocation not available, using default location')
      resolve(getDefaultLocation())
      return
    }

    // Set a timeout to use default location if geolocation takes too long
    const timeoutId = setTimeout(() => {
      console.log('[v0] Geolocation timeout, using default location')
      resolve(getDefaultLocation())
    }, 5000)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        clearTimeout(timeoutId)
        console.log('[v0] Got user location:', position.coords.latitude, position.coords.longitude)
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
      },
      (error) => {
        clearTimeout(timeoutId)
        console.log('[v0] Location permission denied or error:', error.message)
        resolve(getDefaultLocation())
      }
    )
  })
}
