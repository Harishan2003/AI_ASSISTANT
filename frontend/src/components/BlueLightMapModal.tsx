import React, { useState, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export interface BlueLightMapModalProps {
  isOpen?: boolean;
  onClose?: () => void;
  selectedRegion?: string;
  regionTitle?: string;
  isEmbedded?: boolean;
  searchTrigger?: string | null;
  routeTrigger?: { from: string; to: string } | null;
}

interface SearchResult {
  display_name: string;
  lat: string;
  lon: string;
  type?: string;
}

interface Waypoint {
  lat: number;
  lng: number;
  name: string;
}

interface RouteInfo {
  distanceKm: number;
  durationMins: number;
  summary?: string;
}

export const BlueLightMapModal: React.FC<BlueLightMapModalProps> = ({
  isOpen = true,
  onClose,
  selectedRegion = "india",
  regionTitle = "Friday Neural Tactical Map",
  isEmbedded = false,
  searchTrigger,
  routeTrigger,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const labelsTileLayerRef = useRef<L.TileLayer | null>(null);
  const activeMarkerRef = useRef<L.Marker | null>(null);

  // Routing Refs
  const routeLayerRef = useRef<L.GeoJSON | L.Polyline | null>(null);
  const fromMarkerRef = useRef<L.Marker | null>(null);
  const toMarkerRef = useRef<L.Marker | null>(null);

  // States
  const [activeLayer, setActiveLayer] = useState<"friday_cyber" | "satellite" | "street">("friday_cyber");
  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lng: number }>({ lat: 20.5937, lng: 78.9629 });
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [currentZoom, setCurrentZoom] = useState<number>(5);
  const [selectedLocationName, setSelectedLocationName] = useState<string>("India National Hub");
  const [isRadarSweeping, setIsRadarSweeping] = useState<boolean>(true);
  const [radarAngle, setRadarAngle] = useState<number>(0);

  // From / To Navigation & Route Planner States
  const [isRouteMode, setIsRouteMode] = useState<boolean>(false);
  const [fromQuery, setFromQuery] = useState<string>("");
  const [toQuery, setToQuery] = useState<string>("");
  const [fromWaypoint, setFromWaypoint] = useState<Waypoint | null>(null);
  const [toWaypoint, setToWaypoint] = useState<Waypoint | null>(null);
  const [fromResults, setFromResults] = useState<SearchResult[]>([]);
  const [toResults, setToResults] = useState<SearchResult[]>([]);
  const [isSearchingFrom, setIsSearchingFrom] = useState<boolean>(false);
  const [isSearchingTo, setIsSearchingTo] = useState<boolean>(false);
  const [isCalculatingRoute, setIsCalculatingRoute] = useState<boolean>(false);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);

  // Radar sweeping animation loop
  useEffect(() => {
    if ((!isOpen && !isEmbedded) || !isRadarSweeping) return;
    const interval = setInterval(() => {
      setRadarAngle((prev) => (prev + 3.5) % 360);
    }, 35);
    return () => clearInterval(interval);
  }, [isOpen, isEmbedded, isRadarSweeping]);

  // Tile layer URLs (100% Free, Zero Watermark, Zero API Key Required)
  const getTileUrl = (layerType: "friday_cyber" | "satellite" | "street") => {
    switch (layerType) {
      case "satellite":
        return "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
      case "street":
        return "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";
      case "friday_cyber":
      default:
        return "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
    }
  };

  // Custom Friday Tactical Marker Icon
  const createFridayTacticalIcon = (label?: string, color: "cyan" | "green" | "red" = "cyan") => {
    const borderColor = color === "green" ? "#34d399" : color === "red" ? "#f87171" : "#00f0ff";
    const glowColor = color === "green" ? "rgba(52, 211, 153, 0.6)" : color === "red" ? "rgba(248, 113, 113, 0.6)" : "rgba(0, 240, 255, 0.6)";

    return L.divIcon({
      className: "friday-tactical-marker",
      html: `
        <div style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; pointer-events: none;">
          <div style="position: absolute; inset: 0; border-radius: 50%; border: 1.5px dashed ${borderColor}; animation: rotateArc 3s linear infinite; box-shadow: 0 0 10px ${glowColor};"></div>
          <div style="position: absolute; width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid ${borderColor}; animation: pulseRing 1.8s ease-out infinite;"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #ffffff; box-shadow: 0 0 10px ${borderColor};"></div>
          ${
            label
              ? `<div style="position: absolute; top: -24px; left: 50%; transform: translateX(-50%); background: rgba(1, 4, 9, 0.95); border: 1px solid ${borderColor}; color: ${borderColor}; font-family: 'Orbitron', monospace; font-size: 9.5px; padding: 2px 7px; border-radius: 3px; white-space: nowrap; font-weight: bold; letter-spacing: 1px; box-shadow: 0 0 10px ${glowColor}; pointer-events: none;">${label}</div>`
              : ""
          }
        </div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
  };

  // Initialize Leaflet Map
  useEffect(() => {
    if (!isOpen && !isEmbedded) return;

    const timer = setTimeout(() => {
      if (!mapContainerRef.current) return;

      if (!mapInstanceRef.current) {
        let initialLat = 20.5937;
        let initialLng = 78.9629;
        let initialZoom = 5;

        if (selectedRegion && selectedRegion !== "india" && selectedRegion !== "global") {
          if (selectedRegion === "north_america" || selectedRegion === "usa") {
            initialLat = 37.0902;
            initialLng = -95.7129;
            initialZoom = 4;
          } else if (selectedRegion === "europe") {
            initialLat = 48.8566;
            initialLng = 2.3522;
            initialZoom = 4;
          } else if (selectedRegion === "east_asia" || selectedRegion === "japan") {
            initialLat = 35.6762;
            initialLng = 139.6503;
            initialZoom = 5;
          }
        }

        const map = L.map(mapContainerRef.current, {
          center: [initialLat, initialLng],
          zoom: initialZoom,
          minZoom: 2,
          maxZoom: 19,
          zoomControl: false,
          attributionControl: false,
        });

        // Add Base Tile Layer
        const tileLayer = L.tileLayer(getTileUrl(activeLayer), {
          maxZoom: 19,
          subdomains: "abcd",
        }).addTo(map);
        tileLayerRef.current = tileLayer;

        // Add High-Resolution Reference Labels Layer (Displays State, City, Area, Street names naturally)
        const labelsTileLayer = L.tileLayer(
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
          {
            maxZoom: 19,
            subdomains: "abcd",
            pane: "shadowPane",
          }
        ).addTo(map);
        labelsTileLayerRef.current = labelsTileLayer;

        // Add Initial HQ Pin
        const marker = L.marker([initialLat, initialLng], {
          icon: createFridayTacticalIcon("FRIDAY HQ", "cyan"),
        }).addTo(map);
        activeMarkerRef.current = marker;

        // Load Continent Outer Light Vector Layer with Country Click-To-Zoom
        fetch("/world-continents.json")
          .then((res) => res.json())
          .then((geoData) => {
            if (!mapInstanceRef.current) return;
            const geoLayer = L.geoJSON(geoData, {
              style: {
                color: "rgba(0, 220, 255, 0.75)",
                weight: 1.2,
                opacity: 0.75,
                fill: false,
              },
              onEachFeature: (feature, layer) => {
                const countryName = feature.properties?.name || feature.properties?.ADMIN || "SECTOR";
                layer.bindTooltip(countryName.toUpperCase(), {
                  sticky: true,
                  className: "friday-continent-tooltip",
                });
                layer.on({
                  click: (e: L.LeafletMouseEvent) => {
                    L.DomEvent.stopPropagation(e);
                    const bounds = (layer as any).getBounds ? (layer as any).getBounds() : null;
                    if (bounds) {
                      map.fitBounds(bounds, { maxZoom: 6, animate: true });
                    } else {
                      map.flyTo(e.latlng, 6, { animate: true });
                    }
                    setSelectedLocationName(`${countryName.toUpperCase()} // SECTOR INSPECT`);
                  },
                  mouseover: (e: any) => {
                    const l = e.target;
                    l.setStyle({
                      color: "#00f0ff",
                      weight: 2.0,
                      opacity: 1,
                    });
                  },
                  mouseout: (e: any) => {
                    geoLayer.resetStyle(e.target);
                  },
                });
              },
            }).addTo(mapInstanceRef.current);
          })
          .catch(() => {});

        // Event: Move / Pan / Zoom
        map.on("move", () => {
          const center = map.getCenter();
          setCurrentCoords({ lat: Number(center.lat.toFixed(4)), lng: Number(center.lng.toFixed(4)) });
        });

        map.on("zoomend", () => {
          setCurrentZoom(map.getZoom());
        });

        map.on("mousemove", (e: L.LeafletMouseEvent) => {
          setCursorCoords({ lat: Number(e.latlng.lat.toFixed(4)), lng: Number(e.latlng.lng.toFixed(4)) });
        });

        // Event: Click on map to drop pin or set destination
        map.on("click", (e: L.LeafletMouseEvent) => {
          const { lat, lng } = e.latlng;
          if (activeMarkerRef.current) {
            activeMarkerRef.current.setLatLng([lat, lng]);
          } else {
            activeMarkerRef.current = L.marker([lat, lng], {
              icon: createFridayTacticalIcon("TARGET", "cyan"),
            }).addTo(map);
          }
          setSelectedLocationName(`Grid Ref: ${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`);

          fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
            .then((res) => res.json())
            .then((data) => {
              if (data && data.display_name) {
                setSelectedLocationName(data.display_name);
                if (activeMarkerRef.current) {
                  const shortName = data.address?.suburb || data.address?.neighbourhood || data.address?.city || data.address?.state || "TARGET";
                  activeMarkerRef.current.setIcon(createFridayTacticalIcon(shortName.toUpperCase(), "cyan"));
                }
              }
            })
            .catch(() => {});
        });

        mapInstanceRef.current = map;
      } else {
        mapInstanceRef.current.invalidateSize();
      }
    }, 150);

    return () => {
      clearTimeout(timer);
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isOpen]);

  // Update Tile Layer when layer switch button is clicked
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (tileLayerRef.current) {
      mapInstanceRef.current.removeLayer(tileLayerRef.current);
    }
    const newLayer = L.tileLayer(getTileUrl(activeLayer), {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current = newLayer;
  }, [activeLayer]);

  // Multi-Provider Geocoder (Nominatim -> Photon -> Open-Meteo)
  const geocodeText = async (query: string): Promise<SearchResult[]> => {
    if (!query || !query.trim()) return [];
    const cleanQuery = query.trim();

    // 1. Try Nominatim OpenStreetMap
    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(cleanQuery)}&limit=5&addressdetails=1`,
        { headers: { Accept: "application/json" } }
      );
      if (resp.ok) {
        const data = await resp.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((item: any) => ({
            display_name: item.display_name,
            lat: String(item.lat),
            lon: String(item.lon),
            type: item.type,
          }));
        }
      }
    } catch (e) {
      console.warn("Nominatim search failed, trying fallback:", e);
    }

    // 2. Try Photon Komoot API (High availability, no rate limit)
    try {
      const resp = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(cleanQuery)}&limit=5`);
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.features && data.features.length > 0) {
          return data.features.map((f: any) => {
            const props = f.properties || {};
            const parts = [props.name, props.city, props.state, props.country].filter(Boolean);
            return {
              display_name: parts.join(", ") || props.name || cleanQuery,
              lat: String(f.geometry.coordinates[1]),
              lon: String(f.geometry.coordinates[0]),
              type: props.type || "city",
            };
          });
        }
      }
    } catch (e) {
      console.warn("Photon search failed, trying Open-Meteo:", e);
    }

    // 3. Try Open-Meteo Geocoding
    try {
      const resp = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cleanQuery)}&count=5&language=en&format=json`
      );
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.results && data.results.length > 0) {
          return data.results.map((r: any) => ({
            display_name: [r.name, r.admin1, r.country].filter(Boolean).join(", "),
            lat: String(r.latitude),
            lon: String(r.longitude),
            type: "city",
          }));
        }
      }
    } catch (e) {
      console.warn("All geocoding providers failed:", e);
    }

    return [];
  };

  // Autocomplete Geocoder Search Handler
  const searchLocation = async (
    query: string,
    setResults: React.Dispatch<React.SetStateAction<SearchResult[]>>,
    setSearching: React.Dispatch<React.SetStateAction<boolean>>
  ) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const results = await geocodeText(query);
      setResults(results);
    } catch (err) {
      console.error("Geocoding error:", err);
    } finally {
      setSearching(false);
    }
  };

  // Calculate Great-Circle / Haversine Distance (in km)
  const calculateHaversineDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; // Earth radius in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Number((R * c).toFixed(1));
  };

  // Generate Curved Great-Circle Arc Geometry (for fallback when road routing is unavailable)
  const generateGreatCircleArc = (from: Waypoint, to: Waypoint): [number, number][] => {
    const points: [number, number][] = [];
    const steps = 40;
    for (let i = 0; i <= steps; i++) {
      const f = i / steps;
      const lat = from.lat + (to.lat - from.lat) * f;
      const lng = from.lng + (to.lng - from.lng) * f;
      points.push([lat, lng]);
    }
    return points;
  };

  // Handle Calculate Route / Navigation (From -> To or Destination Only)
  const calculateRoute = async (customFrom?: Waypoint | null, customTo?: Waypoint | null) => {
    if (!mapInstanceRef.current) return;
    setIsCalculatingRoute(true);

    try {
      let from = customFrom !== undefined ? customFrom : fromWaypoint;
      let to = customTo !== undefined ? customTo : toWaypoint;

      // Auto-resolve typed FROM text if waypoint wasn't clicked
      if (!from && fromQuery.trim()) {
        const results = await geocodeText(fromQuery);
        if (results.length > 0) {
          from = {
            lat: parseFloat(results[0].lat),
            lng: parseFloat(results[0].lon),
            name: results[0].display_name,
          };
          setFromWaypoint(from);
          setFromQuery(results[0].display_name.split(",")[0]);
        }
      }

      // Auto-resolve typed TO text if waypoint wasn't clicked
      if (!to && toQuery.trim()) {
        const results = await geocodeText(toQuery);
        if (results.length > 0) {
          to = {
            lat: parseFloat(results[0].lat),
            lng: parseFloat(results[0].lon),
            name: results[0].display_name,
          };
          setToWaypoint(to);
          setToQuery(results[0].display_name.split(",")[0]);
        }
      }

      // Case 1: Only Destination (TO) is provided -> Fly to Destination & Drop Tactical Target
      if (!from && to) {
        flyToLocation(to.lat, to.lng, to.name, 14);
        if (toMarkerRef.current) {
          toMarkerRef.current.setLatLng([to.lat, to.lng]);
          toMarkerRef.current.setIcon(createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"));
        } else {
          toMarkerRef.current = L.marker([to.lat, to.lng], {
            icon: createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"),
          }).addTo(mapInstanceRef.current);
        }
        setRouteInfo(null);
        return;
      }

      // Case 2: Only Origin (FROM) is provided -> Fly to Origin
      if (from && !to) {
        flyToLocation(from.lat, from.lng, from.name, 14);
        if (fromMarkerRef.current) {
          fromMarkerRef.current.setLatLng([from.lat, from.lng]);
          fromMarkerRef.current.setIcon(createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"));
        } else {
          fromMarkerRef.current = L.marker([from.lat, from.lng], {
            icon: createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"),
          }).addTo(mapInstanceRef.current);
        }
        setRouteInfo(null);
        return;
      }

      // Case 3: Both FROM and TO are provided -> Calculate Full Route
      if (from && to) {
        let routeGeoJSON: any = null;
        let distKm = 0;
        let durMins = 0;
        let routeSummary = "Tactical Navigation Corridor";

        // Attempt OSRM driving route
        try {
          const url = `https://router.project-osrm.org/route/v1/driving/${from.lng},${from.lat};${to.lng},${to.lat}?overview=full&geometries=geojson`;
          const resp = await fetch(url);
          if (resp.ok) {
            const data = await resp.json();
            if (data && data.routes && data.routes.length > 0) {
              const route = data.routes[0];
              distKm = Number((route.distance / 1000).toFixed(1));
              durMins = Math.round(route.duration / 60);
              routeSummary = route.legs?.[0]?.summary || "Optimal Highway Corridor";
              routeGeoJSON = route.geometry;
            }
          }
        } catch (osrmErr) {
          console.warn("OSRM routing server unavailable, falling back to tactical vector line:", osrmErr);
        }

        // Fallback to Great Circle Tactical Corridor if OSRM returned no routes or failed
        if (!routeGeoJSON) {
          distKm = calculateHaversineDistance(from.lat, from.lng, to.lat, to.lng);
          // Estimate driving/transit time at ~65 km/h average
          durMins = Math.max(10, Math.round((distKm / 65) * 60));
          routeSummary = "Direct Aerial / Tactical Corridor";
          const arcCoords = generateGreatCircleArc(from, to);
          routeGeoJSON = {
            type: "LineString",
            coordinates: arcCoords.map(([lat, lng]) => [lng, lat]),
          };
        }

        setRouteInfo({
          distanceKm: distKm,
          durationMins: durMins,
          summary: routeSummary,
        });

        // Remove previous route polyline
        if (routeLayerRef.current && mapInstanceRef.current) {
          mapInstanceRef.current.removeLayer(routeLayerRef.current);
        }

        // Add Glowing Cyber Route Polyline
        const routeLayer = L.geoJSON(routeGeoJSON, {
          style: {
            color: "#00f0ff",
            weight: 5,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
            className: "friday-route-polyline",
          },
        }).addTo(mapInstanceRef.current);
        routeLayerRef.current = routeLayer;

        // Place Start & Destination Markers
        if (fromMarkerRef.current) {
          fromMarkerRef.current.setLatLng([from.lat, from.lng]);
          fromMarkerRef.current.setIcon(createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"));
        } else {
          fromMarkerRef.current = L.marker([from.lat, from.lng], {
            icon: createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"),
          }).addTo(mapInstanceRef.current);
        }

        if (toMarkerRef.current) {
          toMarkerRef.current.setLatLng([to.lat, to.lng]);
          toMarkerRef.current.setIcon(createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"));
        } else {
          toMarkerRef.current = L.marker([to.lat, to.lng], {
            icon: createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"),
          }).addTo(mapInstanceRef.current);
        }

        // Smoothly fit map camera bounds to display the whole route
        mapInstanceRef.current.fitBounds(routeLayer.getBounds(), {
          padding: [75, 75],
          animate: true,
          duration: 1.5,
        });

        const hrs = Math.floor(durMins / 60);
        const mins = durMins % 60;
        const timeStr = hrs > 0 ? `${hrs}h ${mins}m` : `${mins} mins`;
        setSelectedLocationName(`Route: ${from.name.split(",")[0]} ➔ ${to.name.split(",")[0]} (${distKm} km • ${timeStr})`);
      }
    } catch (err) {
      console.error("Route calculation error:", err);
    } finally {
      setIsCalculatingRoute(false);
    }
  };

  // Clear Active Route
  const clearRoute = () => {
    if (routeLayerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    if (fromMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(fromMarkerRef.current);
      fromMarkerRef.current = null;
    }
    if (toMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(toMarkerRef.current);
      toMarkerRef.current = null;
    }
    setFromWaypoint(null);
    setToWaypoint(null);
    setFromQuery("");
    setToQuery("");
    setRouteInfo(null);
  };

  // Swap From and To
  const swapRoute = () => {
    const tempQ = fromQuery;
    const tempW = fromWaypoint;
    setFromQuery(toQuery);
    setFromWaypoint(toWaypoint);
    setToQuery(tempQ);
    setToWaypoint(tempW);
    if (toWaypoint || tempW) {
      calculateRoute(toWaypoint, tempW);
    }
  };

  // Fly to target coordinate
  const flyToLocation = (lat: number, lng: number, name: string, zoomLevel: number = 13) => {
    if (!mapInstanceRef.current) return;
    setSelectedLocationName(name);
    mapInstanceRef.current.flyTo([lat, lng], zoomLevel, {
      animate: true,
      duration: 1.5,
    });

    if (activeMarkerRef.current) {
      activeMarkerRef.current.setLatLng([lat, lng]);
      const shortName = name.split(",")[0].trim();
      activeMarkerRef.current.setIcon(createFridayTacticalIcon(shortName.toUpperCase(), "cyan"));
    } else {
      activeMarkerRef.current = L.marker([lat, lng], {
        icon: createFridayTacticalIcon(name.split(",")[0].trim().toUpperCase(), "cyan"),
      }).addTo(mapInstanceRef.current);
    }
  };

  // Zoom Controls
  const handleZoomIn = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
  };

  const handleResetIndia = () => {
    flyToLocation(20.5937, 78.9629, "India National Command Hub", 5);
  };

  const handleResetWorld = () => {
    flyToLocation(20, 0, "Global Friday Planetary Mesh", 2);
  };

  // Automated search trigger prop watcher
  useEffect(() => {
    if (!searchTrigger || !searchTrigger.trim()) return;
    const cleanSearch = searchTrigger.trim();
    geocodeText(cleanSearch).then((results) => {
      if (results && results.length > 0) {
        const top = results[0];
        const lat = parseFloat(top.lat);
        const lng = parseFloat(top.lon);
        if (!isNaN(lat) && !isNaN(lng)) {
          flyToLocation(lat, lng, top.display_name, 13);
        }
      }
    });
  }, [searchTrigger]);

  // Automated route trigger prop watcher
  useEffect(() => {
    if (!routeTrigger || !routeTrigger.from || !routeTrigger.to) return;
    setIsRouteMode(true);
    setFromQuery(routeTrigger.from);
    setToQuery(routeTrigger.to);

    Promise.all([geocodeText(routeTrigger.from), geocodeText(routeTrigger.to)]).then(([fromRes, toRes]) => {
      let fromWp: Waypoint | null = null;
      let toWp: Waypoint | null = null;
      if (fromRes && fromRes.length > 0) {
        fromWp = {
          lat: parseFloat(fromRes[0].lat),
          lng: parseFloat(fromRes[0].lon),
          name: fromRes[0].display_name,
        };
        setFromWaypoint(fromWp);
      }
      if (toRes && toRes.length > 0) {
        toWp = {
          lat: parseFloat(toRes[0].lat),
          lng: parseFloat(toRes[0].lon),
          name: toRes[0].display_name,
        };
        setToWaypoint(toWp);
      }
      if (fromWp && toWp) {
        calculateRoute(fromWp, toWp);
      }
    });
  }, [routeTrigger]);

  if (!isOpen && !isEmbedded) return null;

  const content = (
    <>
      <style>{`
        @keyframes pulseRing {
          0% { transform: scale(0.6); opacity: 1; }
          100% { transform: scale(1.8); opacity: 0; }
        }
        @keyframes rotateArc {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .leaflet-container {
          background: #000000 !important;
          font-family: 'Share Tech Mono', 'Orbitron', monospace !important;
          outline: none !important;
        }
        /* Completely Remove Browser Focus/Click White Outlines */
        .leaflet-container:focus,
        .leaflet-container:focus-visible,
        .leaflet-container:active,
        .leaflet-pane,
        .leaflet-pane:focus,
        .leaflet-overlay-pane,
        .leaflet-overlay-pane svg,
        .leaflet-overlay-pane svg:focus,
        .leaflet-overlay-pane svg:focus-visible,
        .leaflet-overlay-pane path,
        .leaflet-overlay-pane path:focus,
        .leaflet-overlay-pane path:focus-visible,
        .leaflet-interactive,
        .leaflet-interactive:focus,
        .leaflet-interactive:focus-visible,
        .leaflet-interactive:active,
        .leaflet-marker-icon,
        .leaflet-marker-icon:focus,
        .leaflet-marker-icon:focus-visible,
        .friday-map-viewport,
        .friday-map-viewport:focus,
        .friday-map-viewport:focus-visible {
          outline: none !important;
          box-shadow: none !important;
          -webkit-tap-highlight-color: transparent !important;
        }
        /* Pure Blue & Black High-Contrast Tactical Cartography Filters */
        .friday-map-viewport .leaflet-tile-pane {
          filter: ${
            activeLayer === "friday_cyber"
              ? "brightness(0.88) contrast(1.65) sepia(100%) hue-rotate(185deg) saturate(650%)"
              : activeLayer === "satellite"
              ? "brightness(0.82) contrast(1.55) sepia(100%) hue-rotate(190deg) saturate(420%)"
              : "invert(100%) sepia(100%) hue-rotate(185deg) saturate(750%) brightness(1.08) contrast(1.75)"
          };
          transition: filter 0.3s ease;
        }
        /* Blueprint CAD Matrix Grid Overlay (Only in Street Blueprint mode) */
        ${
          activeLayer === "street"
            ? `
        .friday-map-viewport::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          z-index: 2;
          background-image: 
            linear-gradient(rgba(0, 240, 255, 0.045) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 240, 255, 0.045) 1px, transparent 1px);
          background-size: 32px 32px;
        }
        `
            : ""
        }
        /* Reference Labels Pane (Street & City Text Glowing in Laser Cyan) */
        .friday-map-viewport .leaflet-shadow-pane {
          filter: brightness(1.25) contrast(1.45) sepia(100%) hue-rotate(185deg) saturate(650%) !important;
        }
        /* Glowing Route Line */
        .friday-route-polyline {
          filter: drop-shadow(0 0 8px #00f0ff) drop-shadow(0 0 16px rgba(0, 240, 255, 0.8)) !important;
        }
        /* Subtle Outer Light of the Continents Only */
        .leaflet-overlay-pane svg path:not(.friday-route-polyline) {
          stroke: rgba(0, 220, 255, 0.75) !important;
          stroke-linecap: round;
          stroke-linejoin: round;
          filter: drop-shadow(0 0 2.5px rgba(0, 240, 255, 0.45)) !important;
          pointer-events: auto;
          transition: stroke 0.2s ease, filter 0.2s ease;
        }
        .friday-continent-tooltip {
          background: rgba(1, 4, 9, 0.95) !important;
          border: 1px solid rgba(0, 240, 255, 0.6) !important;
          color: #00f0ff !important;
          font-family: 'Orbitron', monospace !important;
          font-size: 10px !important;
          font-weight: bold !important;
          letter-spacing: 1px !important;
          border-radius: 4px !important;
          box-shadow: 0 0 8px rgba(0, 240, 255, 0.3) !important;
          padding: 3px 8px !important;
        }
        .friday-continent-tooltip::before {
          border-top-color: rgba(0, 240, 255, 0.6) !important;
        }
      `}</style>

      <div
        className="jarvis-glass-card"
        style={{
          width: isEmbedded ? "100%" : "95vw",
          maxWidth: isEmbedded ? "100%" : "1420px",
          height: isEmbedded ? "100%" : "90vh",
          maxHeight: isEmbedded ? "100%" : "920px",
          background: "radial-gradient(circle at 50% 30%, #030f24 0%, #000000 85%)",
          border: "1.5px solid rgba(0, 240, 255, 0.6)",
          borderRadius: "10px",
          boxShadow: "0 0 24px rgba(0, 240, 255, 0.25), inset 0 0 15px rgba(0, 240, 255, 0.08)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          position: "relative",
          flex: 1,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* HUD Corner Reticle Brackets */}
        <div style={{ position: "absolute", top: "6px", left: "6px", width: "16px", height: "16px", borderTop: "2px solid #00f0ff", borderLeft: "2px solid #00f0ff", pointerEvents: "none", zIndex: 20 }} />
        <div style={{ position: "absolute", top: "6px", right: "6px", width: "16px", height: "16px", borderTop: "2px solid #00f0ff", borderRight: "2px solid #00f0ff", pointerEvents: "none", zIndex: 20 }} />
        <div style={{ position: "absolute", bottom: "6px", left: "6px", width: "16px", height: "16px", borderBottom: "2px solid #00f0ff", borderLeft: "2px solid #00f0ff", pointerEvents: "none", zIndex: 20 }} />
        <div style={{ position: "absolute", bottom: "6px", right: "6px", width: "16px", height: "16px", borderBottom: "2px solid #00f0ff", borderRight: "2px solid #00f0ff", pointerEvents: "none", zIndex: 20 }} />

        {/* Top Header Bar (Row 1: Brand, Mode Switch, Layer Selectors, Radar, Exit) */}
        <div
          style={{
            minHeight: "52px",
            borderBottom: "1px solid rgba(0, 240, 255, 0.3)",
            padding: "8px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(0, 8, 20, 0.92)",
            gap: "12px",
            zIndex: 10,
            flexWrap: "wrap",
          }}
        >
          {/* Friday Logo & Title */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: "rgba(0, 240, 255, 0.18)",
                border: "1.5px solid #00f0ff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 12px #00f0ff",
                color: "#00f0ff",
                fontSize: "12px",
                fontWeight: "900",
              }}
            >
              ▲
            </div>
            <div>
              <div
                style={{
                  fontFamily: "'Orbitron', sans-serif",
                  fontSize: "13px",
                  fontWeight: "900",
                  color: "#00f0ff",
                  letterSpacing: "1.5px",
                  textShadow: "0 0 10px rgba(0, 240, 255, 0.8)",
                }}
              >
                {regionTitle.toUpperCase()}
              </div>
              <div style={{ fontSize: "9px", color: "var(--jarvis-muted, #8ab4f8)", letterSpacing: "1px" }}>
                GEOSPATIAL TACTICAL ROUTER // v3.2.0
              </div>
            </div>
          </div>

          {/* Mode Tabs: Single Location vs Dual FROM / TO Route Planner */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(0, 240, 255, 0.08)", padding: "3px", borderRadius: "6px", border: "1px solid rgba(0, 240, 255, 0.25)" }}>
            <button
              onClick={() => setIsRouteMode(false)}
              style={{
                background: !isRouteMode ? "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.2))" : "transparent",
                border: !isRouteMode ? "1px solid #00f0ff" : "1px solid transparent",
                color: !isRouteMode ? "#00f0ff" : "#8ab4f8",
                borderRadius: "4px",
                padding: "6px 14px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                boxShadow: !isRouteMode ? "0 0 10px rgba(0, 240, 255, 0.3)" : "none",
                letterSpacing: "0.5px",
              }}
            >
              🔍 SINGLE SEARCH
            </button>
            <button
              onClick={() => setIsRouteMode(true)}
              style={{
                background: isRouteMode ? "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.3))" : "transparent",
                border: isRouteMode ? "1.5px solid #00f0ff" : "1px solid transparent",
                color: isRouteMode ? "#00f0ff" : "#8ab4f8",
                borderRadius: "4px",
                padding: "6px 14px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                boxShadow: isRouteMode ? "0 0 14px rgba(0, 240, 255, 0.4)" : "none",
                letterSpacing: "0.5px",
              }}
            >
              ⚡ FROM / TO ROUTE PLANNER
            </button>
          </div>

          {/* Layer Selector, Radar & Close Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", background: "rgba(0, 240, 255, 0.08)", borderRadius: "6px", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "2px" }}>
              <button
                onClick={() => setActiveLayer("friday_cyber")}
                style={{
                  background: activeLayer === "friday_cyber" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.4), rgba(0, 119, 255, 0.25))" : "transparent",
                  color: activeLayer === "friday_cyber" ? "#00f0ff" : "#8ab4f8",
                  border: activeLayer === "friday_cyber" ? "1px solid #00f0ff" : "1px solid transparent",
                  borderRadius: "4px",
                  padding: "5px 10px",
                  fontSize: "10px",
                  fontWeight: "bold",
                  cursor: "pointer",
                }}
              >
                ⚡ NEURAL GRID
              </button>
              <button
                onClick={() => setActiveLayer("satellite")}
                style={{
                  background: activeLayer === "satellite" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.4), rgba(0, 119, 255, 0.25))" : "transparent",
                  color: activeLayer === "satellite" ? "#00f0ff" : "#8ab4f8",
                  border: activeLayer === "satellite" ? "1px solid #00f0ff" : "1px solid transparent",
                  borderRadius: "4px",
                  padding: "5px 10px",
                  fontSize: "10px",
                  fontWeight: "bold",
                  cursor: "pointer",
                }}
              >
                🛰️ ORBITAL SAT
              </button>
              <button
                onClick={() => setActiveLayer("street")}
                style={{
                  background: activeLayer === "street" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.3))" : "transparent",
                  color: activeLayer === "street" ? "#00f0ff" : "#8ab4f8",
                  border: activeLayer === "street" ? "1px solid #00f0ff" : "1px solid transparent",
                  borderRadius: "4px",
                  padding: "5px 10px",
                  fontSize: "10px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  boxShadow: activeLayer === "street" ? "0 0 10px rgba(0, 240, 255, 0.4)" : "none",
                }}
              >
                🗺️ STREET BLUEPRINT
              </button>
            </div>

            {/* Radar Sweep Toggle */}
            <button
              onClick={() => setIsRadarSweeping((prev) => !prev)}
              style={{
                background: isRadarSweeping ? "rgba(52, 211, 153, 0.2)" : "rgba(100, 116, 139, 0.2)",
                border: `1px solid ${isRadarSweeping ? "#34d399" : "#64748b"}`,
                color: isRadarSweeping ? "#34d399" : "#94a3b8",
                borderRadius: "5px",
                padding: "5px 10px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
              }}
              title="Toggle Tactical Radar Ray"
            >
              {isRadarSweeping ? "📡 RADAR ON" : "⏸️ RADAR OFF"}
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              style={{
                background: "rgba(239, 68, 68, 0.2)",
                border: "1px solid #f87171",
                color: "#f87171",
                borderRadius: "5px",
                padding: "5px 12px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
                letterSpacing: "1px",
              }}
            >
              ✕ DISENGAGE
            </button>
          </div>
        </div>

        {/* Dedicated Navigation Command Bar (Row 2: Large Spacious Search & FROM/TO Inputs) */}
        <div
          style={{
            background: "rgba(1, 6, 15, 0.95)",
            borderBottom: "1.5px solid rgba(0, 240, 255, 0.35)",
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            zIndex: 10,
            flexWrap: "wrap",
            boxShadow: "0 4px 20px rgba(0, 0, 0, 0.6)",
          }}
        >
          {!isRouteMode ? (
            /* Spacious Single Target Search Bar */
            <form
              onSubmit={(e) => {
                e.preventDefault();
                searchLocation(toQuery, setToResults, setIsSearchingTo);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                flex: "1 1 450px",
                maxWidth: "650px",
                background: "#010712",
                border: "1.5px solid rgba(0, 240, 255, 0.6)",
                borderRadius: "8px",
                padding: "3px 12px",
                boxShadow: "inset 0 0 14px rgba(0, 240, 255, 0.18), 0 0 15px rgba(0, 240, 255, 0.15)",
                position: "relative",
                minHeight: "42px",
              }}
            >
              <span style={{ color: "#00f0ff", fontSize: "16px", marginRight: "10px" }}>⌕</span>
              <input
                type="text"
                placeholder="Search any Country, State, City, Landmark, or Street..."
                value={toQuery}
                onChange={(e) => {
                  setToQuery(e.target.value);
                  searchLocation(e.target.value, setToResults, setIsSearchingTo);
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#ffffff",
                  fontSize: "13px",
                  outline: "none",
                  width: "100%",
                  padding: "8px 0",
                  fontFamily: "'Share Tech Mono', monospace",
                  letterSpacing: "0.5px",
                }}
              />
              {toQuery && (
                <button
                  type="button"
                  onClick={() => setToQuery("")}
                  style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px", marginRight: "8px" }}
                >
                  ✕
                </button>
              )}
              <button
                type="submit"
                disabled={isSearchingTo}
                style={{
                  background: "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.3))",
                  border: "1px solid var(--jarvis-cyan, #00f0ff)",
                  color: "#00f0ff",
                  borderRadius: "5px",
                  padding: "7px 16px",
                  fontSize: "11.5px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 0 10px rgba(0, 240, 255, 0.3)",
                }}
              >
                {isSearchingTo ? "SCANNING..." : "LOCATE TARGET"}
              </button>

              {/* Single Search Results Dropdown */}
              {toResults.length > 0 && (
                <div
                  style={{
                    position: "absolute",
                    top: "100%",
                    left: 0,
                    right: 0,
                    marginTop: "6px",
                    background: "rgba(1, 4, 9, 0.98)",
                    border: "1.5px solid var(--jarvis-cyan, #00f0ff)",
                    borderRadius: "8px",
                    boxShadow: "0 0 30px rgba(0, 240, 255, 0.6)",
                    zIndex: 99999,
                    maxHeight: "240px",
                    overflowY: "auto",
                  }}
                >
                  {toResults.map((res, idx) => (
                    <div
                      key={idx}
                      onClick={() => {
                        const wp: Waypoint = { lat: parseFloat(res.lat), lng: parseFloat(res.lon), name: res.display_name };
                        setToWaypoint(wp);
                        setToQuery(res.display_name);
                        setToResults([]);
                        flyToLocation(wp.lat, wp.lng, wp.name, 14);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderBottom: "1px solid rgba(0, 240, 255, 0.15)",
                        fontSize: "12px",
                        color: "#e2e8f0",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 240, 255, 0.25)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <span style={{ color: "#00f0ff" }}>📍</span>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {res.display_name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </form>
          ) : (
            /* Large, Spacious FROM / TO Route Planner Form */
            <form
              onSubmit={(e) => {
                e.preventDefault();
                calculateRoute();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                flex: "1 1 650px",
                flexWrap: "wrap",
              }}
            >
              {/* FROM Input Box (Large & Wide) */}
              <div style={{ position: "relative", flex: "1 1 240px", minWidth: "220px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    background: "#010712",
                    border: "1.5px solid rgba(52, 211, 153, 0.8)",
                    borderRadius: "8px",
                    padding: "0 12px",
                    minHeight: "42px",
                    boxShadow: "0 0 12px rgba(52, 211, 153, 0.2), inset 0 0 10px rgba(52, 211, 153, 0.1)",
                  }}
                >
                  <span
                    style={{
                      color: isSearchingFrom ? "#fbbf24" : "#34d399",
                      fontSize: "11px",
                      fontWeight: "900",
                      letterSpacing: "1px",
                      marginRight: "8px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {isSearchingFrom ? "SCAN..." : "🟢 FROM:"}
                  </span>
                  <input
                    type="text"
                    placeholder="Origin (e.g. Chennai, Mumbai, HQ)..."
                    value={fromQuery}
                    onChange={(e) => {
                      setFromQuery(e.target.value);
                      searchLocation(e.target.value, setFromResults, setIsSearchingFrom);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        calculateRoute();
                      }
                    }}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#ffffff",
                      fontSize: "12.5px",
                      outline: "none",
                      width: "100%",
                      padding: "8px 0",
                      fontFamily: "'Share Tech Mono', monospace",
                    }}
                  />
                  {fromQuery && (
                    <button
                      type="button"
                      onClick={() => setFromQuery("")}
                      style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px", padding: "4px" }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* FROM Autocomplete Dropdown */}
                {fromResults.length > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      right: 0,
                      marginTop: "6px",
                      background: "rgba(1, 4, 9, 0.98)",
                      border: "1.5px solid #34d399",
                      borderRadius: "8px",
                      boxShadow: "0 0 25px rgba(52, 211, 153, 0.6)",
                      zIndex: 99999,
                      maxHeight: "220px",
                      overflowY: "auto",
                    }}
                  >
                    {fromResults.map((res, idx) => (
                      <div
                        key={idx}
                        onClick={() => {
                          const wp: Waypoint = { lat: parseFloat(res.lat), lng: parseFloat(res.lon), name: res.display_name };
                          setFromWaypoint(wp);
                          setFromQuery(res.display_name.split(",")[0]);
                          setFromResults([]);
                          if (toWaypoint) calculateRoute(wp, toWaypoint);
                        }}
                        style={{
                          padding: "9px 12px",
                          borderBottom: "1px solid rgba(52, 211, 153, 0.2)",
                          fontSize: "11.5px",
                          color: "#e2e8f0",
                          cursor: "pointer",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(52, 211, 153, 0.25)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        🟢 {res.display_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Swap Button */}
              <button
                type="button"
                onClick={swapRoute}
                style={{
                  background: "rgba(0, 240, 255, 0.18)",
                  border: "1.5px solid rgba(0, 240, 255, 0.5)",
                  color: "#00f0ff",
                  borderRadius: "6px",
                  width: "38px",
                  height: "38px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: "bold",
                  flexShrink: 0,
                }}
                title="Swap Origin and Destination"
              >
                ⇄
              </button>

              {/* TO Input Box (Large & Wide) */}
              <div style={{ position: "relative", flex: "1 1 240px", minWidth: "220px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    background: "#010712",
                    border: "1.5px solid rgba(248, 113, 113, 0.8)",
                    borderRadius: "8px",
                    padding: "0 12px",
                    minHeight: "42px",
                    boxShadow: "0 0 12px rgba(248, 113, 113, 0.2), inset 0 0 10px rgba(248, 113, 113, 0.1)",
                  }}
                >
                  <span
                    style={{
                      color: isSearchingTo ? "#fbbf24" : "#f87171",
                      fontSize: "11px",
                      fontWeight: "900",
                      letterSpacing: "1px",
                      marginRight: "8px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {isSearchingTo ? "SCAN..." : "🔴 TO:"}
                  </span>
                  <input
                    type="text"
                    placeholder="Destination (e.g. Bengaluru, Pune, Airport)..."
                    value={toQuery}
                    onChange={(e) => {
                      setToQuery(e.target.value);
                      searchLocation(e.target.value, setToResults, setIsSearchingTo);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        calculateRoute();
                      }
                    }}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#ffffff",
                      fontSize: "12.5px",
                      outline: "none",
                      width: "100%",
                      padding: "8px 0",
                      fontFamily: "'Share Tech Mono', monospace",
                    }}
                  />
                  {toQuery && (
                    <button
                      type="button"
                      onClick={() => setToQuery("")}
                      style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px", padding: "4px" }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* TO Autocomplete Dropdown */}
                {toResults.length > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      right: 0,
                      marginTop: "6px",
                      background: "rgba(1, 4, 9, 0.98)",
                      border: "1.5px solid #f87171",
                      borderRadius: "8px",
                      boxShadow: "0 0 25px rgba(248, 113, 113, 0.6)",
                      zIndex: 99999,
                      maxHeight: "220px",
                      overflowY: "auto",
                    }}
                  >
                    {toResults.map((res, idx) => (
                      <div
                        key={idx}
                        onClick={() => {
                          const wp: Waypoint = { lat: parseFloat(res.lat), lng: parseFloat(res.lon), name: res.display_name };
                          setToWaypoint(wp);
                          setToQuery(res.display_name.split(",")[0]);
                          setToResults([]);
                          if (fromWaypoint) {
                            calculateRoute(fromWaypoint, wp);
                          } else {
                            calculateRoute(null, wp);
                          }
                        }}
                        style={{
                          padding: "9px 12px",
                          borderBottom: "1px solid rgba(248, 113, 113, 0.2)",
                          fontSize: "11.5px",
                          color: "#e2e8f0",
                          cursor: "pointer",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(248, 113, 113, 0.25)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        🔴 {res.display_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Calculate / Route Action Button (Large & Prominent) */}
              <button
                type="submit"
                disabled={isCalculatingRoute || (!fromQuery.trim() && !toQuery.trim())}
                style={{
                  background: "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.35))",
                  border: "1.5px solid #00f0ff",
                  color: "#00f0ff",
                  borderRadius: "6px",
                  padding: "0 18px",
                  minHeight: "42px",
                  fontSize: "11.5px",
                  fontWeight: "900",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 0 15px rgba(0, 240, 255, 0.4)",
                  letterSpacing: "0.5px",
                  flexShrink: 0,
                }}
              >
                {isCalculatingRoute ? "CALCULATING..." : "⚡ CALCULATE ROUTE"}
              </button>

              {/* Clear Route Button */}
              {(routeInfo || fromWaypoint || toWaypoint || fromQuery || toQuery) && (
                <button
                  type="button"
                  onClick={clearRoute}
                  style={{
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1.5px solid #f87171",
                    color: "#f87171",
                    borderRadius: "6px",
                    padding: "0 12px",
                    minHeight: "42px",
                    fontSize: "11px",
                    fontWeight: "bold",
                    cursor: "pointer",
                    flexShrink: 0,
                  }}
                  title="Clear Active Route"
                >
                  ✕ CLEAR
                </button>
              )}
            </form>
          )}

          {/* Quick Route Shortcuts & Jump Buttons */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "9.5px", color: "var(--jarvis-cyan, #00f0ff)", fontWeight: "bold", letterSpacing: "1px" }}>
              QUICK HUBS:
            </span>

            <button
              onClick={() => {
                const f: Waypoint = { lat: 13.0827, lng: 80.2707, name: "Chennai" };
                const t: Waypoint = { lat: 12.9716, lng: 77.5946, name: "Bengaluru" };
                setIsRouteMode(true);
                setFromQuery("Chennai");
                setToQuery("Bengaluru");
                setFromWaypoint(f);
                setToWaypoint(t);
                calculateRoute(f, t);
              }}
              style={{
                background: "rgba(0, 25, 50, 0.8)",
                border: "1px solid rgba(0, 240, 255, 0.4)",
                color: "#00f0ff",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
              }}
            >
              Chennai ➔ BLR
            </button>

            <button
              onClick={() => {
                const f: Waypoint = { lat: 19.0760, lng: 72.8777, name: "Mumbai" };
                const t: Waypoint = { lat: 18.5204, lng: 73.8567, name: "Pune" };
                setIsRouteMode(true);
                setFromQuery("Mumbai");
                setToQuery("Pune");
                setFromWaypoint(f);
                setToWaypoint(t);
                calculateRoute(f, t);
              }}
              style={{
                background: "rgba(0, 25, 50, 0.8)",
                border: "1px solid rgba(0, 240, 255, 0.4)",
                color: "#00f0ff",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
              }}
            >
              Mumbai ➔ Pune
            </button>

            <button
              onClick={handleResetIndia}
              style={{
                background: "rgba(0, 20, 40, 0.7)",
                border: "1px solid rgba(0, 240, 255, 0.3)",
                color: "#38bdf8",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "10px",
                cursor: "pointer",
              }}
            >
              🇮🇳 India
            </button>

            <button
              onClick={handleResetWorld}
              style={{
                background: "rgba(0, 20, 40, 0.7)",
                border: "1px solid rgba(0, 240, 255, 0.3)",
                color: "#38bdf8",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "10px",
                cursor: "pointer",
              }}
            >
              🌍 World
            </button>
          </div>
        </div>

        {/* Dynamic Route Telemetry Corridor Strip (Displays when route is computed) */}
        {routeInfo && (
          <div
            style={{
              background: "linear-gradient(90deg, rgba(0, 30, 60, 0.95), rgba(0, 15, 35, 0.95))",
              borderBottom: "1.5px solid #00f0ff",
              padding: "7px 20px",
              display: "flex",
              alignItems: "center",
              gap: "16px",
              overflowX: "auto",
              whiteSpace: "nowrap",
              zIndex: 10,
              fontSize: "11.5px",
              color: "#00f0ff",
              boxShadow: "0 0 15px rgba(0, 240, 255, 0.25)",
            }}
          >
            <div>
              <strong style={{ color: "#34d399" }}>🟢 ORIGIN:</strong> {fromWaypoint?.name.split(",")[0] || fromQuery}
            </div>
            <div style={{ color: "#00f0ff", fontWeight: "bold" }}>➔</div>
            <div>
              <strong style={{ color: "#f87171" }}>🔴 DESTINATION:</strong> {toWaypoint?.name.split(",")[0] || toQuery}
            </div>
            <div style={{ background: "rgba(0, 240, 255, 0.2)", padding: "3px 10px", borderRadius: "5px", border: "1px solid rgba(0, 240, 255, 0.5)" }}>
              📏 <strong>DISTANCE:</strong> {routeInfo.distanceKm} km
            </div>
            <div style={{ background: "rgba(0, 240, 255, 0.2)", padding: "3px 10px", borderRadius: "5px", border: "1px solid rgba(0, 240, 255, 0.5)" }}>
              ⏱️ <strong>ESTIMATED TIME:</strong> {Math.floor(routeInfo.durationMins / 60)}h {routeInfo.durationMins % 60}m
            </div>
            <div style={{ color: "#8ab4f8", fontSize: "10.5px" }}>
              TACTICAL DRIVING CORRIDOR ACTIVE
            </div>
          </div>
        )}

        {/* Main Map Viewport & Interactive Layer */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          
          {/* Leaflet Map Container */}
          <div
            ref={mapContainerRef}
            className="friday-map-viewport"
            style={{ width: "100%", height: "100%", zIndex: 1 }}
          />

          {/* Futuristic Friday Tactical Overlay: Concentric Targeting Reticles & Radar Ray */}
          {isRadarSweeping && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                zIndex: 2,
                overflow: "hidden",
              }}
            >
              <svg width="100%" height="100%">
                {/* Center Tactical Reticle */}
                <circle cx="50%" cy="50%" r="45" fill="none" stroke="rgba(0, 240, 255, 0.35)" strokeWidth="1.2" strokeDasharray="4 4" />
                <circle cx="50%" cy="50%" r="160" fill="none" stroke="rgba(0, 240, 255, 0.18)" strokeWidth="0.8" strokeDasharray="6 8" />
                <circle cx="50%" cy="50%" r="300" fill="none" stroke="rgba(0, 240, 255, 0.1)" strokeWidth="0.6" />
                
                {/* Crosshair Axes */}
                <line x1="0" y1="50%" x2="100%" y2="50%" stroke="rgba(0, 240, 255, 0.12)" strokeWidth="0.8" />
                <line x1="50%" y1="0" x2="50%" y2="100%" stroke="rgba(0, 240, 255, 0.12)" strokeWidth="0.8" />

                {/* Radar Rotating Ray */}
                <g transform="translate(700, 360)">
                  <line
                    x1="0"
                    y1="0"
                    x2={450 * Math.cos((radarAngle * Math.PI) / 180)}
                    y2={450 * Math.sin((radarAngle * Math.PI) / 180)}
                    stroke="rgba(0, 240, 255, 0.55)"
                    strokeWidth="1.8"
                    style={{ filter: "drop-shadow(0 0 8px #00f0ff)" }}
                  />
                  <polygon
                    points={`0,0 ${450 * Math.cos(((radarAngle - 20) * Math.PI) / 180)},${450 * Math.sin(((radarAngle - 20) * Math.PI) / 180)} ${450 * Math.cos((radarAngle * Math.PI) / 180)},${450 * Math.sin((radarAngle * Math.PI) / 180)}`}
                    fill="rgba(0, 240, 255, 0.08)"
                  />
                </g>
              </svg>
            </div>
          )}

          {/* Floating Top-Left Friday Target Inspector HUD Badge */}
          <div
            className="jarvis-glass-card"
            style={{
              position: "absolute",
              top: "16px",
              left: "16px",
              zIndex: 10,
              padding: "10px 16px",
              color: "#fff",
              border: "1px solid rgba(0, 240, 255, 0.6)",
              boxShadow: "0 0 20px rgba(0, 240, 255, 0.35)",
              maxWidth: "440px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: routeInfo ? "#00f0ff" : "#34d399", boxShadow: `0 0 8px ${routeInfo ? "#00f0ff" : "#34d399"}` }} />
              <div style={{ fontSize: "9.5px", color: "var(--jarvis-cyan, #00f0ff)", fontWeight: "bold", letterSpacing: "1.5px" }}>
                {routeInfo ? "ACTIVE NAVIGATION CORRIDOR" : `TACTICAL SECTOR // ${currentZoom <= 7 ? "STATE LAYER" : currentZoom <= 12 ? "CITY LAYER" : "STREET PRECISION"}`}
              </div>
            </div>
            <div
              style={{
                fontSize: "13px",
                fontWeight: "bold",
                color: "#ffffff",
                marginTop: "4px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                letterSpacing: "0.5px",
              }}
            >
              {selectedLocationName}
            </div>
            <div style={{ fontSize: "10px", color: "var(--jarvis-muted, #8ab4f8)", marginTop: "4px", display: "flex", gap: "12px" }}>
              <span>LAT: {currentCoords.lat}°</span>
              <span>LNG: {currentCoords.lng}°</span>
              <span style={{ color: "#00f0ff", fontWeight: "bold" }}>ZOOM: {currentZoom}x</span>
            </div>
          </div>

          {/* Floating Right Tactical Zoom & Scale Controls */}
          <div
            style={{
              position: "absolute",
              bottom: "24px",
              right: "20px",
              zIndex: 10,
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <button
              onClick={handleZoomIn}
              className="jarvis-glass-card"
              style={{
                width: "36px",
                height: "36px",
                color: "#00f0ff",
                fontSize: "18px",
                fontWeight: "bold",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid rgba(0, 240, 255, 0.6)",
                boxShadow: "0 0 12px rgba(0, 240, 255, 0.35)",
              }}
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={handleZoomOut}
              className="jarvis-glass-card"
              style={{
                width: "36px",
                height: "36px",
                color: "#00f0ff",
                fontSize: "18px",
                fontWeight: "bold",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid rgba(0, 240, 255, 0.6)",
                boxShadow: "0 0 12px rgba(0, 240, 255, 0.35)",
              }}
              title="Zoom Out"
            >
              -
            </button>
          </div>

          {/* Floating Bottom Friday Telemetry HUD Bar */}
          <div
            className="jarvis-glass-card"
            style={{
              position: "absolute",
              bottom: "16px",
              left: "20px",
              zIndex: 10,
              padding: "6px 16px",
              fontSize: "10.5px",
              color: "var(--jarvis-cyan, #00f0ff)",
              display: "flex",
              gap: "18px",
              border: "1px solid rgba(0, 240, 255, 0.4)",
              boxShadow: "0 0 15px rgba(0, 240, 255, 0.25)",
            }}
          >
            <div>
              <span style={{ color: "#94a3b8" }}>CURSOR:</span> {cursorCoords ? `${cursorCoords.lat}° N, ${cursorCoords.lng}° E` : "---"}
            </div>
            <div>
              <span style={{ color: "#94a3b8" }}>CENTER:</span> {currentCoords.lat}°, {currentCoords.lng}°
            </div>
            <div>
              <span style={{ color: "#94a3b8" }}>STATUS:</span>{" "}
              <strong style={{ color: routeInfo ? "#00f0ff" : "#38bdf8" }}>
                {routeInfo ? `Navigation Active (${routeInfo.distanceKm} km)` : "Tactical Scanning"}
              </strong>
            </div>
            <div style={{ color: "#34d399", fontWeight: "bold" }}>
              ● FRIDAY GEOSPATIAL ROUTER ACTIVE
            </div>
          </div>

        </div>
      </div>
    </>
  );

  if (isEmbedded) {
    return (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
        {content}
      </div>
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(1, 4, 9, 0.94)",
        backdropFilter: "blur(20px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        userSelect: "none",
        animation: "fadeIn 0.25s ease-out",
      }}
      onClick={onClose}
    >
      {content}
    </div>
  );
};
