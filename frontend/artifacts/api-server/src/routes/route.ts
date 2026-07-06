import { Router } from "express";
import { db } from "@workspace/db";
import { routeHistoryTable } from "@workspace/db";
import { desc } from "drizzle-orm";
import { logger } from "../lib/logger";

const router = Router();

const BACKEND_URL = process.env.PATHPILOT_BACKEND_URL ?? "";

router.post("/route/plan", async (req, res) => {
  const { prompt } = req.body as { prompt?: string };

  if (!prompt || typeof prompt !== "string" || prompt.trim().length === 0) {
    res.status(400).json({ error: "prompt is required" });
    return;
  }

  if (!BACKEND_URL) {
    res.status(502).json({ error: "PATHPILOT_BACKEND_URL is not configured" });
    return;
  }

  try {
    const upstreamRes = await fetch(`${BACKEND_URL}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt.trim() }),
    });

    if (!upstreamRes.ok) {
      const text = await upstreamRes.text();
      req.log.error({ status: upstreamRes.status, body: text }, "Upstream backend error");
      res.status(502).json({ error: "Upstream backend returned an error" });
      return;
    }

    const result = await upstreamRes.json() as {
      accepted_routes: unknown[];
      final_route: {
        waypoint?: { name?: string };
        detour_route?: { duration_minutes?: number };
      } | null;
      status: string;
    };

    const duration = result.final_route?.detour_route?.duration_minutes ?? null;
    const waypointName = result.final_route?.waypoint?.name ?? null;

    await db.insert(routeHistoryTable).values({
      prompt: prompt.trim(),
      status: result.status,
      duration_minutes: duration,
      waypoint_name: waypointName,
    });

    res.json(result);
  } catch (err) {
    req.log.error({ err }, "Failed to call upstream backend");
    res.status(502).json({ error: "Failed to reach the route planning backend" });
  }
});

router.get("/route/history", async (req, res) => {
  try {
    const history = await db
      .select()
      .from(routeHistoryTable)
      .orderBy(desc(routeHistoryTable.created_at))
      .limit(50);
    res.json(history);
  } catch (err) {
    req.log.error({ err }, "Failed to fetch route history");
    res.status(500).json({ error: "Failed to fetch route history" });
  }
});

export default router;
