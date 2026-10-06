"""
Builds the before/after latency charts from the timing CSVs.

Run from the project root:
    uv run --no-project --with matplotlib python app/loadtest/latency_charts.py
Outputs PNGs to app/loadtest/charts/.
"""
import csv
import heapq
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "charts"
BEFORE_CSV = ROOT / "timing_baseline.csv"
AFTER_CSV = ROOT / "timing_step4.csv"

# Reference palette (light mode)
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#7a7974"
GRID = "#e6e5e0"
GOOGLE = "#2a78d6"   # slot 1 blue
LLM = "#eb6834"      # slot 2 orange
PLANNER = "#1baf7a"  # slot 3 aqua (sub-3:1 contrast, so every lane is direct-labelled)

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": TEXT_PRIMARY,
    "axes.edgecolor": GRID,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
})


def load_requests(path):
    """Split the timing CSV into one list of rows per request."""
    requests, current = [], []
    for row in csv.DictReader(open(path)):
        row["t"] = float(row["Time Taken"])
        current.append(row)
        if row["Call"] == "total_request":
            requests.append(current)
            current = []
    return requests


def q95(xs):
    """p95 with linear interpolation, same as pandas (and timing_report.py)."""
    xs = sorted(xs)
    k = 0.95 * (len(xs) - 1)
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


def rounded_bar(ax, x, y, width, height, color, radius=0.08):
    ax.add_patch(FancyBboxPatch(
        (x, y), max(width, 0.001), height,
        boxstyle=f"round,pad=0,rounding_size={min(radius, width / 2, height / 2)}",
        linewidth=0, facecolor=color, mutation_aspect=1,
    ))


# ---------------------------------------------------------------------------
# Chart 1: every request, before vs after
# ---------------------------------------------------------------------------
def chart_distribution(before, after):
    def totals(reqs):
        return [(r[-1]["t"], r[-1]["Status"] == "ok") for r in reqs]

    b, a = totals(before), totals(after)
    b_all, a_all = [t for t, _ in b], [t for t, _ in a]
    b_med, a_med = st.median(b_all), st.median(a_all)
    b_p95, a_p95 = q95(b_all), q95(a_all)

    fig = plt.figure(figsize=(12, 12), dpi=100)

    fig.text(0.07, 0.915, "Route planning got 79% faster", fontsize=40, weight="bold")
    fig.text(0.07, 0.875,
             "PathPilot /plan_route, 15 real requests each against live OpenAI + Google APIs",
             fontsize=19, color=TEXT_SECONDARY)

    # hero numbers
    for i, (label, before_v, after_v) in enumerate([
        ("Median response time", b_med, a_med),
        ("95th percentile", b_p95, a_p95),
    ]):
        x0 = 0.07 + i * 0.45
        fig.text(x0, 0.80, label, fontsize=19, color=TEXT_SECONDARY)
        fig.text(x0, 0.725, f"{before_v:.0f}s", fontsize=58, color=TEXT_MUTED, weight="bold")
        fig.text(x0 + 0.135, 0.738, "→", fontsize=40, color=TEXT_MUTED)
        fig.text(x0 + 0.195, 0.725, f"{after_v:.0f}s", fontsize=58, color=TEXT_PRIMARY, weight="bold")

    ax = fig.add_axes([0.17, 0.19, 0.77, 0.45])
    rows = [("Before", b, LLM, 1.0), ("After", a, GOOGLE, 0.0)]
    for name, data, color, y in rows:
        # deterministic jitter so overlapping requests stay visible
        for i, (t, ok) in enumerate(sorted(data)):
            dy = ((i * 7) % 5 - 2) * 0.045
            ax.scatter(t, y + dy, s=260, zorder=3,
                       facecolor=color if ok else SURFACE,
                       edgecolor=SURFACE if ok else color, linewidth=2.5 if not ok else 2)
        med = st.median([t for t, _ in data])
        ax.plot([med, med], [y - 0.2, y + 0.2], color=TEXT_PRIMARY, linewidth=2, zorder=4)
        ax.text(med, y + 0.27, f"median {med:.1f}s", ha="center", fontsize=17,
                color=TEXT_PRIMARY, weight="bold")
        ax.text(-3, y, name, ha="right", va="center", fontsize=22, color=TEXT_PRIMARY, weight="bold")

    ax.set_xlim(0, 90)
    ax.set_ylim(-0.55, 1.55)
    ax.set_yticks([])
    ax.set_xticks(range(0, 91, 15))
    ax.set_xticklabels([f"{x}s" for x in range(0, 91, 15)], fontsize=16)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("End-to-end response time per request (each dot = one request)",
                  fontsize=16, color=TEXT_SECONDARY, labelpad=10)

    fig.text(0.07, 0.085,
             "Before: an LLM agent orchestrated ~25 Google API calls one at a time.",
             fontsize=16, color=TEXT_SECONDARY)
    fig.text(0.07, 0.058,
             "After: deterministic pipeline, parallel calls with asyncio.gather, compact classifier output.",
             fontsize=16, color=TEXT_SECONDARY)
    fig.text(0.07, 0.031, "Hollow dot = failed request (1 per run).", fontsize=14, color=TEXT_MUTED)

    out = OUT / "latency_before_after.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Chart 2: one request as a timeline, before vs after
