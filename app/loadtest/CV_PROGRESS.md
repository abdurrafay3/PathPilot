# PathPilot: Load Testing & Performance Progress

Personal log of what's been measured so far and the CV statements each result supports.
Only statements backed by recorded data are marked **Ready**. Update this file after each stage.

Last updated: 2026-09-28

---

## CV statements

### Ready (backed by data below)

- **Instrumentation / profiling**
  > Instrumented a multi-agent LLM route-planning API (FastAPI, OpenAI Agents SDK, Google Maps/Places/Routes) with per-call latency and status tracking; identified that ~92% of request time (36s of 39s median) was spent in the LLM orchestration agent and ~27 sequential Google API calls per request.

- **Load-testing methodology**
  > Built a Locust load-testing harness with a recorded-fixture mock mode that replays real Google/OpenAI responses at measured latencies (median–p95 per call), enabling repeatable, zero-cost load tests of the full pipeline without hitting third-party rate limits.

- **Single-worker capacity**
  > Load-tested a single async uvicorn worker up to 5,000 concurrent users (~113 RPS, 34.7k requests over 5 min) with 0% errors and flat p95/p99 latency, using ~40% of one CPU core.

- **Single-worker limit**
  > Found the single-worker limit: it sustained 7,500 concurrent users (~167 RPS, 51.5k requests over 5 min) with 0% errors and p95 of 48s vs. 47s at 10 users; at 10,000 users it saturated one CPU core (~95%) and 4% of requests failed.

- **Reliability finding**
  > Surfaced a production reliability bug through instrumentation: the LLM planner agent intermittently exceeded its tool-call turn limit (`MaxTurnsExceeded`), failing ~1 in 15 real requests.

### Pending (fill in the numbers after the next stages)

- **Horizontal scaling** (Docker + nginx, pending)
  > Containerized the API with Docker and load-balanced ___ replicas behind nginx (___ vCPU each), raising max sustained throughput from ___ to ___ RPS and concurrent capacity from ___ to ___ users at <1% error rate.

- **Latency optimization** (pending)
  > Cut p50 end-to-end latency from 39s to ___s by parallelizing ~27 sequential Google API calls with `asyncio.gather` and replacing LLM-driven tool orchestration with a deterministic pipeline, also eliminating `MaxTurnsExceeded` failures and reducing OpenAI token usage.

- **Real end-to-end check** (pending)
  > Measured real end-to-end latency against live APIs at low concurrency: p50 ___s, p95 ___s.

---

## Evidence

### 1. Real-API baseline (sequential, 14 requests, live OpenAI + Google)

Source: `timing_report.csv` (project root), `timing.csv`

| Call | Median | p95 |
|---|---|---|
| **Whole request** | **39.1s** | **74.9s** |
| route_planner agent (incl. tools) | 35.9s | 71.1s |
| waypoint classifier (gpt-4o-mini) | 10.7s | 18.2s |
| intent normalizer (gpt-4o-mini) | 3.1s | 4.4s |
| Google Places Nearby | 0.37s | 0.57s |
| Google Geocoding / Routes | 0.32–0.35s | 0.38–0.58s |

Per request: ~20 Places calls, ~7 detour Routes calls, all sequential.
1 of 15 requests failed with `MaxTurnsExceeded` (planner agent).

### 2. Single uvicorn worker, mock mode (Locust, `FastHttpUser`, wait 1–5s)

Source: `results/` (Locust CSVs + `cpu_*.csv`)

| Users | Requests | Failures | Median | p95 | p99 | Max | Avg RPS | uvicorn CPU | Memory |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 178 | 0% | 41.0s | 47.0s | 49.0s | – | ~0.23 | – | – |
| 50 | 411 | 0% | 41.0s | 47.0s | 49.0s | – | ~1.1 | – | – |
| 100 | 760 | 0% | 41.0s | 47.0s | 49.0s | 50.0s | ~2.3 | – | – |
| 250 | 1,879 | 0% | 41.0s | 47.0s | 49.0s | 50.6s | ~5.8 | – | – |
| 500 | 3,515 | 0% | 41.0s | – | – | 50.6s | 10.3* | ~10% | ~130 MB |
| 1,000 | 9,919 | 0% | 41.0s | – | – | 50.3s | 23.0 | not recorded | ~172 MB (idle after) |
| 3,000 | 36,296 | 0% | 41.0s | 47.0s | 49.0s | 50.7s | 63.6 | ~30% (peak 45%) | ~305 MB |
| 5,000 | 34,688 | 0% | 41.0s | 47.0s | 49.0s | 51.1s | 112.9 | ~40% (peak 83%) | ~431 MB |
| 7,500 | 51,533 | 0% | 42.0s | 48.0s | 49.0s | 52.1s | 166.8 | ~50% (spikes to 95%) | ~579 MB |
| 10,000 | – | **4%** (`HTTP 0`) | 41.0s | 48.0s | – | – | ~210–250** | **~95%** | ~750 MB |

\* Includes ramp-up (stats not reset), so lower than the expected ~11.4.
\** Inflated by instantly-failing requests; use successful RPS (total − failures/s).

**Reading:** RPS tracks `users ÷ ~44s` up to 7,500 users (98% of expected at 7,500), so the server kept up. Latency stayed at the mock delays until 7,500, where median and p95 rose by 1s (first sign of load, from CPU spikes to ~95%). At 10,000 the worker saturated one core, and failures were connection-level (no HTTP response). **Single-worker limit: between 7,500 and 10,000 concurrent users (~170–230 RPS).**

7,500 run: fresh server process (default 5s keep-alive), `caffeinate` running, on battery power, no sleep events in `pmset` log. (An earlier 7,500 attempt was discarded: the Mac went to sleep mid-run.)

**10,000-user failure diagnosis:** ~9,900 open connections + ~6,000 in `TIME_WAIT` exhausted macOS's ~16k ephemeral port range; the server was also near its 10,240 file-descriptor limit. Connection churn came from uvicorn's 5s keep-alive timeout vs. the users' 1–5s wait time. Fix for the next run: `--timeout-keep-alive 30`, `ulimit -n 65536`, `locust --processes 4`.

---

## Methodology (state this alongside any numbers)

- **Hardware:** Apple M5, 10 cores, 32 GB RAM, macOS 27. Load generator and server on the same machine.
- **Software:** Python 3.13.5, FastAPI 0.139.0, uvicorn 0.49.0 (1 worker), Locust 2.46.6.
- **Mock mode (`MOCK_EXTERNAL=1`):** every Google/OpenAI call returns a fixture recorded from one real request, after `asyncio.sleep(uniform(median, p95))` using the measured latencies above. The planner's own LLM turns are simulated with a 10–20s delay. All app logic (parsing, scoring, validation) runs for real.
- **Traffic:** every request exercises the heaviest path (route with a required stop: Places search, classifier, detour scoring).
- **Runs:** ramp up, Reset Stats once all users have spawned, measure 5 minutes of steady state. From 7,500 on: `caffeinate` running and a fresh server process per stage (plug in the charger for future runs).
- **Honest framing:** these are load tests on a local machine with third-party APIs simulated, not production traffic.

---

## Next steps

1. [x] 7,500-user run → single-worker limit between 7,500 and 10,000 users
2. [ ] Dockerfile + single-container baseline
3. [ ] docker-compose + nginx, per-replica CPU limits, 1 / 2 / 4 replicas → scaling results
4. [ ] Latency optimization (`asyncio.gather`, deterministic pipeline) → re-run the same stages
5. [ ] Small real-API end-to-end run (5–10 users) → real p50/p95
6. [ ] Report script: Locust CSVs → tables + charts for the README
