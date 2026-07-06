import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { routeHistoryTable } from "@/lib/schema";
import type { Coordinates } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 600;

const BACKEND_URL = process.env.PATHPILOT_BACKEND_URL ?? "http://127.0.0.1:8000/plan_route";
const DEFAULT_ORIGIN: Coordinates = {
  lat: 22.3375,
  lng: 114.2626,
};

function resolveOrigin(origin?: Coordinates): Coordinates {
  if (
    origin &&
    typeof origin.lat === "number" &&
    typeof origin.lng === "number" &&
    Number.isFinite(origin.lat) &&
    Number.isFinite(origin.lng)
  ) {
    return origin;
  }

  return DEFAULT_ORIGIN;
}

export async function POST(req: NextRequest) {
  let body: { prompt?: string; origin?: Coordinates };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { prompt } = body;
  const origin = resolveOrigin(body.origin);

  if (!prompt || typeof prompt !== "string" || prompt.trim().length === 0) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }

  try {
    const upstreamRes = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_input: prompt.trim(),
        origin,
      }),
    });

    if (!upstreamRes.ok) {
      const text = await upstreamRes.text();
      console.error("Upstream error", upstreamRes.status, text);
      return NextResponse.json(
        { error: "The route planning backend returned an error" },
        { status: 502 }
      );
    }

    const result = await upstreamRes.json().catch((err) => {
      console.error("Failed to parse backend JSON", err);
      return null;
    });

    if (!result || typeof result !== "object") {
      return NextResponse.json(
        { error: "The route planning backend returned an invalid response" },
        { status: 502 }
      );
    }

    const duration =
      (result.final_route?.detour_route?.duration_minutes as number | undefined) ?? null;
    const waypointName =
      (result.final_route?.waypoint?.name as string | undefined) ?? null;

    try {
      await db.insert(routeHistoryTable).values({
        prompt: prompt.trim(),
        status: result.status as string,
        duration_minutes: duration,
        waypoint_name: waypointName,
      });
    } catch (dbError) {
      console.error("Failed to store route history", dbError);
    }

    return NextResponse.json(result);
  } catch (err) {
    console.error("Failed to reach upstream backend", err);
    return NextResponse.json(
      { error: "Failed to reach the route planning backend" },
      { status: 502 }
    );
  }
}
