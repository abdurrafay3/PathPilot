export default function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="w-12 h-12 border-4 border-muted border-t-primary rounded-full animate-spin" />
      <div className="text-center">
        <p className="text-foreground font-medium mb-1">Planning your route...</p>
        <p className="text-sm text-muted-foreground">
          Finding the best waypoints for your journey
        </p>
      </div>
    </div>
  )
}
