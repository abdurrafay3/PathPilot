interface ErrorStateProps {
  error: string
}

export default function ErrorState({ error }: ErrorStateProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          <svg
            className="h-6 w-6 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-medium text-red-900">
            Unable to plan route
          </h3>
          <p className="mt-2 text-sm text-red-700">
            {error}
          </p>
          <p className="mt-3 text-xs text-red-600">
            Please try again with a different search query.
          </p>
        </div>
      </div>
    </div>
  )
}
