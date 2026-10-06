# PathPilot

PathPilot is a conversational route-planning app. Describe a trip in natural
language, and PathPilot turns it into an interactive map route with optional
stops and detours.

The app is designed around a simple question:

> “Can you find me a coffee shop on the way from Central to Causeway Bay?”

PathPilot interprets the request, geocodes the locations, finds candidate
routes and nearby places, scores detours, validates the result, and displays
the final route on a dark Leaflet map.

## Features

- Natural-language route requests
- Browser geolocation with a Hong Kong University of Science and Technology
  fallback location
- Interactive Leaflet map with route and waypoint markers
- Google Geocoding, Places, and Routes integrations
- Multi-step Python agent pipeline for intent normalization and route planning
- Route history stored in PostgreSQL
- FastAPI backend and Next.js frontend
- Mock external-service mode for local development and load testing

## Architecture

```text
Browser
  │
  ▼
Next.js frontend
  ├── Interactive map and chat UI
  ├── /api/route/plan       ─────┐
  ├── /api/route/history          │
  └── /api/healthz                │
                                  ▼
                         FastAPI route planner
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
              OpenAI         Google Maps       PostgreSQL
             agents        Geocoding/Places/   route history
                              Routes APIs
```

The Next.js route at `/api/route/plan` forwards requests to the Python
backend. The frontend defaults to `http://127.0.0.1:8000/plan_route`, but this
can be changed with `PATHPILOT_BACKEND_URL`.

The Python pipeline is organized into focused agents:

1. Intent normalization
2. Geocoding
3. Candidate route generation
4. Waypoint discovery
5. Detour scoring
6. Constraint validation
7. Final route selection

## Requirements

- Python 3.13+
- Node.js 20+
- pnpm
- PostgreSQL (required for route history)
- An OpenAI API key
- A Google Maps Platform API key with access to:
  - Geocoding API
  - Places API
  - Routes API

## Local development

### 1. Clone the repository

```bash
git clone https://github.com/abdurrafay3/PathPilot.git
cd PathPilot
```

### 2. Configure the backend

Install the Python dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Create a `.env` file in the repository root:

```dotenv
OPENAI_API_KEY=your-openai-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

Never commit `.env` or real API keys. The repository ignores `.env` by
default.

Start the FastAPI backend:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The backend is available at <http://127.0.0.1:8000>. FastAPI's interactive
documentation is available at <http://127.0.0.1:8000/docs>.

### 3. Configure the frontend

In a second terminal:

```bash
cd frontend
pnpm install
```

Set the frontend environment variables. `DATABASE_URL` is required for route
history, and `PATHPILOT_BACKEND_URL` points the Next.js API proxy at the
backend started above:

```dotenv
DATABASE_URL=postgres://user:password@localhost:5432/pathpilot
PATHPILOT_BACKEND_URL=http://127.0.0.1:8000/plan_route
```

Push the Drizzle schema to PostgreSQL:

```bash
pnpm db:push
```

Start the frontend:

```bash
pnpm dev
```

Open <http://localhost:3000>.

## Mock mode

If you want to run the backend without making OpenAI or Google API requests,
set `MOCK_EXTERNAL=1`. The repository includes recorded fixtures for the
external calls used by the route-planning pipeline.

```bash
MOCK_EXTERNAL=1 \
OPENAI_API_KEY=fake \
GOOGLE_MAPS_API_KEY=fake \
uv run uvicorn app.main:app --reload --port 8000
```

Mock mode is useful for UI work, repeatable development, and load testing. It
does not produce live geocoding or routing results.

## Docker and load testing

The included Docker Compose configuration runs three mock FastAPI replicas
behind Nginx on port `8080`:

```bash
docker compose up --build
```

Check the service:

```bash
curl http://localhost:8080/
```

The Compose setup is intended for backend performance and load-testing
scenarios. It does not start the Next.js frontend or PostgreSQL; use the local
development instructions above when you want the complete web application.

## API

### `GET /`

Returns a backend health response:

```json
{
  "status": "healthy"
}
```

### `POST /plan_route`

Request:

```json
{
  "user_input": "Find a pharmacy on the way to Central",
  "origin": {
    "lat": 22.3375,
    "lng": 114.2626
  }
}
```

The response contains the validated route, selected waypoint, route
alternatives, and status information produced by the agent pipeline.

The browser normally calls the Next.js proxy instead:

```text
POST /api/route/plan
```

This keeps the Python backend URL server-side and also records successful
requests in the route history table.

## Project layout

```text
.
├── app/                         # FastAPI application and route-planning agents
│   ├── agents/                  # Intent, geocoding, routing, scoring, validation
│   ├── mock/                    # Recorded external-service fixtures
│   ├── schemas/                 # Pydantic request and agent-state models
│   └── main.py                  # FastAPI application and API endpoints
├── frontend/
│   ├── app/                     # Next.js pages and API routes
│   ├── components/              # Chat, map, route cards, and UI states
│   ├── lib/                     # Database, schema, API types, and clients
│   └── package.json
├── Dockerfile                   # Container image for the FastAPI backend
├── docker-compose.yml           # Mock backend replicas and Nginx
├── nginx/                       # Reverse-proxy configuration
├── pyproject.toml               # Python dependencies and project metadata
└── uv.lock                      # Locked Python dependency versions
```

## Development commands

### Backend

```bash
uv run uvicorn app.main:app --reload
uv run black app
```

### Frontend

Run these commands from `frontend/`:

```bash
pnpm dev
pnpm build
pnpm start
pnpm db:push
```

## Contributing

Issues and pull requests are welcome. Before opening a pull request:

1. Explain the user-facing behavior or bug being addressed.
2. Keep changes focused and update the README when setup or behavior changes.
3. Run the relevant backend or frontend checks locally.
4. Do not include API keys, database credentials, generated build output, or
   local environment files.

## License

PathPilot is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/). You're free to use, modify, and share it for noncommercial purposes. Commercial use, including selling it, isn't permitted. See the [LICENSE](LICENSE) file for the full terms.

Required Notice: Copyright (c) 2026 Abdur Rafay Khan