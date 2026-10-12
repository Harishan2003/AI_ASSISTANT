import React, { useState, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { HoloGlobe3D } from "./HoloGlobe3D";

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

export interface Waypoint {
  lat: number;
  lng: number;
  name: string;
}

export interface IntermediateStop {
  id: string;
  query: string;
  waypoint: Waypoint | null;
  results: SearchResult[];
  isSearching: boolean;
}

export interface RouteOption {
  id: string;
  name: string;
  distanceKm: number;
  durationMins: number;
  summary: string;
  geojson: any;
  color: string;
  type: "primary" | "alternative" | "tactical";
}

interface RouteInfo {
  distanceKm: number;
  durationMins: number;
  summary?: string;
}

export type MapLayerType =
  | "friday_hud"
  | "google_sat"
  | "google_hybrid"
  | "google_terrain"
  | "friday_cyber"
  | "osm_blueprint";

export type FridayThemeVariant = "night" | "cyan" | "stealth" | "gold" | "emerald" | "neon" | "abyss" | "natural";

export interface FridayThemeConfig {
  id: FridayThemeVariant;
  name: string;
  icon: string;
  primary: string;
  accent: string;
  bg: string;
  glow: string;
}

export const FRIDAY_THEME_OPTIONS: FridayThemeConfig[] = [
  { id: "cyan", name: "FRIDAY HUD", icon: "💠", primary: "#00E5FF", accent: "#00B8D4", bg: "#02050A", glow: "rgba(0, 229, 255, 0.45)" },
  { id: "night", name: "DARK CHARCOAL", icon: "🌙", primary: "#60a5fa", accent: "#38bdf8", bg: "#071018", glow: "rgba(96, 165, 250, 0.4)" },
  { id: "stealth", name: "OLED BLACK", icon: "🌑", primary: "#ffffff", accent: "#94a3b8", bg: "#000000", glow: "rgba(255, 255, 255, 0.35)" },
  { id: "gold", name: "ARC GOLD", icon: "⚡", primary: "#facc15", accent: "#fb923c", bg: "#0c0602", glow: "rgba(250, 204, 21, 0.4)" },
  { id: "emerald", name: "MATRIX GREEN", icon: "🟢", primary: "#00FFC6", accent: "#10b981", bg: "#010e08", glow: "rgba(0, 255, 198, 0.4)" },
  { id: "neon", name: "NEON MAGENTA", icon: "🔮", primary: "#ec4899", accent: "#a855f7", bg: "#0c0214", glow: "rgba(236, 72, 153, 0.4)" },
  { id: "abyss", name: "OCEAN ABYSS", icon: "🌊", primary: "#38bdf8", accent: "#0284c7", bg: "#010b18", glow: "rgba(56, 189, 248, 0.4)" },
  { id: "natural", name: "GOOGLE CLEAR", icon: "🗺️", primary: "#4285f4", accent: "#34a853", bg: "#ffffff", glow: "rgba(66, 133, 244, 0.4)" },
];

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
  const countryOutlinesLayerRef = useRef<L.GeoJSON | null>(null);

  // Routing Refs
  const routeLayerRef = useRef<L.GeoJSON | L.Polyline | null>(null);
  const altRouteLayersRef = useRef<{ [key: string]: L.Layer }>({});
  const fromMarkerRef = useRef<L.Marker | null>(null);
  const toMarkerRef = useRef<L.Marker | null>(null);
  const stopMarkersRef = useRef<{ [key: string]: L.Marker }>({});

  // States
  const [projectionMode, setProjectionMode] = useState<"globe_3d" | "tactical_2d">("globe_3d");
  const [isHybridMode, setIsHybridMode] = useState<boolean>(true);
  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);
  const [transitionType, setTransitionType] = useState<"dive" | "pullback">("dive");
  const [transitionTargetLabel, setTransitionTargetLabel] = useState<string>("");

  const isHybridModeRef = useRef<boolean>(true);
  const projectionModeRef = useRef<"globe_3d" | "tactical_2d">("globe_3d");

  useEffect(() => {
    isHybridModeRef.current = isHybridMode;
    projectionModeRef.current = projectionMode;
  }, [isHybridMode, projectionMode]);

  const [activeLayer, setActiveLayer] = useState<MapLayerType>("friday_hud");
  const [fridayTheme, setFridayTheme] = useState<FridayThemeVariant>(() => {
    const saved = localStorage.getItem("FRIDAY_MAP_THEME") as FridayThemeVariant;
    if (saved) return saved;
    return "cyan";
  });
  const currentTheme = FRIDAY_THEME_OPTIONS.find((t) => t.id === fridayTheme) || FRIDAY_THEME_OPTIONS[0];

  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lng: number }>({ lat: 20.5937, lng: 78.9629 });
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [currentZoom, setCurrentZoom] = useState<number>(5);
  const [selectedLocationName, setSelectedLocationName] = useState<string>("India National Hub");
  const [isRadarSweeping, setIsRadarSweeping] = useState<boolean>(false);

  // Google Cloud Maps Platform Integration
  const [googleApiKey, setGoogleApiKey] = useState<string>(() => {
    return localStorage.getItem("FRIDAY_GMP_API_KEY") || "";
  });
  const [tempApiKeyInput, setTempApiKeyInput] = useState<string>("");
  const [showGoogleConfigModal, setShowGoogleConfigModal] = useState<boolean>(false);
  const [showSectorDetails, setShowSectorDetails] = useState<boolean>(false);
  const [showThemeMenu, setShowThemeMenu] = useState<boolean>(false);

  // Search & Navigation States
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearchingSingle, setIsSearchingSingle] = useState<boolean>(false);

  // From / Intermediate Stops / To Navigation & Route Planner States
  const [isRouteMode, setIsRouteMode] = useState<boolean>(false);
  const [fromQuery, setFromQuery] = useState<string>("");
  const [toQuery, setToQuery] = useState<string>("");
  const [fromWaypoint, setFromWaypoint] = useState<Waypoint | null>(null);
  const [toWaypoint, setToWaypoint] = useState<Waypoint | null>(null);
  const [intermediateStops, setIntermediateStops] = useState<IntermediateStop[]>([]);
  const [fromResults, setFromResults] = useState<SearchResult[]>([]);
  const [toResults, setToResults] = useState<SearchResult[]>([]);
  const [isSearchingFrom, setIsSearchingFrom] = useState<boolean>(false);
  const [isSearchingTo, setIsSearchingTo] = useState<boolean>(false);
  const [isCalculatingRoute, setIsCalculatingRoute] = useState<boolean>(false);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [routeAlternatives, setRouteAlternatives] = useState<RouteOption[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string>("route-1");

  const isRouteModeRef = useRef<boolean>(false);
  useEffect(() => {
    isRouteModeRef.current = isRouteMode;
  }, [isRouteMode]);

  // Invalidate Leaflet Map Size when switching projection mode or resizing
  useEffect(() => {
    if (projectionMode === "tactical_2d" && mapInstanceRef.current) {
      setTimeout(() => {
        mapInstanceRef.current?.invalidateSize();
      }, 60);
    }
  }, [projectionMode]);

  // Multi-Engine Tile Layer URL Generator (FRIDAY Tactical Matrix + Google Sat & Fallbacks)
  const getTileUrl = (layerType: MapLayerType) => {
    const keyParam = googleApiKey ? `&key=${googleApiKey}` : "";
    switch (layerType) {
      case "friday_hud":
        // Native FRIDAY Tactical Dark Vector (Pure Dark Navy Ocean #020810, Charcoal Land #0b151d, Zero Key & Zero Watermark)
        return "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
      case "google_sat":
        return `https://mt{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}${keyParam}`;
      case "google_hybrid":
        return `https://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}${keyParam}`;
      case "google_terrain":
        return `https://mt{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}${keyParam}`;
      case "osm_blueprint":
        return "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
      case "friday_cyber":
      default:
        return "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
    }
  };

  const getSubdomains = (layerType: MapLayerType) => {
    if (layerType.startsWith("google_")) {
      return ["0", "1", "2", "3"];
    }
    return "abcd";
  };

  const getTileClassName = (layerType: MapLayerType) => {
    if (layerType === "friday_hud") return "friday-tactical-hud-tiles";
    if (layerType === "google_terrain") return "google-terrain-tiles";
    if (layerType === "friday_cyber") return "friday-cyber-tiles";
    return "";
  };

  // Custom Friday Tactical Marker Icon (FRIDAY Target Reticle + Coordinate Tag)
  const createFridayTacticalIcon = (
    label?: string,
    color: "theme" | "cyan" | "green" | "red" = "theme",
    isCurrentLocation: boolean = false
  ) => {
    const mainColor =
      color === "green" ? "#00FFC6" : color === "red" ? "#FF3366" : color === "cyan" ? "#00E5FF" : currentTheme.primary;
    const glowColor =
      color === "green"
        ? "rgba(0, 255, 198, 0.6)"
        : color === "red"
        ? "rgba(255, 51, 102, 0.6)"
        : currentTheme.glow;
    const bgGradient =
      color === "green"
        ? "linear-gradient(135deg, rgba(1, 22, 14, 0.96) 0%, rgba(1, 8, 12, 0.98) 100%)"
        : color === "red"
        ? "linear-gradient(135deg, rgba(26, 2, 8, 0.96) 0%, rgba(12, 1, 4, 0.98) 100%)"
        : "linear-gradient(135deg, rgba(2, 14, 28, 0.96) 0%, rgba(1, 6, 16, 0.98) 100%)";

    // Clean label text and remove any duplicate prefix
    let cleanName = (label || "").trim();
    cleanName = cleanName.replace(/^(START|DEST|ORIGIN|TARGET|STOP\s*\d*|LOCATION)\s*[:\/\-]\s*/i, "").trim();
    if (!cleanName) cleanName = color === "green" ? "ORIGIN" : color === "red" ? "DESTINATION" : "TARGET";

    const tagType =
      color === "green"
        ? "🟢 START"
        : color === "red"
        ? "🔴 DEST"
        : color === "cyan"
        ? "📍 TARGET"
        : isCurrentLocation
        ? "💠 HQ"
        : "🔵 WAYPOINT";

    return L.divIcon({
      className: "friday-tactical-marker-container",
      html: `
        <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; pointer-events: auto;">
          <!-- Pulsing Outer Radar Reticle -->
          <div style="position: absolute; inset: 0; border-radius: 50%; border: 1.5px dashed ${mainColor}; box-shadow: 0 0 14px ${glowColor}; animation: rotateArc 3.5s linear infinite; pointer-events: none;"></div>
          
          <!-- Inner Core Ring -->
          <div style="position: absolute; width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid ${mainColor}; box-shadow: 0 0 8px ${glowColor}; animation: pulseRing 1.8s ease-out infinite; pointer-events: none;"></div>
          
          <!-- Glowing Center Beacon Dot -->
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #ffffff; box-shadow: 0 0 12px ${mainColor}, 0 0 4px #ffffff; pointer-events: none;"></div>
          
          <!-- Holographic FRIDAY HUD Badge Tag (Always Horizontal & Centered Above Pin) -->
          <div style="position: absolute; bottom: 48px; left: 50%; transform: translateX(-50%); background: ${bgGradient}; border: 1.5px solid ${mainColor}; border-radius: 4px; padding: 4px 10px; display: flex; align-items: center; gap: 6px; box-shadow: 0 0 18px ${glowColor}, inset 0 0 8px ${glowColor}; white-space: nowrap; pointer-events: none; z-index: 99999; backdrop-filter: blur(10px);">
            <span style="font-family: 'Orbitron', monospace; font-size: 9.5px; font-weight: 900; color: ${mainColor}; letter-spacing: 0.5px;">${tagType}</span>
            <span style="width: 1px; height: 10px; background: rgba(255,255,255,0.25);"></span>
            <span style="font-family: 'Share Tech Mono', monospace; font-size: 10.5px; font-weight: 700; color: #ffffff; letter-spacing: 1px; text-shadow: 0 0 8px ${mainColor};">${cleanName.toUpperCase()}</span>
          </div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });
  };

  // Seamless Animated Transition from 3D Globe to 2D Tactical Map
  const triggerTransitionTo2D = (lat: number, lng: number, name?: string, targetZoom: number = 12) => {
    setIsTransitioning(true);
    setTransitionType("dive");
    const label = name || `SECTOR (${lat.toFixed(2)}°, ${lng.toFixed(2)}°)`;
    setTransitionTargetLabel(label);
    setSelectedLocationName(label);
    setCurrentCoords({ lat, lng });

    setTimeout(() => {
      setProjectionMode("tactical_2d");
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
          mapInstanceRef.current.setView([lat, lng], targetZoom, { animate: false });
          if (activeMarkerRef.current) {
            activeMarkerRef.current.setLatLng([lat, lng]);
            activeMarkerRef.current.setIcon(createFridayTacticalIcon(label.split(",")[0].toUpperCase(), "cyan"));
          }
        }
      }, 50);

      setTimeout(() => {
        setIsTransitioning(false);
      }, 450);
    }, 300);
  };

  // Seamless Animated Transition from 2D Tactical Map back to 3D Globe
  const triggerTransitionToGlobe = (lat: number, lng: number) => {
    setIsTransitioning(true);
    setTransitionType("pullback");
    setTransitionTargetLabel("GLOBAL ORBITAL MATRIX");
    setCurrentCoords({ lat, lng });

    setTimeout(() => {
      setProjectionMode("globe_3d");
      setTimeout(() => {
        setIsTransitioning(false);
      }, 450);
    }, 300);
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
          maxZoom: 20,
          zoomControl: false,
          attributionControl: false,
        });

        // Add Base Tile Layer with high-res zoom support
        const sub = getSubdomains(activeLayer);
        const tileLayer = L.tileLayer(getTileUrl(activeLayer), {
          maxZoom: 22,
          maxNativeZoom: activeLayer.startsWith("google_") ? 21 : 19,
          subdomains: sub,
          className: getTileClassName(activeLayer),
        }).addTo(map);
        tileLayerRef.current = tileLayer;

        // Add High-Resolution Reference Labels Layer (Displays State, City, Area, Street names)
        if (activeLayer === "friday_hud" || activeLayer === "friday_cyber") {
          const labelsTileLayer = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            {
              maxZoom: 20,
              maxNativeZoom: 19,
              subdomains: "abcd",
              className: "friday-tactical-label-tiles",
            }
          ).addTo(map);
          labelsTileLayerRef.current = labelsTileLayer;
        } else if (activeLayer === "google_hybrid" || activeLayer === "google_sat") {
          const labelsTileLayer = L.tileLayer(
            "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            {
              maxZoom: 20,
              maxNativeZoom: 19,
              subdomains: "abcd",
            }
          ).addTo(map);
          labelsTileLayerRef.current = labelsTileLayer;
        }

        // Add Country Boundaries Blue Outline Layer
        fetch("/world-continents.json")
          .then((res) => res.json())
          .then((geoData) => {
            if (mapInstanceRef.current) {
              if (countryOutlinesLayerRef.current) {
                mapInstanceRef.current.removeLayer(countryOutlinesLayerRef.current);
              }
              const countriesLayer = L.geoJSON(geoData, {
                style: {
                  color: "#00E5FF",
                  weight: 1.2,
                  opacity: 0.65,
                  fillColor: "#00E5FF",
                  fillOpacity: 0.02,
                  className: "friday-country-boundary-path",
                },
                onEachFeature: (feature, layer) => {
                  if (feature.properties && feature.properties.name) {
                    layer.bindTooltip(`● ${feature.properties.name.toUpperCase()}`, {
                      className: "friday-continent-tooltip",
                      sticky: true,
                    });
                  }
                },
              }).addTo(mapInstanceRef.current);
              countryOutlinesLayerRef.current = countriesLayer;
            }
          })
          .catch((err) => console.warn("Failed to load country outlines:", err));

        // Add Initial HQ Pin
        const marker = L.marker([initialLat, initialLng], {
          icon: createFridayTacticalIcon("FRIDAY HQ", "cyan"),
        }).addTo(map);
        activeMarkerRef.current = marker;

        // Event: Move / Pan / Zoom
        map.on("move", () => {
          const center = map.getCenter();
          setCurrentCoords({ lat: Number(center.lat.toFixed(4)), lng: Number(center.lng.toFixed(4)) });
        });

        map.on("zoomend", () => {
          const newZoom = map.getZoom();
          setCurrentZoom(newZoom);
          // If in Hybrid mode and user zooms out to planetary level (<= 3), smoothly pull back to 3D Globe!
          if (isHybridModeRef.current && projectionModeRef.current === "tactical_2d" && newZoom <= 3) {
            const center = map.getCenter();
            triggerTransitionToGlobe(Number(center.lat.toFixed(4)), Number(center.lng.toFixed(4)));
          }
        });

        let lastMove = 0;
        map.on("mousemove", (e: L.LeafletMouseEvent) => {
          const now = performance.now();
          if (now - lastMove > 100) {
            lastMove = now;
            setCursorCoords({ lat: Number(e.latlng.lat.toFixed(4)), lng: Number(e.latlng.lng.toFixed(4)) });
          }
        });

        // Event: Click on map to drop tactical target pin / route point
        map.on("click", (e: L.LeafletMouseEvent) => {
          const { lat, lng } = e.latlng;
          const latRounded = Number(lat.toFixed(4));
          const lngRounded = Number(lng.toFixed(4));

          fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
            .then((res) => res.json())
            .then((data) => {
              const placeName = data?.display_name || `Target (${latRounded}°, ${lngRounded}°)`;
              const shortName =
                data?.address?.suburb ||
                data?.address?.neighbourhood ||
                data?.address?.city ||
                data?.address?.town ||
                data?.address?.village ||
                data?.address?.state ||
                data?.address?.country ||
                "TARGET";

              setSelectedLocationName(placeName);

              if (isRouteModeRef.current) {
                // In Route Mode: Click sets Destination
                setToQuery(placeName);
                const wp: Waypoint = { lat: latRounded, lng: lngRounded, name: placeName };
                setToWaypoint(wp);

                if (toMarkerRef.current && mapInstanceRef.current) {
                  toMarkerRef.current.setLatLng([lat, lng]);
                  toMarkerRef.current.setIcon(createFridayTacticalIcon(shortName.toUpperCase(), "red"));
                } else if (mapInstanceRef.current) {
                  toMarkerRef.current = L.marker([lat, lng], {
                    icon: createFridayTacticalIcon(shortName.toUpperCase(), "red"),
                  }).addTo(mapInstanceRef.current);
                }
              } else {
                // In Normal Map Search / Recon: Click sets Tactical Target (NOT DEST!)
                setSearchQuery(placeName);
                if (activeMarkerRef.current && mapInstanceRef.current) {
                  activeMarkerRef.current.setLatLng([lat, lng]);
                  activeMarkerRef.current.setIcon(createFridayTacticalIcon(shortName.toUpperCase(), "cyan"));
                } else if (mapInstanceRef.current) {
                  activeMarkerRef.current = L.marker([lat, lng], {
                    icon: createFridayTacticalIcon(shortName.toUpperCase(), "cyan"),
                  }).addTo(mapInstanceRef.current);
                }
              }
            })
            .catch(() => {
              const fallbackName = `Target (${latRounded}°, ${lngRounded}°)`;
              setSelectedLocationName(fallbackName);

              if (isRouteModeRef.current) {
                setToQuery(fallbackName);
                const wp: Waypoint = { lat: latRounded, lng: lngRounded, name: fallbackName };
                setToWaypoint(wp);

                if (toMarkerRef.current && mapInstanceRef.current) {
                  toMarkerRef.current.setLatLng([lat, lng]);
                  toMarkerRef.current.setIcon(createFridayTacticalIcon("TARGET", "red"));
                } else if (mapInstanceRef.current) {
                  toMarkerRef.current = L.marker([lat, lng], {
                    icon: createFridayTacticalIcon("TARGET", "red"),
                  }).addTo(mapInstanceRef.current);
                }
              } else {
                setSearchQuery(fallbackName);
                if (activeMarkerRef.current && mapInstanceRef.current) {
                  activeMarkerRef.current.setLatLng([lat, lng]);
                  activeMarkerRef.current.setIcon(createFridayTacticalIcon("TARGET", "cyan"));
                } else if (mapInstanceRef.current) {
                  activeMarkerRef.current = L.marker([lat, lng], {
                    icon: createFridayTacticalIcon("TARGET", "cyan"),
                  }).addTo(mapInstanceRef.current);
                }
              }
            });
        });

        mapInstanceRef.current = map;
      } else {
        mapInstanceRef.current.invalidateSize();
      }
    }, 100);

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
    if (labelsTileLayerRef.current) {
      mapInstanceRef.current.removeLayer(labelsTileLayerRef.current);
      labelsTileLayerRef.current = null;
    }
    const sub = getSubdomains(activeLayer);
    const newLayer = L.tileLayer(getTileUrl(activeLayer), {
      maxZoom: 22,
      maxNativeZoom: activeLayer.startsWith("google_") ? 21 : 19,
      subdomains: sub,
      className: getTileClassName(activeLayer),
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current = newLayer;

    if (activeLayer === "friday_hud" || activeLayer === "friday_cyber") {
      const labelsLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 20,
          maxNativeZoom: 19,
          subdomains: "abcd",
          className: "friday-tactical-label-tiles",
        }
      ).addTo(mapInstanceRef.current);
      labelsTileLayerRef.current = labelsLayer;
    } else if (activeLayer === "google_hybrid" || activeLayer === "google_sat") {
      const labelsLayer = L.tileLayer(
        "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 20,
          maxNativeZoom: 19,
          subdomains: "abcd",
        }
      ).addTo(mapInstanceRef.current);
      labelsTileLayerRef.current = labelsLayer;
    }
  }, [activeLayer, googleApiKey]);

  // Multi-Provider Geocoder (Nominatim -> Photon -> Open-Meteo + Raw GPS Coordinates)
  const geocodeText = async (query: string): Promise<SearchResult[]> => {
    if (!query || !query.trim()) return [];
    const cleanQuery = query.trim();

    // 0. Check if user entered raw GPS coordinates (e.g. 10.7905, 78.7047)
    const coordMatch = cleanQuery.match(/^(-?\d+(\.\d+)?)[,\s]+(-?\d+(\.\d+)?)$/);
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1]);
      const lon = parseFloat(coordMatch[3]);
      if (!isNaN(lat) && !isNaN(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
        return [
          {
            display_name: `GPS Target: ${lat.toFixed(5)}° N, ${lon.toFixed(5)}° E`,
            lat: String(lat),
            lon: String(lon),
            type: "coordinates",
          },
        ];
      }
    }

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

  // Render All Alternative Routes on the Leaflet Map
  const renderRouteAlternativesOnMap = (
    routes: RouteOption[],
    activeId: string,
    allWaypoints: Waypoint[]
  ) => {
    if (!mapInstanceRef.current) return;

    // 1. Remove previous route layers
    if (routeLayerRef.current) {
      mapInstanceRef.current.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    Object.values(altRouteLayersRef.current).forEach((layer) => {
      mapInstanceRef.current?.removeLayer(layer);
    });
    altRouteLayersRef.current = {};

    // 2. Draw all alternative routes (inactive first, then active on top)
    routes.forEach((route) => {
      const isActive = route.id === activeId;
      if (isActive) {
        const activeLayer = L.geoJSON(route.geojson, {
          style: {
            color: "#00E5FF",
            weight: 5,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
            className: "friday-route-corridor",
          },
        }).addTo(mapInstanceRef.current!);
        routeLayerRef.current = activeLayer;
      } else {
        const altLayer = L.geoJSON(route.geojson, {
          style: {
            color: route.color || "#38bdf8",
            weight: 3.5,
            opacity: 0.65,
            dashArray: "6, 8",
            className: "friday-alt-route",
          },
        }).addTo(mapInstanceRef.current!);

        // Clicking on an alternative path activates it!
        altLayer.on("click", () => {
          selectActiveRoute(route.id, routes, allWaypoints);
        });
        altRouteLayersRef.current[route.id] = altLayer;
      }
    });

    // 3. Update active route telemetry info
    const activeRoute = routes.find((r) => r.id === activeId) || routes[0];
    setRouteInfo({
      distanceKm: activeRoute.distanceKm,
      durationMins: activeRoute.durationMins,
      summary: activeRoute.summary,
    });

    // 4. Place Start, Intermediate Stops, and Destination Markers
    const startWp = allWaypoints[0];
    const destWp = allWaypoints[allWaypoints.length - 1];

    if (fromMarkerRef.current) {
      fromMarkerRef.current.setLatLng([startWp.lat, startWp.lng]);
      fromMarkerRef.current.setIcon(createFridayTacticalIcon(`START: ${startWp.name.split(",")[0].toUpperCase()}`, "green"));
    } else {
      fromMarkerRef.current = L.marker([startWp.lat, startWp.lng], {
        icon: createFridayTacticalIcon(`START: ${startWp.name.split(",")[0].toUpperCase()}`, "green"),
      }).addTo(mapInstanceRef.current);
    }

    // Clear and draw intermediate stop markers
    Object.values(stopMarkersRef.current).forEach((m) => mapInstanceRef.current?.removeLayer(m));
    stopMarkersRef.current = {};

    for (let i = 1; i < allWaypoints.length - 1; i++) {
      const stopWp = allWaypoints[i];
      const stopMarker = L.marker([stopWp.lat, stopWp.lng], {
        icon: createFridayTacticalIcon(`STOP ${i}: ${stopWp.name.split(",")[0].toUpperCase()}`, "cyan"),
      }).addTo(mapInstanceRef.current);
      stopMarkersRef.current[`stop-${i}`] = stopMarker;
    }

    if (toMarkerRef.current) {
      toMarkerRef.current.setLatLng([destWp.lat, destWp.lng]);
      toMarkerRef.current.setIcon(createFridayTacticalIcon(`DEST: ${destWp.name.split(",")[0].toUpperCase()}`, "red"));
    } else {
      toMarkerRef.current = L.marker([destWp.lat, destWp.lng], {
        icon: createFridayTacticalIcon(`DEST: ${destWp.name.split(",")[0].toUpperCase()}`, "red"),
      }).addTo(mapInstanceRef.current);
    }

    // 5. Fit Bounds
    if (routeLayerRef.current) {
      mapInstanceRef.current.fitBounds((routeLayerRef.current as any).getBounds(), {
        padding: [80, 80],
        animate: true,
        duration: 1.2,
      });
    }

    const hrs = Math.floor(activeRoute.durationMins / 60);
    const mins = activeRoute.durationMins % 60;
    const timeStr = hrs > 0 ? `${hrs}h ${mins}m` : `${mins} mins`;
    setSelectedLocationName(`Route: ${startWp.name.split(",")[0]} ➔ ${destWp.name.split(",")[0]} (${activeRoute.distanceKm} km • ${timeStr})`);
  };

  // Switch Active Route from Alternatives
  const selectActiveRoute = (routeId: string, routesList?: RouteOption[], waypointsList?: Waypoint[]) => {
    setSelectedRouteId(routeId);
    const routes = routesList || routeAlternatives;
    const allWaypoints =
      waypointsList || [
        fromWaypoint || { lat: currentCoords.lat, lng: currentCoords.lng, name: "Origin" },
        ...intermediateStops.map((s) => s.waypoint).filter(Boolean) as Waypoint[],
        toWaypoint || { lat: currentCoords.lat, lng: currentCoords.lng, name: "Destination" },
      ];

    if (routes.length > 0) {
      renderRouteAlternativesOnMap(routes, routeId, allWaypoints);
    }
  };

  // Handle Calculate Route / Navigation (Multi-Stop + 2-3 Alternatives)
  const calculateRoute = async (customFrom?: Waypoint | null, customTo?: Waypoint | null) => {
    if (!mapInstanceRef.current) return;
    setIsCalculatingRoute(true);

    // Immediately hide all suggestion dropdowns on Enter or submit
    setFromResults([]);
    setToResults([]);
    setIntermediateStops((prev) => prev.map((s) => ({ ...s, results: [] })));

    try {
      let from = customFrom !== undefined ? customFrom : fromWaypoint;
      let to = customTo !== undefined ? customTo : toWaypoint;

      // Auto-resolve typed FROM text if user typed their own city name or modified query
      if (fromQuery.trim()) {
        const needsGeocoding = !from || !from.name.toLowerCase().includes(fromQuery.trim().toLowerCase());
        if (needsGeocoding) {
          const results = await geocodeText(fromQuery.trim());
          if (results && results.length > 0) {
            from = {
              lat: parseFloat(results[0].lat),
              lng: parseFloat(results[0].lon),
              name: results[0].display_name,
            };
            setFromWaypoint(from);
          }
        }
      }

      // Auto-resolve typed TO text if user typed their own city name or modified query
      if (toQuery.trim()) {
        const needsGeocoding = !to || !to.name.toLowerCase().includes(toQuery.trim().toLowerCase());
        if (needsGeocoding) {
          const results = await geocodeText(toQuery.trim());
          if (results && results.length > 0) {
            to = {
              lat: parseFloat(results[0].lat),
              lng: parseFloat(results[0].lon),
              name: results[0].display_name,
            };
            setToWaypoint(to);
          }
        }
      }

      // Auto-resolve any intermediate stop texts
      const updatedStops = [...intermediateStops];
      for (let i = 0; i < updatedStops.length; i++) {
        if (updatedStops[i].query.trim()) {
          const st = updatedStops[i];
          const needsGeocoding = !st.waypoint || !st.waypoint.name.toLowerCase().includes(st.query.trim().toLowerCase());
          if (needsGeocoding) {
            const results = await geocodeText(st.query.trim());
            if (results && results.length > 0) {
              updatedStops[i].waypoint = {
                lat: parseFloat(results[0].lat),
                lng: parseFloat(results[0].lon),
                name: results[0].display_name,
              };
            }
          }
        }
      }
      setIntermediateStops(updatedStops);

      // Case 1: Only Destination (TO) is provided -> Fly to Destination & Drop Tactical Target
      if (!from && to) {
        flyToLocation(to.lat, to.lng, to.name, 14);
        if (toMarkerRef.current && mapInstanceRef.current) {
          toMarkerRef.current.setLatLng([to.lat, to.lng]);
          toMarkerRef.current.setIcon(createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"));
        } else if (mapInstanceRef.current) {
          toMarkerRef.current = L.marker([to.lat, to.lng], {
            icon: createFridayTacticalIcon(`DEST: ${to.name.split(",")[0].toUpperCase()}`, "red"),
          }).addTo(mapInstanceRef.current);
        }
        setRouteInfo(null);
        setRouteAlternatives([]);
        return;
      }

      // Case 2: Only Origin (FROM) is provided -> Fly to Origin
      if (from && !to) {
        flyToLocation(from.lat, from.lng, from.name, 14);
        if (fromMarkerRef.current && mapInstanceRef.current) {
          fromMarkerRef.current.setLatLng([from.lat, from.lng]);
          fromMarkerRef.current.setIcon(createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"));
        } else if (mapInstanceRef.current) {
          fromMarkerRef.current = L.marker([from.lat, from.lng], {
            icon: createFridayTacticalIcon(`START: ${from.name.split(",")[0].toUpperCase()}`, "green"),
          }).addTo(mapInstanceRef.current);
        }
        setRouteInfo(null);
        setRouteAlternatives([]);
        return;
      }

      // Case 3: Both FROM and TO are provided -> Calculate Full Road Route with Authentic Road Alternatives & Multi-Stops
      if (from && to) {
        const validStops = updatedStops.filter((s) => s.waypoint !== null);
        const allWaypoints: Waypoint[] = [from, ...validStops.map((s) => s.waypoint!), to];
        const coordsString = allWaypoints.map((w) => `${w.lng},${w.lat}`).join(";");

        let generatedAlternatives: RouteOption[] = [];

        // Attempt OSRM driving road route with genuine alternatives
        try {
          const url = `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson&alternatives=3&steps=true&annotations=true`;
          const resp = await fetch(url);
          if (resp.ok) {
            const data = await resp.json();
            if (data && data.routes && data.routes.length > 0) {
              // Sort routes by duration to guarantee the primary route is the fastest/shortest
              const sortedRoutes = [...data.routes].sort((a, b) => a.duration - b.duration);

              generatedAlternatives = sortedRoutes.slice(0, 3).map((r: any, idx: number) => {
                const distKm = Number((r.distance / 1000).toFixed(1));
                const durMins = Math.round(r.duration / 60);
                const roadSummary =
                  r.legs?.map((l: any) => l.summary).filter(Boolean).join(" / ") ||
                  (idx === 0
                    ? "Fastest Highway Corridor"
                    : idx === 1
                    ? "National Highway Route"
                    : "Alternative State Highway");

                return {
                  id: `route-${idx + 1}`,
                  name:
                    idx === 0
                      ? "⚡ ROUTE 1 (FASTEST ROAD)"
                      : idx === 1
                      ? "🛣️ ROUTE 2 (NATIONAL HIGHWAY)"
                      : `🌐 ROUTE ${idx + 1} (STATE HIGHWAY / BYPASS)`,
                  distanceKm: distKm,
                  durationMins: durMins,
                  summary: roadSummary,
                  geojson: r.geometry,
                  color: idx === 0 ? "#00E5FF" : idx === 1 ? "#38bdf8" : "#00FFC6",
                  type: idx === 0 ? "primary" : "alternative",
                };
              });
            }
          }
        } catch (osrmErr) {
          console.warn("OSRM routing server unavailable:", osrmErr);
        }

        // Offline / fallback road line if OSRM endpoint failed
        if (generatedAlternatives.length === 0) {
          const distEst = Number(
            (
              Math.hypot(to.lat - from.lat, to.lng - from.lng) * 111
            ).toFixed(1)
          );
          const durEst = Math.round((distEst / 65) * 60);
          generatedAlternatives.push({
            id: "route-1",
            name: "⚡ ROUTE 1 (DIRECT ROAD CORRIDOR)",
            distanceKm: distEst,
            durationMins: durEst,
            summary: "Direct Regional Corridor",
            geojson: {
              type: "LineString",
              coordinates: allWaypoints.map((w) => [w.lng, w.lat]),
            },
            color: "#00E5FF",
            type: "primary",
          });
        }

        setRouteAlternatives(generatedAlternatives);
        if (generatedAlternatives.length > 0) {
          setSelectedRouteId(generatedAlternatives[0].id);
          renderRouteAlternativesOnMap(generatedAlternatives, generatedAlternatives[0].id, allWaypoints);
        }
      }
    } catch (err) {
      console.error("Route calculation error:", err);
    } finally {
      setIsCalculatingRoute(false);
    }
  };

  // Intermediate Stop Helper Functions
  const addIntermediateStop = () => {
    const newStop: IntermediateStop = {
      id: `stop-${Date.now()}`,
      query: "",
      waypoint: null,
      results: [],
      isSearching: false,
    };
    setIntermediateStops((prev) => [...prev, newStop]);
  };

  const removeIntermediateStop = (id: string) => {
    setIntermediateStops((prev) => prev.filter((s) => s.id !== id));
    if (stopMarkersRef.current[id] && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(stopMarkersRef.current[id]);
      delete stopMarkersRef.current[id];
    }
  };

  const updateStopQuery = (id: string, text: string) => {
    setIntermediateStops((prev) =>
      prev.map((s) => (s.id === id ? { ...s, query: text } : s))
    );
    searchLocation(text, (res) => {
      setIntermediateStops((prev) =>
        prev.map((s) => (s.id === id ? { ...s, results: typeof res === "function" ? res(s.results) : res } : s))
      );
    }, (searching) => {
      setIntermediateStops((prev) =>
        prev.map((s) => (s.id === id ? { ...s, isSearching: typeof searching === "function" ? searching(s.isSearching) : searching } : s))
      );
    });
  };

  // Clear Active Route & Waypoints
  const clearRoute = () => {
    if (routeLayerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    Object.values(altRouteLayersRef.current).forEach((layer) => {
      mapInstanceRef.current?.removeLayer(layer);
    });
    altRouteLayersRef.current = {};

    if (fromMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(fromMarkerRef.current);
      fromMarkerRef.current = null;
    }
    if (toMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(toMarkerRef.current);
      toMarkerRef.current = null;
    }
    Object.values(stopMarkersRef.current).forEach((m) => mapInstanceRef.current?.removeLayer(m));
    stopMarkersRef.current = {};

    setFromWaypoint(null);
    setToWaypoint(null);
    setIntermediateStops([]);
    setFromQuery("");
    setToQuery("");
    setRouteInfo(null);
    setRouteAlternatives([]);
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
    setSelectedLocationName(name);
    setCurrentCoords({ lat, lng });

    if (projectionModeRef.current === "globe_3d") {
      triggerTransitionTo2D(lat, lng, name, zoomLevel);
      return;
    }

    if (!mapInstanceRef.current) return;
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
        /* FRIDAY Tactical Cartography Layer Filters */
        .friday-map-viewport .leaflet-tile-pane {
          filter: ${
            activeLayer === "friday_hud" || activeLayer === "friday_cyber" || activeLayer === "osm_blueprint"
              ? fridayTheme === "cyan"
                ? "brightness(0.9) contrast(1.35) sepia(100%) hue-rotate(170deg) saturate(380%)"
                : fridayTheme === "night"
                ? "brightness(0.9) contrast(1.35) sepia(100%) hue-rotate(190deg) saturate(350%)"
                : fridayTheme === "emerald"
                ? "brightness(0.9) contrast(1.35) sepia(100%) hue-rotate(85deg) saturate(380%)"
                : fridayTheme === "gold"
                ? "brightness(0.9) contrast(1.35) sepia(100%) hue-rotate(5deg) saturate(450%)"
                : fridayTheme === "neon"
                ? "brightness(0.9) contrast(1.35) sepia(100%) hue-rotate(270deg) saturate(420%)"
                : fridayTheme === "abyss"
                ? "brightness(0.85) contrast(1.45) sepia(100%) hue-rotate(185deg) saturate(500%)"
                : fridayTheme === "stealth"
                ? "grayscale(100%) contrast(1.4) brightness(0.9)"
                : "none"
              : activeLayer.startsWith("google_")
              ? "contrast(1.05) brightness(0.95)"
              : "none"
          };
          transition: filter 0.3s ease;
        }

        /* FRIDAY Tactical Glowing Labels */
        .friday-map-viewport .friday-tactical-label-tiles {
          filter: brightness(1.6) contrast(1.8) sepia(100%) hue-rotate(168deg) saturate(600%) drop-shadow(0 0 3px rgba(0, 229, 255, 0.75)) !important;
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

          {/* 3D Globe / 3D Buildings / 2D Tactical View Mode Switcher */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(0, 240, 255, 0.12)", padding: "3px", borderRadius: "8px", border: "1.5px solid rgba(0, 240, 255, 0.4)" }}>
            <button
              onClick={() => {
                setIsHybridMode(true);
                if (currentZoom <= 9) setProjectionMode("globe_3d");
                else setProjectionMode("tactical_2d");
              }}
              style={{
                background: isHybridMode ? "linear-gradient(135deg, rgba(0, 240, 255, 0.55), rgba(0, 119, 255, 0.4))" : "transparent",
                border: isHybridMode ? "1.5px solid #00f0ff" : "1px solid transparent",
                color: isHybridMode ? "#ffffff" : "#8ab4f8",
                borderRadius: "5px",
                padding: "6px 14px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                boxShadow: isHybridMode ? "0 0 16px rgba(0, 240, 255, 0.6)" : "none",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
              title="Unified Adaptive Zoom: 3D Globe (<= 9x) auto-transitions to 2D Map (> 9x)"
            >
              <span>⚡</span>
              <span>HYBRID (3D GLOBE ⇄ 2D MAP)</span>
              <span
                style={{
                  fontSize: "9px",
                  background: isHybridMode ? "rgba(0, 240, 255, 0.3)" : "rgba(100, 116, 139, 0.3)",
                  padding: "1px 6px",
                  borderRadius: "3px",
                  color: isHybridMode ? "#00f0ff" : "#94a3b8",
                  fontFamily: "monospace",
                }}
              >
                {projectionMode === "globe_3d" ? "GLOBE [1-9x]" : "2D MAP [10-22x]"}
              </span>
            </button>

            <button
              onClick={() => {
                setIsHybridMode(false);
                setProjectionMode("globe_3d");
              }}
              style={{
                background: !isHybridMode && projectionMode === "globe_3d" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.5), rgba(0, 119, 255, 0.3))" : "transparent",
                border: !isHybridMode && projectionMode === "globe_3d" ? "1.5px solid #00f0ff" : "1px solid transparent",
                color: !isHybridMode && projectionMode === "globe_3d" ? "#ffffff" : "#8ab4f8",
                borderRadius: "5px",
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                boxShadow: !isHybridMode && projectionMode === "globe_3d" ? "0 0 14px rgba(0, 240, 255, 0.5)" : "none",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
              title="Locked 3D Holographic Globe Mode"
            >
              <span>🌐</span>
              <span>3D GLOBE</span>
            </button>

            <button
              onClick={() => {
                setIsHybridMode(false);
                setProjectionMode("tactical_2d");
                setTimeout(() => mapInstanceRef.current?.invalidateSize(), 100);
              }}
              style={{
                background: !isHybridMode && projectionMode === "tactical_2d" ? "linear-gradient(135deg, rgba(52, 211, 153, 0.45), rgba(16, 185, 129, 0.25))" : "transparent",
                border: !isHybridMode && projectionMode === "tactical_2d" ? "1.5px solid #34d399" : "1px solid transparent",
                color: !isHybridMode && projectionMode === "tactical_2d" ? "#ffffff" : "#8ab4f8",
                borderRadius: "5px",
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                boxShadow: !isHybridMode && projectionMode === "tactical_2d" ? "0 0 14px rgba(52, 211, 153, 0.5)" : "none",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
              title="Locked 2D Tactical Leaflet Map"
            >
              <span>🗺️</span>
              <span>2D MAP</span>
            </button>
          </div>

          {/* Mode Tabs: Single Location vs Dual FROM / TO Route Planner */}
          {projectionMode === "tactical_2d" && (
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
          )}

          {/* Unified MAP THEME Dropdown (Consolidates all layer engines & color themes) */}
          <div style={{ position: "relative" }}>
            <button
              onClick={() => setShowThemeMenu((prev) => !prev)}
              style={{
                background: showThemeMenu
                  ? `linear-gradient(135deg, ${currentTheme.primary}45, ${currentTheme.accent}30)`
                  : "rgba(0, 0, 0, 0.65)",
                border: `1.5px solid ${currentTheme.primary}`,
                borderRadius: "6px",
                padding: "6px 12px",
                color: "#ffffff",
                fontSize: "10.5px",
                fontWeight: "bold",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "7px",
                boxShadow: `0 0 14px ${currentTheme.primary}35`,
                fontFamily: "'Orbitron', monospace",
                letterSpacing: "0.5px",
              }}
              title="Select Map Layer Engine & Holographic Theme"
            >
              <span>🎨</span>
              <span>MAP THEME</span>
              <span style={{ fontSize: "8px", color: currentTheme.primary }}>{showThemeMenu ? "▲" : "▼"}</span>
              <span
                style={{
                  fontSize: "9px",
                  background: `${currentTheme.primary}25`,
                  color: currentTheme.primary,
                  padding: "1px 6px",
                  borderRadius: "3px",
                  border: `1px solid ${currentTheme.primary}50`,
                  fontFamily: "'Share Tech Mono', monospace",
                }}
              >
                {activeLayer === "friday_hud"
                  ? "FRIDAY HUD"
                  : activeLayer === "google_sat"
                  ? "ORBITAL SAT"
                  : activeLayer === "google_hybrid"
                  ? "HYBRID SAT"
                  : activeLayer === "google_terrain"
                  ? "TERRAIN"
                  : activeLayer === "friday_cyber"
                  ? "NEURAL GRID"
                  : "BLUEPRINT"}
              </span>
            </button>

            {/* MAP THEME Dropdown Popover */}
            {showThemeMenu && (
              <div
                className="jarvis-glass-card"
                style={{
                  position: "absolute",
                  top: "calc(100% + 8px)",
                  right: 0,
                  background: "rgba(2, 8, 20, 0.98)",
                  border: `1.5px solid ${currentTheme.primary}`,
                  borderRadius: "8px",
                  padding: "14px",
                  minWidth: "340px",
                  zIndex: 999999,
                  boxShadow: `0 12px 36px rgba(0,0,0,0.85), 0 0 24px ${currentTheme.primary}35`,
                  backdropFilter: "blur(20px)",
                  animation: "fadeIn 0.15s ease-out",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* SECTION 1: MAP ENGINE / TILES */}
                <div
                  style={{
                    fontSize: "10px",
                    color: currentTheme.primary,
                    fontFamily: "'Orbitron', monospace",
                    fontWeight: "900",
                    letterSpacing: "1px",
                    marginBottom: "8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: `1px solid ${currentTheme.primary}30`,
                    paddingBottom: "5px",
                  }}
                >
                  <span>◤ MAP ENGINE & TILES ◢</span>
                  <span style={{ fontSize: "8.5px", color: "#94a3b8" }}>SELECT LAYER</span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", marginBottom: "14px" }}>
                  {[
                    { id: "friday_hud", name: "⚡ FRIDAY HUD", desc: "Tactical Dark Vector" },
                    { id: "google_sat", name: "🛰️ ORBITAL SAT", desc: "Orbital Satellite" },
                    { id: "google_hybrid", name: "🌐 HYBRID SAT", desc: "Sat + Roads/Labels" },
                    { id: "google_terrain", name: "⛰️ TERRAIN", desc: "3D Topographic" },
                    { id: "friday_cyber", name: "⚡ NEURAL GRID", desc: "ArcGIS Dark Matrix" },
                    { id: "osm_blueprint", name: "🗺️ BLUEPRINT", desc: "Blueprint Mesh" },
                  ].map((layer) => {
                    const isSelected = activeLayer === layer.id;
                    return (
                      <button
                        key={layer.id}
                        onClick={() => {
                          setActiveLayer(layer.id as MapLayerType);
                        }}
                        style={{
                          background: isSelected
                            ? "linear-gradient(135deg, rgba(0, 229, 255, 0.35), rgba(0, 184, 212, 0.2))"
                            : "rgba(255, 255, 255, 0.04)",
                          border: isSelected ? "1.5px solid #00E5FF" : "1px solid rgba(255, 255, 255, 0.1)",
                          color: isSelected ? "#00E5FF" : "#cbd5e1",
                          borderRadius: "5px",
                          padding: "7px 9px",
                          fontSize: "10px",
                          fontWeight: isSelected ? "bold" : "normal",
                          cursor: "pointer",
                          textAlign: "left",
                          boxShadow: isSelected ? "0 0 10px rgba(0, 229, 255, 0.3)" : "none",
                          display: "flex",
                          flexDirection: "column",
                          gap: "2px",
                        }}
                      >
                        <span style={{ fontWeight: "bold" }}>{layer.name}</span>
                        <span style={{ fontSize: "8.5px", color: isSelected ? "#ffffff" : "#64748b" }}>{layer.desc}</span>
                      </button>
                    );
                  })}
                </div>

                {/* SECTION 2: HOLOGRAPHIC COLOR THEMES */}
                <div
                  style={{
                    fontSize: "10px",
                    color: currentTheme.primary,
                    fontFamily: "'Orbitron', monospace",
                    fontWeight: "900",
                    letterSpacing: "1px",
                    marginBottom: "8px",
                    borderTop: "1px solid rgba(255,255,255,0.1)",
                    paddingTop: "10px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span>◤ HUD COLOR PALETTE ◢</span>
                  <span style={{ fontSize: "8.5px", color: "#94a3b8" }}>ACCENT THEME</span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "5px" }}>
                  {FRIDAY_THEME_OPTIONS.map((t) => {
                    const isSelected = fridayTheme === t.id;
                    return (
                      <button
                        key={t.id}
                        onClick={() => {
                          setFridayTheme(t.id);
                          localStorage.setItem("FRIDAY_MAP_THEME", t.id);
                        }}
                        style={{
                          background: isSelected ? `linear-gradient(135deg, ${t.primary}45, ${t.accent}30)` : "rgba(255, 255, 255, 0.03)",
                          border: isSelected ? `1.5px solid ${t.primary}` : "1px solid rgba(255, 255, 255, 0.08)",
                          color: isSelected ? "#ffffff" : "#94a3b8",
                          borderRadius: "4px",
                          padding: "6px 8px",
                          fontSize: "9.5px",
                          fontWeight: isSelected ? "bold" : "normal",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          boxShadow: isSelected ? `0 0 10px ${t.primary}40` : "none",
                        }}
                      >
                        <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: t.primary, boxShadow: `0 0 6px ${t.primary}` }}></span>
                        <span>{t.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Radar & Close Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>

            {/* Google Cloud Maps Platform Integration Config Trigger */}
            <button
              onClick={() => {
                setTempApiKeyInput(googleApiKey);
                setShowGoogleConfigModal(true);
              }}
              style={{
                background: googleApiKey ? "rgba(52, 211, 153, 0.2)" : "rgba(0, 240, 255, 0.15)",
                border: `1px solid ${googleApiKey ? "#34d399" : "rgba(0, 240, 255, 0.4)"}`,
                color: googleApiKey ? "#34d399" : "#00f0ff",
                borderRadius: "5px",
                padding: "5px 10px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "5px",
              }}
              title="Configure Google Cloud Maps Project (gmp-demo-project-951557005)"
            >
              <span>⚙️ G-CLOUD</span>
              <span style={{ fontSize: "8.5px", background: "rgba(0, 240, 255, 0.25)", padding: "1px 4px", borderRadius: "3px" }}>
                {googleApiKey ? "KEY ACTIVE" : "LINKED"}
              </span>
            </button>

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

        {/* Dedicated Navigation Command Bar (Row 2: Single Target Search or Multi-Stop Route Planner) */}
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
            /* Futuristic FRIDAY HUD Single Target Search Bar */
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setSearchResults([]);
                if (!searchQuery.trim()) return;
                setIsSearchingSingle(true);
                geocodeText(searchQuery.trim())
                  .then((results) => {
                    if (results && results.length > 0) {
                      const first = results[0];
                      const lat = parseFloat(first.lat);
                      const lng = parseFloat(first.lon);
                      setSearchResults([]);
                      setSelectedLocationName(first.display_name);
                      setSearchQuery(first.display_name.split(",")[0]);
                      flyToLocation(lat, lng, first.display_name, 14);
                    } else {
                      setSearchResults(results);
                    }
                  })
                  .catch((err) => console.error("Locate target error:", err))
                  .finally(() => setIsSearchingSingle(false));
              }}
              style={{
                display: "flex",
                alignItems: "center",
                flex: "1 1 480px",
                maxWidth: "700px",
                background: "linear-gradient(135deg, rgba(2, 10, 26, 0.98) 0%, rgba(1, 4, 12, 0.98) 100%)",
                border: "1.5px solid #00E5FF",
                borderRadius: "6px",
                padding: "3px 10px",
                boxShadow: "0 0 18px rgba(0, 229, 255, 0.25), inset 0 0 10px rgba(0, 229, 255, 0.08)",
                position: "relative",
                minHeight: "42px",
              }}
            >
              <div
                style={{
                  background: "rgba(0, 229, 255, 0.15)",
                  border: "1px solid #00E5FF",
                  borderRadius: "4px",
                  padding: "2px 8px",
                  fontSize: "10px",
                  color: "#00E5FF",
                  fontFamily: "'Orbitron', monospace",
                  fontWeight: "900",
                  marginRight: "8px",
                  letterSpacing: "1px",
                  whiteSpace: "nowrap",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <span>◤</span>
                <span>RECON // TARGET</span>
                <span>◢</span>
              </div>

              <input
                type="text"
                placeholder="Type any City, State, Country, or Landmark (e.g. Madurai, Tokyo, Paris)..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  searchLocation(e.target.value, setSearchResults, setIsSearchingSingle);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    setSearchResults([]);
                    if (!searchQuery.trim()) return;
                    setIsSearchingSingle(true);
                    geocodeText(searchQuery.trim())
                      .then((results) => {
                        if (results && results.length > 0) {
                          const first = results[0];
                          const lat = parseFloat(first.lat);
                          const lng = parseFloat(first.lon);
                          setSearchResults([]);
                          setSelectedLocationName(first.display_name);
                          setSearchQuery(first.display_name.split(",")[0]);
                          flyToLocation(lat, lng, first.display_name, 14);
                        }
                      })
                      .finally(() => setIsSearchingSingle(false));
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
                  letterSpacing: "0.5px",
                }}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setSearchResults([]);
                  }}
                  style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px", marginRight: "8px" }}
                >
                  ✕
                </button>
              )}
              <button
                type="submit"
                disabled={isSearchingSingle}
                style={{
                  background: "linear-gradient(135deg, rgba(0, 229, 255, 0.4), rgba(0, 184, 212, 0.25))",
                  border: "1.5px solid #00E5FF",
                  color: "#00E5FF",
                  borderRadius: "4px",
                  padding: "6px 14px",
                  fontSize: "11px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 0 12px rgba(0, 229, 255, 0.35)",
                  fontFamily: "'Orbitron', monospace",
                  letterSpacing: "0.5px",
                }}
              >
                {isSearchingSingle ? "SCANNING..." : "⚡ LOCATE"}
              </button>

              {/* Single Search Results Dropdown */}
              {searchResults.length > 0 && (
                <div
                  className="friday-search-dropdown"
                  style={{
                    position: "absolute",
                    top: "calc(100% + 4px)",
                    left: 0,
                    right: 0,
                    background: "rgba(1, 6, 18, 0.98)",
                    border: "1.5px solid #00E5FF",
                    borderRadius: "6px",
                    boxShadow: "0 10px 30px rgba(0, 229, 255, 0.5)",
                    zIndex: 999999,
                    maxHeight: "260px",
                    overflowY: "auto",
                  }}
                >
                  {searchResults.map((res, idx) => (
                    <div
                      key={idx}
                      onClick={() => {
                        const wp: Waypoint = { lat: parseFloat(res.lat), lng: parseFloat(res.lon), name: res.display_name };
                        setSearchQuery(res.display_name.split(",")[0]);
                        setSearchResults([]);
                        flyToLocation(wp.lat, wp.lng, wp.name, 14);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderBottom: "1px solid rgba(0, 229, 255, 0.15)",
                        fontSize: "12px",
                        color: "#e2e8f0",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        fontFamily: "'Share Tech Mono', monospace",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 229, 255, 0.25)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <span style={{ color: "#00E5FF" }}>📍</span>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {res.display_name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </form>
          ) : (
            /* Multi-Stop / Multiple Destinations FRIDAY HUD Route Planner Form */
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setFromResults([]);
                setToResults([]);
                setIntermediateStops((prev) => prev.map((s) => ({ ...s, results: [] })));
                calculateRoute();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                flex: "1 1 760px",
                flexWrap: "wrap",
              }}
            >
              {/* START / ORIGIN Input Box */}
              <div style={{ position: "relative", flex: "1 1 220px", minWidth: "190px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    background: "linear-gradient(135deg, rgba(1, 14, 10, 0.98) 0%, rgba(1, 4, 12, 0.98) 100%)",
                    border: "1.5px solid #00FFC6",
                    borderRadius: "6px",
                    padding: "3px 8px",
                    minHeight: "40px",
                    boxShadow: "0 0 16px rgba(0, 255, 198, 0.25), inset 0 0 8px rgba(0, 255, 198, 0.1)",
                  }}
                >
                  <div
                    style={{
                      background: "rgba(0, 255, 198, 0.15)",
                      border: "1px solid #00FFC6",
                      borderRadius: "3px",
                      padding: "2px 6px",
                      color: "#00FFC6",
                      fontSize: "9.5px",
                      fontFamily: "'Orbitron', monospace",
                      fontWeight: "900",
                      marginRight: "6px",
                      whiteSpace: "nowrap",
                      letterSpacing: "0.5px",
                    }}
                  >
                    ◤ {isSearchingFrom ? "SCANNING..." : "🟢 START"} ◢
                  </div>
                  <input
                    type="text"
                    placeholder="Origin (e.g. Chennai, Salem)..."
                    value={fromQuery}
                    onChange={(e) => {
                      setFromQuery(e.target.value);
                      searchLocation(e.target.value, setFromResults, setIsSearchingFrom);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        setFromResults([]);
                        calculateRoute();
                      }
                    }}
                    style={{ background: "transparent", border: "none", color: "#ffffff", fontSize: "12px", outline: "none", width: "100%", padding: "6px 0", fontFamily: "'Share Tech Mono', monospace" }}
                  />
                  {fromQuery && (
                    <button type="button" onClick={() => { setFromQuery(""); setFromResults([]); setFromWaypoint(null); }} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px" }}>
                      ✕
                    </button>
                  )}
                </div>

                {/* FROM Autocomplete Dropdown */}
                {fromResults.length > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "calc(100% + 4px)",
                      left: 0,
                      right: 0,
                      background: "rgba(1, 8, 14, 0.98)",
                      border: "1.5px solid #00FFC6",
                      borderRadius: "6px",
                      boxShadow: "0 10px 30px rgba(0, 255, 198, 0.5)",
                      zIndex: 999999,
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
                        style={{ padding: "8px 12px", borderBottom: "1px solid rgba(0, 255, 198, 0.2)", fontSize: "11.5px", color: "#e2e8f0", cursor: "pointer", fontFamily: "'Share Tech Mono', monospace" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 255, 198, 0.25)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        🟢 {res.display_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Dynamic Intermediate Waypoint / Stops Inputs */}
              {intermediateStops.map((stop, sIdx) => (
                <div key={stop.id} style={{ position: "relative", flex: "1 1 190px", minWidth: "170px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      background: "linear-gradient(135deg, rgba(2, 12, 24, 0.98) 0%, rgba(1, 4, 12, 0.98) 100%)",
                      border: "1.5px solid #00E5FF",
                      borderRadius: "6px",
                      padding: "3px 8px",
                      minHeight: "40px",
                      boxShadow: "0 0 14px rgba(0, 229, 255, 0.25), inset 0 0 8px rgba(0, 229, 255, 0.1)",
                    }}
                  >
                    <div
                      style={{
                        background: "rgba(0, 229, 255, 0.15)",
                        border: "1px solid #00E5FF",
                        borderRadius: "3px",
                        padding: "2px 5px",
                        color: "#00E5FF",
                        fontSize: "9px",
                        fontFamily: "'Orbitron', monospace",
                        fontWeight: "900",
                        marginRight: "6px",
                        whiteSpace: "nowrap",
                      }}
                    >
                      ◤ 🔵 S{sIdx + 1} ◢
                    </div>
                    <input
                      type="text"
                      placeholder={`Stop ${sIdx + 1} (e.g. Pune)...`}
                      value={stop.query}
                      onChange={(e) => updateStopQuery(stop.id, e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          setIntermediateStops((prev) => prev.map((s) => (s.id === stop.id ? { ...s, results: [] } : s)));
                          calculateRoute();
                        }
                      }}
                      style={{ background: "transparent", border: "none", color: "#ffffff", fontSize: "11.5px", outline: "none", width: "100%", padding: "6px 0", fontFamily: "'Share Tech Mono', monospace" }}
                    />
                    <button
                      type="button"
                      onClick={() => removeIntermediateStop(stop.id)}
                      style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: "12px", marginLeft: "4px" }}
                      title="Remove this waypoint"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Stop Autocomplete Dropdown */}
                  {stop.results && stop.results.length > 0 && (
                    <div
                      style={{
                        position: "absolute",
                        top: "calc(100% + 4px)",
                        left: 0,
                        right: 0,
                        background: "rgba(1, 6, 18, 0.98)",
                        border: "1.5px solid #00E5FF",
                        borderRadius: "6px",
                        boxShadow: "0 10px 25px rgba(0, 229, 255, 0.5)",
                        zIndex: 999999,
                        maxHeight: "220px",
                        overflowY: "auto",
                      }}
                    >
                      {stop.results.map((res, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            const wp: Waypoint = { lat: parseFloat(res.lat), lng: parseFloat(res.lon), name: res.display_name };
                            setIntermediateStops((prev) =>
                              prev.map((s) => (s.id === stop.id ? { ...s, waypoint: wp, query: res.display_name.split(",")[0], results: [] } : s))
                            );
                          }}
                          style={{ padding: "8px 12px", borderBottom: "1px solid rgba(0, 229, 255, 0.2)", fontSize: "11px", color: "#e2e8f0", cursor: "pointer", fontFamily: "'Share Tech Mono', monospace" }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 229, 255, 0.25)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                        >
                          🔵 {res.display_name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* + ADD WAYPOINT Button */}
              <button
                type="button"
                onClick={addIntermediateStop}
                style={{
                  background: "rgba(0, 229, 255, 0.12)",
                  border: "1.5px dashed #00E5FF",
                  color: "#00E5FF",
                  borderRadius: "6px",
                  padding: "0 10px",
                  minHeight: "40px",
                  fontSize: "10.5px",
                  fontFamily: "'Orbitron', monospace",
                  fontWeight: "bold",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 0 10px rgba(0, 229, 255, 0.2)",
                }}
                title="Add intermediate waypoint stop"
              >
                + ADD WAYPOINT
              </button>

              {/* Swap Button */}
              <button
                type="button"
                onClick={swapRoute}
                style={{
                  background: "rgba(0, 229, 255, 0.15)",
                  border: "1.5px solid #00E5FF",
                  color: "#00E5FF",
                  borderRadius: "6px",
                  width: "36px",
                  height: "40px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "bold",
                  flexShrink: 0,
                  boxShadow: "0 0 10px rgba(0, 229, 255, 0.25)",
                }}
                title="Swap Origin and Destination"
              >
                ⇄
              </button>

              {/* DESTINATION / TARGET Input Box */}
              <div style={{ position: "relative", flex: "1 1 220px", minWidth: "190px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    background: "linear-gradient(135deg, rgba(16, 2, 8, 0.98) 0%, rgba(1, 4, 12, 0.98) 100%)",
                    border: "1.5px solid #FF3366",
                    borderRadius: "6px",
                    padding: "3px 8px",
                    minHeight: "40px",
                    boxShadow: "0 0 16px rgba(255, 51, 102, 0.3), inset 0 0 8px rgba(255, 51, 102, 0.1)",
                  }}
                >
                  <div
                    style={{
                      background: "rgba(255, 51, 102, 0.15)",
                      border: "1px solid #FF3366",
                      borderRadius: "3px",
                      padding: "2px 6px",
                      color: "#FF3366",
                      fontSize: "9.5px",
                      fontFamily: "'Orbitron', monospace",
                      fontWeight: "900",
                      marginRight: "6px",
                      whiteSpace: "nowrap",
                      letterSpacing: "0.5px",
                    }}
                  >
                    ◤ {isSearchingTo ? "SCANNING..." : "🔴 DEST"} ◢
                  </div>
                  <input
                    type="text"
                    placeholder="Destination (e.g. Bengaluru, Airport)..."
                    value={toQuery}
                    onChange={(e) => {
                      setToQuery(e.target.value);
                      searchLocation(e.target.value, setToResults, setIsSearchingTo);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        setToResults([]);
                        calculateRoute();
                      }
                    }}
                    style={{ background: "transparent", border: "none", color: "#ffffff", fontSize: "12px", outline: "none", width: "100%", padding: "6px 0", fontFamily: "'Share Tech Mono', monospace" }}
                  />
                  {toQuery && (
                    <button type="button" onClick={() => { setToQuery(""); setToResults([]); setToWaypoint(null); }} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px" }}>
                      ✕
                    </button>
                  )}
                </div>

                {/* TO Autocomplete Dropdown */}
                {toResults.length > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "calc(100% + 4px)",
                      left: 0,
                      right: 0,
                      background: "rgba(16, 2, 8, 0.98)",
                      border: "1.5px solid #FF3366",
                      borderRadius: "6px",
                      boxShadow: "0 10px 30px rgba(255, 51, 102, 0.5)",
                      zIndex: 999999,
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
                          if (fromWaypoint) calculateRoute(fromWaypoint, wp);
                        }}
                        style={{ padding: "8px 12px", borderBottom: "1px solid rgba(255, 51, 102, 0.2)", fontSize: "11.5px", color: "#e2e8f0", cursor: "pointer", fontFamily: "'Share Tech Mono', monospace" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 51, 102, 0.25)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        🔴 {res.display_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Calculate Road Route Action Button */}
              <button
                type="submit"
                disabled={isCalculatingRoute || (!fromQuery.trim() && !toQuery.trim())}
                style={{
                  background: "linear-gradient(135deg, rgba(0, 229, 255, 0.45), rgba(0, 184, 212, 0.3))",
                  border: "1.5px solid #00E5FF",
                  color: "#00E5FF",
                  borderRadius: "6px",
                  padding: "0 16px",
                  minHeight: "40px",
                  fontSize: "11px",
                  fontFamily: "'Orbitron', monospace",
                  fontWeight: "900",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 0 16px rgba(0, 229, 255, 0.4)",
                  letterSpacing: "0.5px",
                  flexShrink: 0,
                }}
              >
                {isCalculatingRoute ? "ROUTING..." : "⚡ CALCULATE ROAD ROUTE"}
              </button>

              {/* Clear Route Button */}
              {(routeInfo || fromWaypoint || toWaypoint || fromQuery || toQuery || intermediateStops.length > 0) && (
                <button
                  type="button"
                  onClick={clearRoute}
                  style={{
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1.5px solid #f87171",
                    color: "#f87171",
                    borderRadius: "6px",
                    padding: "0 10px",
                    minHeight: "40px",
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
        </div>

        {/* Dynamic Route Alternatives Selection Strip (Displays 2 to 3 selectable alternative routes) */}
        {routeAlternatives.length > 0 && (
          <div
            style={{
              background: "linear-gradient(90deg, rgba(2, 10, 26, 0.98), rgba(1, 6, 18, 0.98))",
              borderBottom: "1.5px solid #00E5FF",
              padding: "8px 20px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              overflowX: "auto",
              whiteSpace: "nowrap",
              zIndex: 10,
              fontSize: "11px",
              color: "#ffffff",
              boxShadow: "0 0 20px rgba(0, 229, 255, 0.3)",
              fontFamily: "'Share Tech Mono', monospace",
            }}
          >
            <span style={{ color: "#00FFC6", fontWeight: "bold", letterSpacing: "1px" }}>
              ⚡ SELECT ROUTE CORRIDOR:
            </span>

            {routeAlternatives.map((route) => {
              const isSelected = route.id === selectedRouteId;
              const hrs = Math.floor(route.durationMins / 60);
              const mins = route.durationMins % 60;
              const timeStr = hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;

              return (
                <button
                  key={route.id}
                  type="button"
                  onClick={() => selectActiveRoute(route.id)}
                  style={{
                    background: isSelected ? "linear-gradient(135deg, rgba(0, 229, 255, 0.35), rgba(0, 184, 212, 0.2))" : "rgba(255, 255, 255, 0.05)",
                    border: isSelected ? "1.5px solid #00E5FF" : "1px solid rgba(255, 255, 255, 0.15)",
                    color: isSelected ? "#00E5FF" : "#94a3b8",
                    borderRadius: "6px",
                    padding: "6px 12px",
                    fontSize: "11px",
                    fontWeight: isSelected ? "bold" : "normal",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    boxShadow: isSelected ? "0 0 14px rgba(0, 229, 255, 0.4)" : "none",
                    transition: "all 0.2s ease",
                  }}
                >
                  <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: isSelected ? "#00E5FF" : "#64748b", boxShadow: isSelected ? "0 0 8px #00E5FF" : "none" }} />
                  <span>{route.name}</span>
                  <span style={{ color: isSelected ? "#ffffff" : "#64748b", background: "rgba(0,0,0,0.3)", padding: "1px 6px", borderRadius: "3px" }}>
                    {route.distanceKm} km • {timeStr}
                  </span>
                </button>
              );
            })}

            <div style={{ marginLeft: "auto", color: "#64748b", fontSize: "10px" }}>
              CLICK ANY TAB OR MAP PATH TO SWITCH CORRIDOR
            </div>
          </div>
        )}

        {/* Main Layered Viewport Container (3D Holographic Globe + 2D Tactical Map) */}
        <div style={{ position: "relative", width: "100%", height: "100%", flex: 1, minHeight: 0, overflow: "hidden" }}>
          {/* 3D Holographic Earth Globe Layer */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: projectionMode === "globe_3d" ? 1 : 0,
              pointerEvents: projectionMode === "globe_3d" ? "auto" : "none",
              transition: "opacity 0.4s ease, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1)",
              transform: isTransitioning && transitionType === "dive" ? "scale(1.25)" : "scale(1)",
              zIndex: projectionMode === "globe_3d" ? 2 : 1,
            }}
          >
            <HoloGlobe3D
              selectedRegion={selectedRegion}
              initialLat={currentCoords.lat}
              initialLng={currentCoords.lng}
              isHybridMode={isHybridMode}
              isActive={projectionMode === "globe_3d"}
              onSectorSelect={(name, lat, lng) => {
                setSelectedLocationName(name);
                setCurrentCoords({ lat, lng });
              }}
              onDiveIn={(lat, lng, locName) => {
                flyToLocation(lat, lng, locName || "TACTICAL SECTOR", 12);
              }}
              onZoomChange={(zoom) => {
                setCurrentZoom(Math.round(zoom));
              }}
            />
          </div>

          {/* 2D Tactical Leaflet Map Container with Dynamic Theme */}
          <div
            ref={mapContainerRef}
            className={`friday-map-viewport map-theme-${fridayTheme}`}
            style={{
              position: "absolute",
              inset: 0,
              background: currentTheme.bg,
              opacity: projectionMode === "tactical_2d" ? 1 : 0,
              pointerEvents: projectionMode === "tactical_2d" ? "auto" : "none",
              transition: "opacity 0.4s ease, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1)",
              transform: isTransitioning && transitionType === "pullback" ? "scale(0.85)" : "scale(1)",
              zIndex: projectionMode === "tactical_2d" ? 2 : 1,
            }}
          />

          {/* Seamless Warp Transition FX between 3D Globe and 2D Map */}
          {isTransitioning && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                zIndex: 99999,
                background: "radial-gradient(circle at 50% 50%, rgba(0, 240, 255, 0.25) 0%, rgba(1, 4, 9, 0.95) 75%)",
                backdropFilter: "blur(8px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "14px",
                pointerEvents: "none",
                animation: "fadeIn 0.2s ease-out",
              }}
            >
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "50%",
                  border: "2px dashed #00f0ff",
                  animation: "rotateArc 1.2s linear infinite",
                  boxShadow: "0 0 25px #00f0ff",
                }}
              />
              <div style={{ fontFamily: "'Orbitron', monospace", fontSize: "14px", color: "#00f0ff", letterSpacing: "2px", fontWeight: "900", textShadow: "0 0 12px #00f0ff" }}>
                {transitionType === "dive" ? "TACTICAL DIVE ENGAGED" : "ORBITAL PULLBACK"}
              </div>
              <div style={{ fontSize: "11px", color: "#8ab4f8", fontFamily: "'Share Tech Mono', monospace", letterSpacing: "1px" }}>
                TARGET // {transitionTargetLabel.toUpperCase()}
              </div>
            </div>
          )}

          {/* 2D TACTICAL MAP OVERLAYS (ONLY VISIBLE IN 2D MODE) */}
          {projectionMode === "tactical_2d" && (
            <>
              {/* Subtle Tactical HUD Corner Brackets */}
              <div className="friday-hud-corner-tl" />
              <div className="friday-hud-corner-tr" />
              <div className="friday-hud-corner-bl" />
              <div className="friday-hud-corner-br" />

              {/* Tactical Matrix Coordinate Grid Overlay */}
              <div className="friday-tactical-grid-overlay" />

              {/* Futuristic Friday Tactical Overlay: Concentric Targeting Reticles & GPU Animated Radar Beam */}
              {isRadarSweeping && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    pointerEvents: "none",
                    zIndex: 3,
                    overflow: "hidden",
                  }}
                >
                  <svg width="100%" height="100%">
                    {/* Center Tactical Reticle */}
                    <circle cx="50%" cy="50%" r="45" fill="none" stroke={currentTheme.primary} strokeWidth="1.2" strokeDasharray="4 4" opacity="0.35" />
                    <circle cx="50%" cy="50%" r="160" fill="none" stroke={currentTheme.primary} strokeWidth="0.8" strokeDasharray="6 8" opacity="0.2" />
                    <circle cx="50%" cy="50%" r="300" fill="none" stroke={currentTheme.primary} strokeWidth="0.6" opacity="0.12" />
                    
                    {/* Crosshair Axes */}
                    <line x1="0" y1="50%" x2="100%" y2="50%" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="0.8" />
                    <line x1="50%" y1="0" x2="50%" y2="100%" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="0.8" />

                    {/* Hardware Accelerated Radar Rotating Beam (0 React re-renders) */}
                    <g
                      style={{
                        transformOrigin: "50% 50%",
                        animation: "rotateArc 3.5s linear infinite",
                      }}
                    >
                      <line
                        x1="50%"
                        y1="50%"
                        x2="100%"
                        y2="50%"
                        stroke={currentTheme.primary}
                        strokeWidth="1.5"
                        opacity="0.6"
                        style={{ filter: `drop-shadow(0 0 6px ${currentTheme.primary})` }}
                      />
                    </g>
                  </svg>
                </div>
              )}

              {/* Floating Top-Right "● SECTOR DETAILS" HUD Panel */}
              <div style={{ position: "absolute", top: "16px", right: "16px", zIndex: 10, display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                {!showSectorDetails ? (
                  <button
                    onClick={() => setShowSectorDetails(true)}
                    className="jarvis-glass-card"
                    style={{
                      background: "rgba(2, 5, 10, 0.9)",
                      border: `1px solid ${currentTheme.primary}80`,
                      color: currentTheme.primary,
                      borderRadius: "4px",
                      padding: "6px 12px",
                      fontSize: "10px",
                      fontWeight: "bold",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "7px",
                      boxShadow: `0 0 12px ${currentTheme.primary}25`,
                      backdropFilter: "blur(12px)",
                      letterSpacing: "1px",
                      fontFamily: "'Share Tech Mono', monospace",
                    }}
                    title="Expand FRIDAY Sector Telemetry Details"
                  >
                    <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#00FFC6", boxShadow: "0 0 8px #00FFC6" }} />
                    <span>● SECTOR DETAILS</span>
                    <span style={{ fontSize: "8px", opacity: 0.7 }}>▼</span>
                  </button>
                ) : (
                  <div
                    className="jarvis-glass-card"
                    style={{
                      background: "rgba(2, 5, 10, 0.95)",
                      border: `1px solid ${currentTheme.primary}`,
                      borderRadius: "6px",
                      padding: "12px 16px",
                      color: "#ffffff",
                      boxShadow: `0 0 25px ${currentTheme.primary}35`,
                      minWidth: "260px",
                      maxWidth: "380px",
                      backdropFilter: "blur(16px)",
                      animation: "fadeIn 0.2s ease-out",
                      fontFamily: "'Share Tech Mono', monospace",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${currentTheme.primary}30`, paddingBottom: "6px", marginBottom: "10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#00FFC6", boxShadow: "0 0 8px #00FFC6" }} />
                        <span style={{ fontSize: "11px", color: currentTheme.primary, fontWeight: "bold", letterSpacing: "1.5px" }}>
                          ● SECTOR DETAILS
                        </span>
                      </div>
                      <button
                        onClick={() => setShowSectorDetails(false)}
                        style={{ background: "transparent", border: "none", color: "#64748b", cursor: "pointer", fontSize: "12px", padding: "0 4px" }}
                        title="Collapse Details"
                      >
                        ✕
                      </button>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748b" }}>LAT</span>
                        <strong style={{ color: "#00E5FF" }}>{currentCoords.lat > 0 ? `${currentCoords.lat.toFixed(2)}° N` : `${Math.abs(currentCoords.lat).toFixed(2)}° S`}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748b" }}>LONG</span>
                        <strong style={{ color: "#00E5FF" }}>{currentCoords.lng > 0 ? `${currentCoords.lng.toFixed(2)}° E` : `${Math.abs(currentCoords.lng).toFixed(2)}° W`}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
                        <span style={{ color: "#64748b" }}>REGION</span>
                        <strong style={{ color: "#ffffff", textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {selectedLocationName.split(",")[0].toUpperCase()}
                        </strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748b" }}>STATUS</span>
                        <strong style={{ color: "#00FFC6" }}>{routeInfo ? "ROUTING" : "ACTIVE"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", borderTop: `1px dashed ${currentTheme.primary}25`, paddingTop: "5px", marginTop: "2px" }}>
                        <span style={{ color: "#64748b" }}>RESOLUTION</span>
                        <strong style={{ color: currentTheme.primary }}>{currentZoom}x TACTICAL</strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Floating Right Tactical Zoom & Level Presets Toolbar */}
              <div
                style={{
                  position: "absolute",
                  bottom: "24px",
                  right: "20px",
                  zIndex: 10,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                  gap: "6px",
                  fontFamily: "'Share Tech Mono', monospace",
                }}
              >
                {/* Quick Level Preset Jump Buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: "4px", background: "rgba(2, 5, 10, 0.92)", border: "1px solid rgba(0, 229, 255, 0.35)", borderRadius: "4px", padding: "5px", boxShadow: "0 0 15px rgba(0, 229, 255, 0.15)" }}>
                  <button
                    onClick={() => { if (mapInstanceRef.current) mapInstanceRef.current.setZoom(18); }}
                    style={{
                      background: currentZoom >= 17 ? "rgba(0, 229, 255, 0.25)" : "transparent",
                      border: currentZoom >= 17 ? "1px solid #00E5FF" : "1px solid transparent",
                      color: currentZoom >= 17 ? "#00E5FF" : "#64748b",
                      fontSize: "9.5px",
                      padding: "4px 8px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontWeight: "bold",
                      textAlign: "left",
                    }}
                    title="Street & Building Footprint Level (18x)"
                  >
                    🛣️ STREET 18x
                  </button>
                  <button
                    onClick={() => { if (mapInstanceRef.current) mapInstanceRef.current.setZoom(14); }}
                    style={{
                      background: currentZoom >= 13 && currentZoom < 17 ? "rgba(0, 229, 255, 0.25)" : "transparent",
                      border: currentZoom >= 13 && currentZoom < 17 ? "1px solid #00E5FF" : "1px solid transparent",
                      color: currentZoom >= 13 && currentZoom < 17 ? "#00E5FF" : "#64748b",
                      fontSize: "9.5px",
                      padding: "4px 8px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontWeight: "bold",
                      textAlign: "left",
                    }}
                    title="City & Area Level (14x)"
                  >
                    🏙️ CITY 14x
                  </button>
                  <button
                    onClick={() => { if (mapInstanceRef.current) mapInstanceRef.current.setZoom(8); }}
                    style={{
                      background: currentZoom >= 7 && currentZoom < 13 ? "rgba(0, 229, 255, 0.25)" : "transparent",
                      border: currentZoom >= 7 && currentZoom < 13 ? "1px solid #00E5FF" : "1px solid transparent",
                      color: currentZoom >= 7 && currentZoom < 13 ? "#00E5FF" : "#64748b",
                      fontSize: "9.5px",
                      padding: "4px 8px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontWeight: "bold",
                      textAlign: "left",
                    }}
                    title="State & Province Level (8x)"
                  >
                    🗺️ STATE 8x
                  </button>
                  <button
                    onClick={() => { if (mapInstanceRef.current) mapInstanceRef.current.setZoom(4); }}
                    style={{
                      background: currentZoom < 7 ? "rgba(0, 229, 255, 0.25)" : "transparent",
                      border: currentZoom < 7 ? "1px solid #00E5FF" : "1px solid transparent",
                      color: currentZoom < 7 ? "#00E5FF" : "#64748b",
                      fontSize: "9.5px",
                      padding: "4px 8px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontWeight: "bold",
                      textAlign: "left",
                    }}
                    title="Country & Continent Overview (4x)"
                  >
                    🌍 NATION 4x
                  </button>
                </div>

                {/* Minimalist FRIDAY HUD Zoom Panel */}
                <div style={{ display: "flex", gap: "4px", background: "rgba(2, 5, 10, 0.92)", border: "1px solid rgba(0, 229, 255, 0.4)", borderRadius: "4px", padding: "2px" }}>
                  <button
                    onClick={handleZoomIn}
                    style={{
                      width: "32px",
                      height: "32px",
                      background: "transparent",
                      border: "none",
                      color: "#00E5FF",
                      fontSize: "18px",
                      fontWeight: "bold",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title="Zoom In (+)"
                  >
                    +
                  </button>
                  <div style={{ width: "1px", background: "rgba(0, 229, 255, 0.3)" }} />
                  <button
                    onClick={handleZoomOut}
                    style={{
                      width: "32px",
                      height: "32px",
                      background: "transparent",
                      border: "none",
                      color: "#00E5FF",
                      fontSize: "18px",
                      fontWeight: "bold",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title="Zoom Out (-)"
                  >
                    −
                  </button>
                </div>
              </div>

              {/* Floating Bottom FRIDAY Telemetry Status Bar */}
              <div
                className="jarvis-glass-card"
                style={{
                  position: "absolute",
                  bottom: "16px",
                  left: "20px",
                  zIndex: 10,
                  padding: "7px 18px",
                  fontSize: "11px",
                  color: "#00E5FF",
                  display: "flex",
                  gap: "20px",
                  border: "1px solid rgba(0, 229, 255, 0.35)",
                  boxShadow: "0 0 15px rgba(0, 229, 255, 0.15)",
                  background: "rgba(2, 5, 10, 0.92)",
                  fontFamily: "'Share Tech Mono', monospace",
                  letterSpacing: "0.5px",
                }}
              >
                <div>
                  <span style={{ color: "#64748b" }}>CURSOR:</span> {cursorCoords ? `${cursorCoords.lat > 0 ? `${cursorCoords.lat.toFixed(4)}° N` : `${Math.abs(cursorCoords.lat).toFixed(4)}° S`} ${cursorCoords.lng > 0 ? `${cursorCoords.lng.toFixed(4)}° E` : `${Math.abs(cursorCoords.lng).toFixed(4)}° W`}` : "---"}
                </div>
                <div>
                  <span style={{ color: "#64748b" }}>CENTER:</span> {currentCoords.lat > 0 ? `${currentCoords.lat.toFixed(4)}° N` : `${Math.abs(currentCoords.lat).toFixed(4)}° S`} {currentCoords.lng > 0 ? `${currentCoords.lng.toFixed(4)}° E` : `${Math.abs(currentCoords.lng).toFixed(4)}° W`}
                </div>
                <div>
                  <span style={{ color: "#64748b" }}>STATUS:</span>{" "}
                  <strong style={{ color: routeInfo ? "#00E5FF" : "#38bdf8" }}>
                    {routeInfo ? `TACTICAL ROUTING (${routeInfo.distanceKm} KM)` : "TACTICAL SCANNING"}
                  </strong>
                </div>
                <div style={{ color: "#00FFC6", fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#00FFC6", boxShadow: "0 0 6px #00FFC6", display: "inline-block" }}></span>
                  FRIDAY GEOSPATIAL ROUTER ACTIVE
                </div>
              </div>
            </>
          )}

          {/* Google Cloud Platform Configuration Modal */}
          {showGoogleConfigModal && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "rgba(1, 4, 9, 0.85)",
                backdropFilter: "blur(14px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 99999,
                padding: "20px",
              }}
              onClick={() => setShowGoogleConfigModal(false)}
            >
              <div
                className="jarvis-glass-card"
                style={{
                  width: "100%",
                  maxWidth: "520px",
                  background: "rgba(2, 10, 26, 0.98)",
                  border: "1.5px solid #00f0ff",
                  borderRadius: "10px",
                  padding: "24px",
                  boxShadow: "0 0 40px rgba(0, 240, 255, 0.35)",
                  color: "#ffffff",
                  fontFamily: "'Inter', sans-serif",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(0, 240, 255, 0.3)", paddingBottom: "12px", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#00f0ff", boxShadow: "0 0 12px #00f0ff" }} />
                    <span style={{ fontFamily: "'Orbitron', monospace", fontSize: "13px", fontWeight: "bold", color: "#00f0ff", letterSpacing: "1px" }}>
                      GOOGLE CLOUD MAPS PLATFORM
                    </span>
                  </div>
                  <button
                    onClick={() => setShowGoogleConfigModal(false)}
                    style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "16px" }}
                  >
                    ✕
                  </button>
                </div>

                <div style={{ background: "rgba(0, 240, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px", padding: "12px", marginBottom: "16px", fontSize: "11.5px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ color: "#94a3b8" }}>LINKED PROJECT:</span>
                    <strong style={{ color: "#34d399", fontFamily: "monospace" }}>gmp-demo-project-951557005</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ color: "#94a3b8" }}>FRIDAY CYBER ENGINE:</span>
                    <strong style={{ color: "#00f0ff" }}>ACTIVE & LIVE (ZERO KEY NEEDED)</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#94a3b8" }}>MAX ZOOM RESOLUTION:</span>
                    <strong style={{ color: "#facc15" }}>22x ULTRA PRECISION</strong>
                  </div>
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "11px", color: "#8ab4f8", marginBottom: "6px", fontWeight: "bold", letterSpacing: "0.5px" }}>
                    GOOGLE MAPS API KEY (OPTIONAL):
                  </label>
                  <input
                    type="text"
                    placeholder="AIzaSy... (Paste API Key if created in Cloud Console)"
                    value={tempApiKeyInput}
                    onChange={(e) => setTempApiKeyInput(e.target.value)}
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      background: "#010712",
                      border: "1.5px solid rgba(0, 240, 255, 0.5)",
                      borderRadius: "6px",
                      padding: "10px 12px",
                      color: "#ffffff",
                      fontSize: "12px",
                      fontFamily: "monospace",
                      outline: "none",
                      boxShadow: "inset 0 0 10px rgba(0, 240, 255, 0.15)",
                    }}
                  />
                  <span style={{ fontSize: "10px", color: "#64748b", marginTop: "4px", display: "block" }}>
                    Google Maps high-resolution tiles work immediately in Friday Cyber Dark theme. Adding your project API key connects your Google Cloud quota and billing metrics.
                  </span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", marginTop: "20px" }}>
                  <a
                    href="https://console.cloud.google.com/google/maps-apis/discover?project=gmp-demo-project-951557005&authuser=1&hl=en-IN"
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      color: "#38bdf8",
                      padding: "8px 14px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      textDecoration: "none",
                      fontWeight: "bold",
                    }}
                  >
                    Console Project ↗
                  </a>

                  <div style={{ display: "flex", gap: "8px" }}>
                    {googleApiKey && (
                      <button
                        onClick={() => {
                          localStorage.removeItem("FRIDAY_GMP_API_KEY");
                          setGoogleApiKey("");
                          setTempApiKeyInput("");
                        }}
                        style={{
                          background: "rgba(239, 68, 68, 0.2)",
                          border: "1px solid #f87171",
                          color: "#f87171",
                          padding: "8px 12px",
                          borderRadius: "6px",
                          fontSize: "11px",
                          cursor: "pointer",
                          fontWeight: "bold",
                        }}
                      >
                        Clear Key
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const trimmed = tempApiKeyInput.trim();
                        if (trimmed) {
                          localStorage.setItem("FRIDAY_GMP_API_KEY", trimmed);
                          setGoogleApiKey(trimmed);
                        } else {
                          localStorage.removeItem("FRIDAY_GMP_API_KEY");
                          setGoogleApiKey("");
                        }
                        setShowGoogleConfigModal(false);
                      }}
                      style={{
                        background: "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.35))",
                        border: "1.5px solid #00f0ff",
                        color: "#00f0ff",
                        padding: "8px 18px",
                        borderRadius: "6px",
                        fontSize: "11px",
                        fontWeight: "bold",
                        cursor: "pointer",
                        boxShadow: "0 0 15px rgba(0, 240, 255, 0.3)",
                      }}
                    >
                      Save & Activate
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

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
