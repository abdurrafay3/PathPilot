"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { ChatPanel } from "./ChatPanel";
import type { ConstraintValidatorAgentOutput, Coordinates, RouteHistoryItem } from "@/lib/types";

const MapPanel = dynamic(() => import("./MapPanel"), { ssr: false });

const HKUST_ORIGIN: Coordinates = {
  lat: 22.3375,
  lng: 114.2626,
};

export function Home() {
  const queryClient = useQueryClient();
  const [currentRoute, setCurrentRoute] = useState<ConstraintValidatorAgentOutput | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const [origin, setOrigin] = useState<Coordinates>(HKUST_ORIGIN);
  const [originLabel, setOriginLabel] = useState("HKUST, Hong Kong");

  useEffect(() => {
    if (!navigator.geolocation) {
      setOrigin(HKUST_ORIGIN);
      setOriginLabel("HKUST, Hong Kong");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setOrigin({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setOriginLabel("Your current browser location");
      },
      () => {
        setOrigin(HKUST_ORIGIN);
        setOriginLabel("HKUST, Hong Kong");
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 }
    );
  }, []);

  const { data: history = [] } = useQuery<RouteHistoryItem[]>({
    queryKey: ["route-history"],
    queryFn: async () => {
      const response = await fetch("/api/route/history");
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(payload?.error ?? "Failed to fetch route history");
      }

      return Array.isArray(payload) ? payload : [];
    },
  });

  const { data: health } = useQuery<{ status: string }>({
    queryKey: ["health"],
    queryFn: () => fetch("/api/healthz").then((r) => r.json()),
    refetchInterval: 30_000,
  });

  const planRoute = useMutation<
    ConstraintValidatorAgentOutput,
    Error,
    { prompt: string; origin: Coordinates }
  >({
    mutationFn: ({ prompt, origin }) =>
      fetch("/api/route/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, origin }),
      }).then(async (r) => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({ error: "Unknown error" }));
          throw new Error(err.error ?? "Failed to plan route");
        }
        return r.json();
      }),
    onSuccess: (result) => {
      setCurrentRoute(result);
      setPendingPrompt(null);
      queryClient.invalidateQueries({ queryKey: ["route-history"] });
    },
    onError: () => {
      setPendingPrompt(null);
    },
  });

  const handleSendPrompt = (prompt: string) => {
    setPendingPrompt(prompt);
    planRoute.mutate({ prompt, origin });
  };

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-slate-950">
      <div className="relative h-full flex-1">
        <MapPanel route={currentRoute} />
        {health && (
          <div className="absolute left-4 top-4 z-[400] flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-400 backdrop-blur-md">
            <span
              className={`h-2 w-2 rounded-full ${health.status === "ok" ? "bg-emerald-400" : "bg-yellow-400"}`}
            />
            System {health.status}
          </div>
        )}
      </div>
      <div className="hidden h-full w-[420px] shrink-0 md:block">
        <ChatPanel
          history={history}
          isPending={planRoute.isPending}
          pendingPrompt={pendingPrompt}
          errorMessage={planRoute.error?.message ?? null}
          originLabel={originLabel}
          onSendPrompt={handleSendPrompt}
        />
      </div>
    </div>
  );
}
