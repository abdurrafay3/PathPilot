import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import { decode } from '@googlemaps/polyline-codec';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import type { ConstraintValidatorAgentOutput } from '@workspace/api-client-react';

// Fix leaflet default icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface MapPanelProps {
  route: ConstraintValidatorAgentOutput | null;
}

function RouteLayer({ route }: { route: ConstraintValidatorAgentOutput }) {
  const map = useMap();
  
  const polylinePositions = useMemo(() => {
    if (route.status === 'valid_route_found' && route.final_route?.detour_route?.polyline) {
      const decoded = decode(route.final_route.detour_route.polyline);
      return decoded.map(([lat, lng]) => [lat, lng] as [number, number]);
    }
    return [];
  }, [route]);

  useEffect(() => {
    if (polylinePositions.length > 0) {
      const bounds = L.latLngBounds(polylinePositions);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [polylinePositions, map]);

  if (route.status !== 'valid_route_found' || !route.final_route) return null;

  const { waypoint } = route.final_route;

  return (
    <>
      {polylinePositions.length > 0 && (
        <Polyline positions={polylinePositions} color="hsl(var(--primary))" weight={5} opacity={0.8} />
      )}
      <Marker position={[waypoint.coordinates.lat, waypoint.coordinates.lng]}>
        <Popup>
          <div className="text-sm font-sans">
            <div className="font-bold text-base">{waypoint.name}</div>
            <div className="text-muted-foreground">{waypoint.place_type}</div>
            {waypoint.rating && <div>Rating: {waypoint.rating} / 5</div>}
            {waypoint.open_now !== undefined && (
              <div className={waypoint.open_now ? "text-green-600" : "text-destructive"}>
                {waypoint.open_now ? "Open Now" : "Closed"}
              </div>
            )}
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export function MapPanel({ route }: MapPanelProps) {
  // Default to a central location if no route, e.g., San Francisco
  const defaultCenter: [number, number] = [37.7749, -122.4194];

  return (
    <div className="h-full w-full bg-slate-900 relative">
      <MapContainer
        center={defaultCenter}
        zoom={13}
        className="h-full w-full z-0"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="dark-map-tiles"
        />
        {route && <RouteLayer route={route} />}
      </MapContainer>
    </div>
  );
}