# ---------------------------------------------------------------------------
def build_timeline(req, parallel):
    """
    Turn one request's measured call durations into (lane, start, duration, kind) bars.
    Durations are measured; start times are reconstructed from the pipeline's order
    (sequential before, gather + semaphore(10) after).
    """
    calls = [r for r in req if r["Call"] != "total_request"]
    get = lambda pred: [r for r in calls if pred(r)]
    reverse = get(lambda r: r["Call"] == "geocode_reverse")[0]["t"]
    normalizer = get(lambda r: "normalize" in r["Function"])[0]["t"]
    geocode = sum(r["t"] for r in get(lambda r: r["Call"] == "geocode_forward"))
    routes = get(lambda r: r["Function"].startswith("route_candidate"))[0]["t"]
    places = [r["t"] for r in get(lambda r: r["Call"] == "places_nearby")]
    classifier = get(lambda r: "classify" in r["Function"])[0]["t"]
    detours = [r["t"] for r in get(lambda r: "detour" in r["Function"])]
    planner = get(lambda r: r["Function"] == "route_planner.plan_route")[0]["t"]

    bars = []
    t = 0.0
    bars.append(("Geocoding & routes", t, reverse, "google")); t += reverse
    bars.append(("Intent normalizer (LLM)", t, normalizer, "llm")); t += normalizer
    planner_end = t + planner

    if not parallel:
        # The agent's own LLM turns are only measured in total (planner time minus tools);
        # split evenly across the ~6 turns that precede each tool call and the final answer.
        tools = geocode + routes + sum(places) + classifier + sum(detours)
        turn = (planner - tools) / 6
        bars.append(("Planner agent LLM turns", t, turn, "planner")); t += turn
        bars.append(("Geocoding & routes", t, geocode, "google")); t += geocode
        bars.append(("Planner agent LLM turns", t, turn, "planner")); t += turn
        bars.append(("Geocoding & routes", t, routes, "google")); t += routes
        bars.append(("Planner agent LLM turns", t, turn, "planner")); t += turn
        for i, d in enumerate(places):
            bars.append((f"places_{i}", t, d, "google")); t += d
        bars.append(("Classifier (LLM)", t, classifier, "llm")); t += classifier
        bars.append(("Planner agent LLM turns", t, turn, "planner")); t += turn
        for i, d in enumerate(detours):
            bars.append((f"detour_{i}", t, d, "google")); t += d
        bars.append(("Planner agent LLM turns", t, turn * 2, "planner")); t += turn * 2
    else:
        bars.append(("Geocoding & routes", t, geocode, "google")); t += geocode
        bars.append(("Geocoding & routes", t, routes, "google")); t += routes
        # semaphore(10): first 10 start together, the rest start as slots free up
        slots = [t] * 10
        heapq.heapify(slots)
        end = t
        for i, d in enumerate(places):
            start = heapq.heappop(slots)
            bars.append((f"places_{i}", start, d, "google"))
            heapq.heappush(slots, start + d)
            end = max(end, start + d)
        t = end
        bars.append(("Classifier (LLM)", t, classifier, "llm")); t += classifier
        for i, d in enumerate(detours):
            bars.append((f"detour_{i}", t, d, "google"))
        t += max(detours)
    return bars, planner_end, len(places), len(detours)


