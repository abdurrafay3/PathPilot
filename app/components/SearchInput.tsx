'use client'

import { useState, FormEvent } from 'react'

interface SearchInputProps {
  onSearch: (query: string) => void
  isLoading: boolean
  originSet: boolean
}

export default function SearchInput({
  onSearch,
  isLoading,
  originSet,
}: SearchInputProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (input.trim() && !isLoading && originSet) {
      onSearch(input)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-col gap-4">
        <label htmlFor="destination" className="text-lg font-semibold text-foreground">
          Where would you like to go?
        </label>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            id="destination"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g., 'Find a good coffee shop between my current location and Times Square'"
            disabled={!originSet || isLoading}
            className="flex-1 px-4 py-4 rounded-lg border-2 border-border bg-white text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || !originSet || isLoading}
            className="px-8 py-4 bg-gradient-to-r from-primary to-accent text-white font-semibold rounded-lg hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all whitespace-nowrap"
          >
            {isLoading ? 'Planning...' : 'Plan Route'}
          </button>
        </div>
        {!originSet && (
          <p className="text-sm text-blue-600 font-medium animate-pulse">
            🔍 Requesting your location...
          </p>
        )}
      </div>
    </form>
  )
}
