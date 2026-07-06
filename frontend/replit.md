# Path Pilot

A conversational route planning app that turns natural language prompts into interactive map routes. Split-screen layout: interactive dark map on the left, chatbot on the right.

## Run & Operate

- `npm run dev` — start the app (runs from the workspace root via `pnpm -w run dev` in the workflow)
- `npm run build` — build for production
- `npm run db:push` — push DB schema changes

> **Note:** `npm run dev` at the workspace root works because the workflow uses `pnpm -w run dev`, which executes the root `package.json` dev script (`next dev`). You can also run `pnpm -w run dev` directly.

- Required env: `DATABASE_URL` — Postgres connection string (already configured)
- Required env: `PATHPILOT_BACKEND_URL` — Full URL to the Python route planning backend

## Stack

- **Framework**: Next.js 15 (App Router) — handles both frontend and API routes
- **Map**: Leaflet + react-leaflet v5, CARTO Dark Matter tiles (no API key needed)
- **Polyline decoding**: @googlemaps/polyline-codec
- **Database**: PostgreSQL + Drizzle ORM (route history)
- **Data fetching**: @tanstack/react-query
- **Styling**: Tailwind CSS v4
- **Package manager**: pnpm (workspace root package)

## Where things live

```
app/
  layout.tsx           — root layout, providers
  page.tsx             — renders the Home component
  globals.css          — Tailwind v4 import
  api/
    healthz/route.ts        — GET /api/healthz
    route/plan/route.ts     — POST /api/route/plan (proxies to Python backend)
    route/history/route.ts  — GET /api/route/history (from DB)
components/
  Home.tsx             — client component, manages state
  MapPanel.tsx         — Leaflet map (loaded with ssr: false)
  ChatPanel.tsx        — conversation UI
lib/
  types.ts             — TypeScript types for route data
  schema.ts            — Drizzle schema (route_history table)
  db.ts                — Drizzle DB connection
```

## Architecture

- The Next.js API route `/api/route/plan` proxies requests to the external Python backend (`PATHPILOT_BACKEND_URL`)
- Route history is stored in PostgreSQL and displayed as chat history on page load
- The map decodes encoded polylines from the backend using @googlemaps/polyline-codec
- MapPanel is dynamically imported with `{ ssr: false }` since Leaflet needs browser APIs

## Product

- Users type a natural language route prompt (e.g. "stop at a pharmacy on the way from Central to Causeway Bay")
- The backend returns a `ConstraintValidatorAgentOutput` with the final validated route
- The frontend decodes the route polyline and renders it on the dark map
- Waypoints are shown as markers with name, type, rating, and open status popups
- Route history persists across sessions via PostgreSQL

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._
