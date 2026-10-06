# PathPilot: Latency Optimisation Plan

Plan to cut end-to-end latency of `/plan_route`. Baseline numbers come from the real-API run in [`timing_report_baseline.csv`](../../timing_report_baseline.csv) (raw rows: `timing_baseline.csv`, 14 live requests, Sep 27). Savings below are **estimates**. Re-measure with `timing_script.py` after each step and record the measured numbers in [CV_PROGRESS.md](CV_PROGRESS.md).

Last updated: 2026-10-03

---

## Target

| | Baseline | Estimate (all steps) | **Measured (steps 1–4)** |
|---|---|---|---|
| Median | 39.1s | ~8–10s (~75% faster) | **8.1s (−79%)** |
| p95 | 74.9s | should improve even more | **10.9s (−85%)** |

---

## Measured results

Real APIs, all 15 prompts in `example_prompts.txt`, one request at a time. Median/p95 use the same method as `timing_report.py` (pandas interpolation), over all requests including failures.

| Run | File | Median | p95 | Max | Failures | Google call median |
|---|---|---|---|---|---|---|
| Baseline (Sep 27) | `timing_baseline.csv` | 39.1s | 74.9s | 83.5s | 1/14 (`MaxTurnsExceeded`) | 0.36s |
| Steps 1 + 3 (Sep 30) | `timing_step3.csv` | 33.6s | 48.1s | 58.9s | 1/15 (422, fallback bug) | 1.06s (slow VPN server) |
| **Steps 1–4 (Oct 3)** | `timing_step4.csv` | **8.1s** | **10.9s** | **12.0s** | 1/15 (geocode timeout, see below) | **0.35s** |

**Steps 1–4 vs baseline: median −79%, p95 −85%, max −86%, mean 42.5s → 8.4s.** Every request finished in 3.6–12.0s (baseline: 9.8–83.5s). Google call latency matched the baseline (0.35s vs 0.36s), so the comparison is like-for-like.

**Network:** OpenAI requires a VPN from Hong Kong, and the VPN server determines Google latency: a far server gave ~1.06s per call (Sep 30 run), a nearby one ~0.3s (curl check: 0.22–0.39s). Use the same nearby server for every timing and load-test run. The Sep 30 step 3 numbers are therefore pessimistic.

**Not covered:** prompt 15 (the heaviest at baseline: 86 Google calls, 83.5s) failed on a geocode timeout, so the steps 1–4 numbers are over 14 completed requests + 1 failure. Worth rerunning that one prompt after the timeout fix.

**Per-component medians (per request):**

| Component | Baseline | Steps 1 + 3 (slow VPN) | **Steps 1–4** | Notes |
|---|---|---|---|---|
| Planner, whole run (incl. tools) | 35.9s | 28.2s | **4.3s** | Steps 1, 3, 4 |
| Planner's own LLM turns | ~15s | ~0.4s | ~0s | Step 1. No more `MaxTurnsExceeded` |
| Places (wall time) | ~6s sequential | ~3–6s | <1s | Step 3 |
| Detours (summed call time) | 2.7s | 8.2s | 2.7s | Step 4: same total call time, but calls now overlap (~1 round) |
| Classifier (LLM) | 10.7s | 13.7s | **2.0s** | Step 2: returns kept IDs only (~20 output tokens instead of full JSON) |
| Intent normalizer (LLM) | 3.1s | 4.3s | 3.7s | Unchanged; now the largest single cost |

Intermediate runs: `timing_step1.csv` (step 1 only, 3 usable requests: planner overhead 0.4–0.7s vs ~14.8s median at baseline), `timing_step3_5prompts.csv` (first 5 prompts).

### Fixes made along the way

Removing the planner agent exposed errors the LLM used to absorb by retrying tools:

