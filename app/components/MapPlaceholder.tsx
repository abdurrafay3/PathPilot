export default function MapPlaceholder() {
  return (
    <div className="bg-muted rounded-lg p-8 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full mb-4">
        <svg
          className="w-8 h-8 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 20l-5.447-2.724A1 1 0 003 16.382V5.618a1 1 0 011.553-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 16.382V5.618a1 1 0 00-1.553-.894L15 7m0 13V7m0 0L9 4"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        Interactive Map
      </h3>
      <p className="text-muted-foreground max-w-sm mx-auto">
        Map visualization will display the route polyline and waypoints here. Ready for integration with mapping libraries like Google Maps or Leaflet.
      </p>
    </div>
  )
}
