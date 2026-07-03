'use client'

import { useState, useEffect } from 'react'
import { planRoute, type RouteResponse, type LocationCoords } from '@/lib/api'
import { requestUserLocation } from '@/lib/location'
import SearchInput from './SearchInput'
import RouteResults from './RouteResults'
import LoadingState from './LoadingState'
import ErrorState from './ErrorState'

export default function RoutePlanner() {
  const [origin, setOrigin] = useState<LocationCoords | null>(null)
  const [result, setResult] = useState<RouteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Request location on mount
  useEffect(() => {
    const initLocation = async () => {
      try {
        const coords = await requestUserLocation()
        setOrigin(coords)
      } catch (err) {
        console.error('Failed to get location:', err)
      }
    }
    initLocation()
  }, [])

  const handleSearch = async (query: string) => {
    if (!origin) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await planRoute(query, origin)
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to plan route')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary via-accent to-secondary sticky top-0 z-10 shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <h1 className="text-4xl font-bold text-white">
            PathPilot
          </h1>
          <p className="text-blue-100 mt-2 text-lg">
            Smart route planning with AI-powered waypoint suggestions
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col w-full">
        {/* Search Section */}
        <section className="bg-white border-b border-border shadow-sm">
          <div className="max-w-4xl mx-auto w-full px-4 py-8">
            <SearchInput 
              onSearch={handleSearch} 
              isLoading={loading}
              originSet={origin !== null}
            />
          </div>
        </section>

        {/* Results Section */}
        <section className="flex-1 w-full py-8 px-4">
          <div className="max-w-4xl mx-auto w-full">
            {loading && <LoadingState />}
            {error && <ErrorState error={error} />}
            {result && <RouteResults result={result} origin={origin} />}
            {!loading && !error && !result && (
              <div className="text-center py-16">
                <p className="text-muted-foreground text-lg">
                  Enter a destination to get started
                </p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
