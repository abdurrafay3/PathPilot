"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import { decode } from "@googlemaps/polyline-codec";
import L from "leaflet";
import type { ConstraintValidatorAgentOutput } from "@/lib/types";

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)["_getIconUrl"];
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function RouteLayer({ route }: { route: ConstraintValidatorAgentOutput }) {
  const map = useMap();

  const polylinePositions = useMemo((): [number, number][] => {
    if (route.status === "valid_route_found" && route.final_route?.detour_route?.polyline) {
      return decode(route.final_route.detour_route.polyline).map(
        ([lat, lng]) => [lat, lng] as [number, number]
      );
    }
    return [];
  }, [route]);

  const waypointMarkers = useMemo(() => {
    if (route.status !== "valid_route_found" || !route.final_route) {
      return [];
    }

    const waypoints = route.final_route.waypoints?.length
      ? route.final_route.waypoints
      : route.final_route.waypoint
        ? [route.final_route.waypoint]
        : [];

    return waypoints.filter((waypoint) => waypoint.coordinates);
  }, [route]);

  useEffect(() => {
    const bounds = L.latLngBounds(polylinePositions);

    waypointMarkers.forEach((waypoint) => {
      bounds.extend([waypoint.coordinates.lat, waypoint.coordinates.lng]);
    });

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [polylinePositions, waypointMarkers, map]);

  if (route.status !== "valid_route_found" || !route.final_route) return null;

  return (
    <>
      {polylinePositions.length > 0 && (
        <Polyline
          positions={polylinePositions}
          color="#f93636"
          weight={5}
          opacity={0.9}
        />
      )}
      {waypointMarkers.map((waypoint, index) => (
        <Marker
          key={`${waypoint.name}-${waypoint.coordinates.lat}-${waypoint.coordinates.lng}-${index}`}
          position={[waypoint.coordinates.lat, waypoint.coordinates.lng]}
        >
          <Popup>
            <div className="min-w-[160px] font-sans text-sm text-slate-800">
              <div className="mb-1 text-base font-bold">{waypoint.name}</div>
              <div className="capitalize text-slate-500">{waypoint.place_type.replace(/_/g, " ")}</div>
              {waypoint.rating != null && (
                <div className="mt-1 text-slate-600">
                  Rating: <span className="font-medium">{waypoint.rating}</span> / 5
                </div>
              )}
              {waypoint.open_now != null && (
                <div className={`mt-1 font-medium ${waypoint.open_now ? "text-emerald-600" : "text-red-600"}`}>
                  {waypoint.open_now ? "Open Now" : "Closed"}
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default function MapPanel({ route }: { route: ConstraintValidatorAgentOutput | null }) {
  return (
    <MapContainer
      center={[22.3193, 114.1694]}
      zoom={12}
      className="h-full w-full"
      zoomControl={true}
      style={{ background: "#dbeafe" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        subdomains="abc"
        maxZoom={20}
      />
      {route && <RouteLayer route={route} />}
    </MapContainer>
  );
}
