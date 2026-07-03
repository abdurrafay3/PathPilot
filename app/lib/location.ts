import { LocationCoords } from './api'

const DEFAULT_LOCATION: LocationCoords = {
  lat: 22.3375,
  lng: 114.263,
}

export function getDefaultLocation(): LocationCoords {
  return { ...DEFAULT_LOCATION }
}

export function requestUserLocation(): Promise<LocationCoords> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      console.log('Geolocation not available, using default location')
      resolve(getDefaultLocation())
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
      },
      (error) => {
        console.log('Location permission denied or unavailable, using default location')
        resolve(getDefaultLocation())
      }
    )
  })
}