- **Geocoding crash → 500 + connection reset:** `ZERO_RESULTS` raised an uncaught `ValueError`/`IndexError`; uvicorn then closed the keep-alive connection, resetting the next request too. Now raises `GeocodingError`, returned as a 422.
- **Generic destinations ("airport"):** the normalizer passed category words the Geocoding API can't resolve. Added a prompt rule to output full place names ("Hong Kong International Airport, Hong Kong"), `region=hk`, and a Places Text Search fallback biased to the origin.
- **LLM-invented coordinates:** the normalizer sometimes filled in coordinates itself, skipping geocoding. `main.py` now clears destination coordinates (always geocoded) and keeps origin coordinates only if they match the request.
- **Text Search fallback result ignored** (fixed): it always raised, so prompt 14 ("the hospital") got a 422 although Text Search found it. Now returns the fallback. Prompt 14 succeeded in the steps 1–4 run.
- **Open bug: fallback returns `None` when Text Search also finds nothing.** That `None` flows into `fetch_candidate_routes` and crashes on `.lat` (500). Needs `if fallback: return fallback` followed by `raise GeocodingError(...)`.
- **Open bug: geocoding timeout → 500.** `get_coordinates_from_address` uses `httpx.AsyncClient()` with httpx's default 5s timeout; one slow call (prompt 15, Oct 3) raised an uncaught `httpx.TimeoutException`. Set `timeout=10.0` and catch timeouts (retry once or raise `GeocodingError`).
- **`RequestError` handler** (fixed): `search_nearest_waypoints` read `e.response`, which `RequestError` doesn't have; would have crashed a whole `gather` on any timeout.
- **Detour gather bugs** (fixed before measuring): the job list stored the `order_waypoints` function instead of the list, every call reused a stale `ordered_waypoints`, and the gather sat inside the route loop (re-fetching earlier routes' jobs).
- **Classifier `filtered` list** (fixed before measuring): a list comprehension without its `for` kept only the last route.

---

## Where the 39s goes today (baseline)

Every step runs one after another.

| Step | Median |
|---|---|
| Reverse geocode ([geocoder.py](../agents/geocoder.py)) | 0.3s |
| Intent normalizer, gpt-4o-mini ([intent_normalizer.py](../agents/intent_normalizer.py)) | 3.1s |
| **Planner agent, whole run incl. tools** ([route_planner.py](../agents/route_planner.py)) | **35.9s** |
| ↳ ~20 Places Nearby calls, one at a time | ~6.5s |
| ↳ Waypoint classifier, gpt-4o-mini | 10.7s |
| ↳ ~7–9 detour Routes calls, one at a time | ~2.5s |
| ↳ Forward geocoding + candidate routes | ~0.7s |
| ↳ **Planner's own LLM turns** (35.9s minus tools) | **~15s** |

---

## Optimisations (largest saving first)

### 1. Replace the planner agent with plain code: saves ~15s

The planner is an LLM that spends 5–6 model turns deciding to call the tools in an order the prompt already fixes. It is also the source of the `MaxTurnsExceeded` failures (~1 in 15 real requests).

- The replacement already exists: the `if MOCK:` branch in [route_planner.py:50-65](../agents/route_planner.py#L50-L65) runs the same steps as ordinary code.
- Use that path for real requests and drop `fake_latency(10, 20)`.
- Bonus: fewer OpenAI tokens per request, and no more `MaxTurnsExceeded`.

### 2. Shorten the classifier's output: saves ~6–8s

`classify_waypoint_candidates` uses `output_type=WaypointFinderAgentOutput` ([waypoint_finder.py:303](../agents/waypoint_finder.py#L303)), so the model writes every candidate back out in full (name, coordinates, rating, …). LLM response time is mostly spent generating output.

- Have it return only the IDs of the places it keeps, e.g. `{"keep": [3, 7, 12]}`, and fill in the rest from data already in memory.
- Send fewer fields in the prompt.
- Cap the candidates sent (e.g. the 10 closest to the route).
- Expected: 10.7s → ~2–4s.

### 3. Run the Places calls in parallel: saves ~6s

The triple loop at [waypoint_finder.py:168-177](../agents/waypoint_finder.py#L168-L177) awaits each `search_nearest_waypoints` call before starting the next.

- Start them all with `asyncio.gather`, limited by an `asyncio.Semaphore` of ~10 to stay under Google's rate limit.
- Merge the results afterwards with the same dedupe logic (`seen_waypoints`, keep the closest).
- Expected: ~20 × 0.37s → ~0.5s.

### 4. Run the detour Routes calls in parallel: saves ~2s

Same idea for the loop around [detour_scorer.py:366](../agents/detour_scorer.py#L366).

- Separate detours can run at the same time with `asyncio.gather`.
- For transit, the legs of one detour depend on each other ([detour_scorer.py:153-164](../agents/detour_scorer.py#L153-L164)), so keep those sequential within a detour.
- Expected: ~2.5s → ~0.4s.

### 5. Reuse one HTTP client: saves ~0.1s per call

Every Google call creates a new `httpx.AsyncClient`, which means a new TLS connection each time. This happens in 6 places:

- [route_candidate.py:75](../agents/route_candidate.py#L75)
- [waypoint_finder.py:64](../agents/waypoint_finder.py#L64)
- [detour_scorer.py:90](../agents/detour_scorer.py#L90), [detour_scorer.py:244](../agents/detour_scorer.py#L244)
- [geocoder.py:27](../agents/geocoder.py#L27), [geocoder.py:58](../agents/geocoder.py#L58)

Create one client at app startup (FastAPI lifespan) and share it. The per-request saving is small once calls run in parallel, but it also cuts CPU use under load, which the load tests would pick up.

### 6. Small extras: under 0.5s

- Geocode origin and destination at the same time ([geocoder.py:101-106](../agents/geocoder.py#L101-L106)).

---

## Estimate after all steps

| Step | Estimated median |
|---|---|
| Reverse geocode | 0.3s |
| Intent normalizer | 3.1s |
| Forward geocoding (parallel) | 0.35s |
| Candidate routes | 0.3s |
| Places (one parallel round) | 0.5s |
| Classifier (short output) | ~3s |
| Detours (parallel) | ~0.4s |
| **Total** | **~8s** (up to ~10s if the classifier stays slower) |

The two remaining LLM calls (normalizer and classifier) make up ~75% of this. Going below ~5s would take bigger changes: a faster model, or skipping the classifier when Google's place types already match what the user asked for.

---

## Caveats

- **Thin baseline:** 14 requests.
- **Call counts vary:** the number of Places calls depends on route length and how many Google place types each required stop maps to.
- **Estimates only:** re-measure after each change.
- **Update mock mode too:** it hard-codes today's sequential delays (e.g. `fake_latency(10, 20)` for the planner). After optimising, update it to match the new call pattern, or load tests will still show ~41s.

---

## Checklist

1. [x] Step 1: deterministic pipeline instead of planner agent → planner overhead ~15s → ~0.4s
2. [x] Step 3: parallel Places calls (`asyncio.gather`, semaphore 10) → Places ~3–6s wall time
3. [x] Full 15-prompt real run after steps 1 + 3 → median 33.6s, p95 48.1s (`timing_step3.csv`, slow VPN server)
4. [x] Fix: return the Text Search fallback result
5. [x] Fix: `search_nearest_waypoints` `RequestError` handler
6. [x] Step 4: parallel detour calls (`asyncio.gather`, semaphore 10, all routes in one round)
7. [x] Step 2: classifier returns kept IDs only; compact one-line-per-place prompt; skipped when there are no candidates
8. [x] Full 15-prompt real run after steps 1–4 → **median 8.1s, p95 10.9s** (`timing_step4.csv`)
9. [ ] Fix: raise `GeocodingError` when the Text Search fallback also returns nothing
10. [ ] Fix: explicit geocoding timeout + handle `httpx.TimeoutException`; rerun prompt 15
11. [ ] Step 5: shared `httpx.AsyncClient`
12. [ ] ~~Step 6: parallel forward geocoding~~ (dropped: destination lookup is now biased by origin coordinates, and the origin is rarely geocoded)
13. [ ] Update mock-mode delays to match the new pipeline: remove planner `fake_latency(10, 20)`, classifier `fake_latency(10.74, 18.16)` → ~1–3s (measured median 2.0s)
14. [ ] Rerun load tests (single worker + nginx) with the new mock latencies