def chart_timeline(before_req, after_req):
    b_bars, b_end, n_places, n_detours = build_timeline(before_req, parallel=False)
    a_bars, a_end, _, _ = build_timeline(after_req, parallel=True)

    # lane layout (top to bottom)
    lanes = (["Geocoding & routes", "Intent normalizer (LLM)", "Planner agent LLM turns"]
             + [f"places_{i}" for i in range(n_places)]
             + ["Classifier (LLM)"]
             + [f"detour_{i}" for i in range(n_detours)])
    # thin rows for individual calls, extra space around the single-bar lanes
    y_of, y = {}, 0.0
    for name in reversed(lanes):
        single = not name.startswith(("places_", "detour_"))
        prev_single = y_of and not list(y_of)[-1].startswith(("places_", "detour_"))
        if y_of:
            y += 2.2 if (single or prev_single) else 1.0
        y_of[name] = y
    top = y
    colors = {"google": GOOGLE, "llm": LLM, "planner": PLANNER}

    fig = plt.figure(figsize=(12, 12), dpi=100)
    fig.text(0.07, 0.935, "Same request, before and after", fontsize=40, weight="bold")
    fig.text(0.07, 0.897,
             '"Take me to Mongkok with a restaurant on the way", 15 Places + 9 Routes calls',
             fontsize=19, color=TEXT_SECONDARY)

    panels = [("Before: LLM agent, calls one at a time", b_bars, b_end, 0.52),
              ("After: deterministic pipeline, calls in parallel", a_bars, a_end, 0.13)]
    for title, bars, end, bottom in panels:
        ax = fig.add_axes([0.25, bottom, 0.70, 0.30])
        for lane, start, dur, kind in bars:
            rounded_bar(ax, start, y_of[lane] - 0.36, dur, 0.72, colors[kind])
        ax.set_xlim(0, 60)
        ax.set_ylim(-0.8, top + 0.8)
        ax.set_xticks(range(0, 61, 10))
        ax.set_xticklabels([f"{x}s" for x in range(0, 61, 10)], fontsize=15)
        ax.set_yticks([])
        ax.grid(axis="x", color=GRID, linewidth=1)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.text(0, top + 2.0, title, fontsize=20, weight="bold")
        ax.axvline(end, color=TEXT_PRIMARY, linewidth=1.5, linestyle=(0, (3, 3)))
        ax.text(end + 0.6, top * 0.5, f"{end:.1f}s", fontsize=26, weight="bold", va="center")

        # direct lane labels (identity never relies on colour alone)
        def label(text, y):
            ax.text(-1.0, y, text, ha="right", va="center", fontsize=14, color=TEXT_SECONDARY)
        label("Geocoding & routes", y_of["Geocoding & routes"])
        label("Intent normalizer (LLM)", y_of["Intent normalizer (LLM)"])
        label("Planner agent turns (LLM)", y_of["Planner agent LLM turns"])
        label(f"{n_places} Places searches", (y_of["places_0"] + y_of[f"places_{n_places - 1}"]) / 2)
        label("Classifier (LLM)", y_of["Classifier (LLM)"])
        label(f"{n_detours} detour routes", (y_of["detour_0"] + y_of[f"detour_{n_detours - 1}"]) / 2)
        if not any(kind == "planner" for _, _, _, kind in bars):
            ax.text(0.6, y_of["Planner agent LLM turns"], "removed (deterministic pipeline)",
                    va="center", fontsize=14, color=TEXT_MUTED, style="italic")

    # legend (3 series)
    for i, (name, color) in enumerate([("Google Maps API call", GOOGLE),
                                       ("OpenAI call (gpt-4o-mini)", LLM),
                                       ("Planner agent's own LLM turns", PLANNER)]):
        x = 0.07 + i * 0.30
        fig.patches.append(FancyBboxPatch((x, 0.052), 0.022, 0.016, boxstyle="round,pad=0,rounding_size=0.004",
                                          transform=fig.transFigure, facecolor=color, linewidth=0))
        fig.text(x + 0.03, 0.054, name, fontsize=15, color=TEXT_SECONDARY)
    fig.text(0.07, 0.018,
             "Call durations are measured. Start times are reconstructed from the pipeline order; "
             "the agent's LLM-turn total is split evenly between turns.",
             fontsize=12, color=TEXT_MUTED)

    out = OUT / "latency_timeline.png"
    fig.savefig(out)
    plt.close(fig)
    return out


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    before, after = load_requests(BEFORE_CSV), load_requests(AFTER_CSV)
    print(chart_distribution(before, after))
    print(chart_timeline(before[0], after[0]))
