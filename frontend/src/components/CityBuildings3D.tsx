/**
 * Friday AI Assistant - 3D Real Metropolis & Skyscraper Architecture Component
 * ============================================================================
 * High-density Three.js WebGL 3D urban metropolis with architectural landmark spires,
 * illuminated glass window grids, skybridges, animated highway traffic light flows,
 * search geocoder, state-preserving rotation controls, and interactive building telemetry.
 */

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

export interface CityBuildings3DProps {
  currentSectorName?: string;
}

interface RealCityBlueprint {
  id: string;
  name: string;
  country: string;
  lat: number;
  lng: number;
  density: number;
  tallestMeters: number;
  accentColor: string;
  landmarks: {
    name: string;
    heightM: number;
    floors: number;
    type: string;
    relX: number;
    relZ: number;
    archetype?: "spire" | "stepped" | "cylinder" | "twin";
  }[];
}

const REAL_CITY_BLUEPRINTS: RealCityBlueprint[] = [
  {
    id: "chennai",
    name: "CHENNAI METROPOLITAN",
    country: "INDIA",
    lat: 13.0827,
    lng: 80.2707,
    density: 220,
    tallestMeters: 320,
    accentColor: "#00f0ff",
    landmarks: [
      { name: "TIDEL QUANTUM PARK", heightM: 165, floors: 42, type: "TECH CORRIDOR HUB", relX: 0, relZ: 0, archetype: "spire" },
      { name: "LIC TACTICAL TOWER", heightM: 195, floors: 48, type: "HISTORIC PINNACLE", relX: -2, relZ: 1, archetype: "stepped" },
      { name: "CHENNAI CENTRAL TERMINAL", heightM: 95, floors: 22, type: "TRANSIT NEXUS", relX: 2, relZ: -2, archetype: "cylinder" },
      { name: "EXPRESS AVENUE MEGA-NODE", heightM: 130, floors: 32, type: "COMMERCIAL CORE", relX: -1, relZ: -3, archetype: "twin" },
      { name: "GUINDY TECH TOWERS", heightM: 155, floors: 38, type: "AI RESEARCH PARK", relX: 3, relZ: 2, archetype: "spire" },
    ],
  },
  {
    id: "bengaluru",
    name: "BENGALURU AI MATRIX",
    country: "INDIA",
    lat: 12.9716,
    lng: 77.5946,
    density: 240,
    tallestMeters: 310,
    accentColor: "#34d399",
    landmarks: [
      { name: "UB CITY TACTICAL SPIRE", heightM: 148, floors: 38, type: "FINANCIAL HUB", relX: 0, relZ: 0, archetype: "spire" },
      { name: "WORLD TRADE CENTER BENGALURU", heightM: 180, floors: 45, type: "GLOBAL COMMERCE", relX: -2, relZ: -1, archetype: "stepped" },
      { name: "ELECTRONIC CITY NEXUS", heightM: 160, floors: 40, type: "QUANTUM HARDWARE", relX: 2, relZ: 2, archetype: "twin" },
      { name: "MANYATA EMBASSY AI PARK", heightM: 140, floors: 35, type: "DEFENSE TECH", relX: 1, relZ: -3, archetype: "cylinder" },
    ],
  },
  {
    id: "mumbai",
    name: "MUMBAI FINANCIAL CAPITAL",
    country: "INDIA",
    lat: 19.076,
    lng: 72.8777,
    density: 280,
    tallestMeters: 442,
    accentColor: "#facc15",
    landmarks: [
      { name: "WORLD ONE SUPER-TALL", heightM: 442, floors: 110, type: "PRIMARY SPIRE", relX: 0, relZ: 0, archetype: "spire" },
      { name: "BKC FINANCIAL NEXUS", heightM: 240, floors: 60, type: "BANKING CORE", relX: 2, relZ: -1, archetype: "stepped" },
      { name: "BOMBAY STOCK EXCHANGE", heightM: 176, floors: 44, type: "EQUITIES EXCHANGE", relX: -2, relZ: 2, archetype: "cylinder" },
      { name: "BANDRA-WORLI COMM TOWER", heightM: 220, floors: 55, type: "TELEMETRY ARRAY", relX: -1, relZ: -3, archetype: "twin" },
    ],
  },
  {
    id: "delhi",
    name: "NEW DELHI DEFENSE SECTOR",
    country: "INDIA",
    lat: 28.6139,
    lng: 77.209,
    density: 210,
    tallestMeters: 260,
    accentColor: "#38bdf8",
    landmarks: [
      { name: "CONNAUGHT PLACE RADAR CORE", heightM: 130, floors: 32, type: "CENTRAL COMMAND", relX: 0, relZ: 0, archetype: "cylinder" },
      { name: "AEROCITY CYBER TOWER", heightM: 150, floors: 38, type: "TRANSIT SECURITY", relX: 2, relZ: 2, archetype: "spire" },
      { name: "NEHRU PLACE DATA COMPLEX", heightM: 180, floors: 45, type: "HARDWARE MATRIX", relX: -2, relZ: -2, archetype: "stepped" },
    ],
  },
  {
    id: "manhattan",
    name: "NEW YORK MANHATTAN",
    country: "USA",
    lat: 40.7128,
    lng: -74.006,
    density: 320,
    tallestMeters: 541,
    accentColor: "#38bdf8",
    landmarks: [
      { name: "ONE WORLD TRADE CENTER", heightM: 541, floors: 104, type: "COMMAND MEGA-SPIRE", relX: 0, relZ: 0, archetype: "spire" },
      { name: "EMPIRE STATE BUILDING", heightM: 443, floors: 102, type: "COMMUNICATIONS BEACON", relX: -1, relZ: 2, archetype: "stepped" },
      { name: "CHRYSLER TACTICAL TOWER", heightM: 319, floors: 77, type: "STRATEGIC ARRAY", relX: 2, relZ: -1, archetype: "spire" },
      { name: "432 PARK AVENUE", heightM: 426, floors: 85, type: "QUANTUM GRID NODE", relX: 1, relZ: 3, archetype: "twin" },
    ],
  },
  {
    id: "tokyo",
    name: "TOKYO SHIBUYA / SHINJUKU",
    country: "JAPAN",
    lat: 35.6762,
    lng: 139.6503,
    density: 300,
    tallestMeters: 450,
    accentColor: "#f43f5e",
    landmarks: [
      { name: "TOKYO TOWER BEACON", heightM: 333, floors: 75, type: "OPTICAL RELAY", relX: 0, relZ: 0, archetype: "spire" },
      { name: "SHIBUYA SKY COMPLEX", heightM: 250, floors: 62, type: "NEURAL TRANSIT", relX: -2, relZ: 1, archetype: "stepped" },
      { name: "TOKYO METROPOLITAN TOWER", heightM: 263, floors: 66, type: "GOVERNMENT NODE", relX: 2, relZ: -2, archetype: "twin" },
      { name: "ROPPONGI HILLS AI CORE", heightM: 248, floors: 62, type: "FINANCIAL MATRIX", relX: -1, relZ: -3, archetype: "cylinder" },
    ],
  },
  {
    id: "dubai",
    name: "DUBAI DOWNTOWN MATRIX",
    country: "UAE",
    lat: 25.2048,
    lng: 55.2708,
    density: 230,
    tallestMeters: 828,
    accentColor: "#f59e0b",
    landmarks: [
      { name: "BURJ KHALIFA MEGA-SPIRE", heightM: 828, floors: 163, type: "GLOBAL PINNACLE", relX: 0, relZ: 0, archetype: "spire" },
      { name: "PRINCESS TOWER", heightM: 414, floors: 101, type: "STRATEGIC NODE", relX: -2, relZ: 2, archetype: "stepped" },
      { name: "MARINA 101 APEX", heightM: 425, floors: 101, type: "OCEANIC SENSOR", relX: 2, relZ: -2, archetype: "twin" },
    ],
  },
  {
    id: "london",
    name: "LONDON CITY FINANCIAL CORE",
    country: "UK",
    lat: 51.5074,
    lng: -0.1278,
    density: 220,
    tallestMeters: 310,
    accentColor: "#00f0ff",
    landmarks: [
      { name: "THE SHARD NEURAL APEX", heightM: 310, floors: 87, type: "TACTICAL CORE", relX: 0, relZ: 0, archetype: "spire" },
      { name: "22 BISHOPSGATE", heightM: 278, floors: 62, type: "BANKING MATRIX", relX: -1, relZ: 2, archetype: "stepped" },
      { name: "THE GHERKIN (30 ST MARY AXE)", heightM: 180, floors: 41, type: "INSURANCE NODE", relX: 2, relZ: -1, archetype: "cylinder" },
    ],
  },
  {
    id: "singapore",
    name: "SINGAPORE MARINA BAY",
    country: "SINGAPORE",
    lat: 1.3521,
    lng: 103.8198,
    density: 250,
    tallestMeters: 300,
    accentColor: "#a855f7",
    landmarks: [
      { name: "MARINA BAY SANDS TRIAD", heightM: 210, floors: 58, type: "MARITIME RADAR", relX: 0, relZ: 0, archetype: "twin" },
      { name: "GUOCO TOWER APEX", heightM: 290, floors: 68, type: "FINANCIAL SPIRE", relX: -2, relZ: 1, archetype: "spire" },
      { name: "ONE RAFFLES PLACE", heightM: 280, floors: 63, type: "TRADE EXCHANGE", relX: 2, relZ: -2, archetype: "stepped" },
    ],
  },
];

type CameraPreset = "isometric" | "street" | "topdown" | "flyby";

export const CityBuildings3D: React.FC<CityBuildings3DProps> = ({ currentSectorName }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeCity, setActiveCity] = useState<RealCityBlueprint>(() => {
    if (currentSectorName) {
      const match = REAL_CITY_BLUEPRINTS.find(
        (c) =>
          c.name.toLowerCase().includes(currentSectorName.toLowerCase()) ||
          c.country.toLowerCase().includes(currentSectorName.toLowerCase())
      );
      if (match) return match;
    }
    return REAL_CITY_BLUEPRINTS[0];
  });

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [customLocationName, setCustomLocationName] = useState<string | null>(null);

  // Live Control States
  const [wireframeMode, setWireframeMode] = useState<boolean>(false);
  const [cameraMode, setCameraMode] = useState<CameraPreset>("isometric");
  const [autoRotate, setAutoRotate] = useState<boolean>(false);
  const [scanlineActive, setScanlineActive] = useState<boolean>(true);
  const [selectedBuilding, setSelectedBuilding] = useState<{
    id: number;
    name: string;
    heightM: number;
    floors: number;
    status: string;
    energyMw: number;
    lat: number;
    lng: number;
  } | null>(null);

  // Live refs to preserve rotation & camera angles on toggle
  const autoRotateRef = useRef<boolean>(false);
  const scanlineActiveRef = useRef<boolean>(true);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const cityGroupRef = useRef<THREE.Group | null>(null);
  const scanPlaneRef = useRef<THREE.Mesh | null>(null);
  const highlightBoxRef = useRef<THREE.BoxHelper | null>(null);
  const solidMatRef = useRef<THREE.MeshStandardMaterial | null>(null);

  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  useEffect(() => {
    scanlineActiveRef.current = scanlineActive;
    if (scanPlaneRef.current) {
      scanPlaneRef.current.visible = scanlineActive;
    }
  }, [scanlineActive]);

  useEffect(() => {
    if (solidMatRef.current) {
      solidMatRef.current.wireframe = wireframeMode;
      solidMatRef.current.needsUpdate = true;
    }
  }, [wireframeMode]);

  // Search any city in the world
  const handleSearchCity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);

    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery.trim())}&limit=1&addressdetails=1`
      );
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.length > 0) {
          const item = data[0];
          const lat = parseFloat(item.lat);
          const lon = parseFloat(item.lon);
          const displayName = item.display_name;

          const matched = REAL_CITY_BLUEPRINTS.find(
            (b) =>
              displayName.toLowerCase().includes(b.id) ||
              displayName.toLowerCase().includes(b.name.split(" ")[0].toLowerCase())
          );

          if (matched) {
            setActiveCity(matched);
            setCustomLocationName(null);
          } else {
            const customCity: RealCityBlueprint = {
              id: "custom",
              name: displayName.split(",")[0].toUpperCase() + " SECTOR",
              country: item.address?.country?.toUpperCase() || "GLOBAL",
              lat,
              lng: lon,
              density: 230,
              tallestMeters: 380,
              accentColor: "#00f0ff",
              landmarks: [
                { name: `${displayName.split(",")[0].toUpperCase()} CENTRAL CORE`, heightM: 320, floors: 80, type: "PRIMARY HUB", relX: 0, relZ: 0, archetype: "spire" },
                { name: `${item.address?.suburb || "NORTH"} NODE`, heightM: 220, floors: 55, type: "COMM ARRAY", relX: -2, relZ: 1, archetype: "stepped" },
                { name: `${item.address?.city || "SOUTH"} TOWER`, heightM: 260, floors: 65, type: "DATA NEXUS", relX: 2, relZ: -2, archetype: "cylinder" },
              ],
            };
            setActiveCity(customCity);
            setCustomLocationName(displayName);
          }
          setSelectedBuilding(null);
        }
      }
    } catch (err) {
      console.warn("City geocode error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  // Camera presets
  const applyCameraPreset = (preset: CameraPreset) => {
    setCameraMode(preset);
    const camera = cameraRef.current;
    if (!camera) return;

    if (preset === "isometric") {
      camera.position.set(160, 140, 190);
      camera.lookAt(0, 35, 0);
    } else if (preset === "street") {
      camera.position.set(40, 16, 80);
      camera.lookAt(0, 60, 0);
    } else if (preset === "topdown") {
      camera.position.set(0, 340, 10);
      camera.lookAt(0, 0, 0);
    } else if (preset === "flyby") {
      camera.position.set(120, 90, 140);
      camera.lookAt(0, 30, 0);
    }
  };

  // Build 3D City Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let width = container.clientWidth || 800;
    let height = container.clientHeight || 550;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x010714, 0.0022);

    const camera = new THREE.PerspectiveCamera(48, width / height, 1, 4000);
    camera.position.set(160, 140, 190);
    camera.lookAt(0, 35, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x010714, 1);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 2. Multi-Directional Cyber Lighting
    const ambientLight = new THREE.AmbientLight(0x0a223f, 1.8);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(new THREE.Color(activeCity.accentColor), 2.2);
    dirLight1.position.set(250, 400, 250);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 1.2);
    dirLight2.position.set(-250, 250, -250);
    scene.add(dirLight2);

    const hemiLight = new THREE.HemisphereLight(0x00f0ff, 0x010613, 0.8);
    scene.add(hemiLight);

    // 3. City Group
    const cityGroup = new THREE.Group();
    scene.add(cityGroup);
    cityGroupRef.current = cityGroup;

    // Procedural Window Grid Texture
    const createBuildingTexture = (accentHex: string) => {
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 512;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.fillStyle = "#021124";
        ctx.fillRect(0, 0, 256, 512);

        // Windows Pattern
        ctx.fillStyle = accentHex;
        for (let y = 10; y < 500; y += 16) {
          for (let x = 10; x < 246; x += 14) {
            if (Math.random() > 0.28) {
              const brightness = Math.random();
              if (brightness > 0.85) {
                ctx.fillStyle = "#ffffff";
                ctx.globalAlpha = 0.95;
              } else if (brightness > 0.4) {
                ctx.fillStyle = accentHex;
                ctx.globalAlpha = 0.85;
              } else {
                ctx.fillStyle = "#facc15";
                ctx.globalAlpha = 0.6;
              }
              ctx.fillRect(x, y, 8, 10);
            }
          }
        }
      }
      const texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.RepeatWrapping;
      texture.repeat.set(1, 3);
      return texture;
    };

    const buildingTexture = createBuildingTexture(activeCity.accentColor);

    // Ground City Floor Grid
    const gridSize = 550;
    const gridDivisions = 55;
    const gridHelper = new THREE.GridHelper(gridSize, gridDivisions, new THREE.Color(activeCity.accentColor), 0x03284d);
    gridHelper.position.y = 0;
    (gridHelper.material as THREE.Material).transparent = true;
    (gridHelper.material as THREE.Material).opacity = 0.65;
    scene.add(gridHelper);

    // Dark Asphalt Reflective Plate
    const groundGeo = new THREE.PlaneGeometry(gridSize * 1.8, gridSize * 1.8);
    const groundMat = new THREE.MeshPhongMaterial({
      color: 0x010815,
      shininess: 90,
      specular: new THREE.Color(activeCity.accentColor),
      transparent: true,
      opacity: 0.95,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    scene.add(ground);

    // Concentric Radar Rings on Ground
    for (let r = 50; r <= 260; r += 50) {
      const ringGeo = new THREE.RingGeometry(r - 0.8, r, 72);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(activeCity.accentColor),
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.2;
      scene.add(ring);
    }

    // 4. Dense Metropolis Generation (17x17 Grid = 289 Skyscraper Slots)
    const gridSizeNum = 17;
    const spacing = 20;
    const originOffset = ((gridSizeNum - 1) * spacing) / 2;
    const buildingMeshes: THREE.Mesh[] = [];

    const baseColor = new THREE.Color(activeCity.accentColor);
    const buildingSolidMat = new THREE.MeshStandardMaterial({
      color: 0x03172e,
      map: buildingTexture,
      roughness: 0.2,
      metalness: 0.85,
      emissive: baseColor,
      emissiveIntensity: 0.3,
      transparent: true,
      opacity: 0.94,
      wireframe: wireframeMode,
    });
    solidMatRef.current = buildingSolidMat;

    const edgeMat = new THREE.LineBasicMaterial({
      color: baseColor,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    });

    const rooftopBeaconMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      blending: THREE.AdditiveBlending,
    });

    const skybridgeMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });

    let bIdx = 0;
    const buildingPositions: { x: number; y: number; z: number; height: number; mesh: THREE.Mesh }[] = [];

    for (let row = 0; row < gridSizeNum; row++) {
      for (let col = 0; col < gridSizeNum; col++) {
        const gridColOffset = col - Math.floor(gridSizeNum / 2);
        const gridRowOffset = row - Math.floor(gridSizeNum / 2);

        // Check if this slot corresponds to a landmark
        const landmark = activeCity.landmarks.find((lm) => lm.relX === gridColOffset && lm.relZ === gridRowOffset);

        // Skip roads to form street blocks
        const isRoadCol = col % 4 === 0;
        const isRoadRow = row % 4 === 0;
        if (!landmark && isRoadCol && isRoadRow) continue;

        const posX = col * spacing - originOffset + (Math.random() - 0.5) * 2;
        const posZ = row * spacing - originOffset + (Math.random() - 0.5) * 2;
        const distFromCenter = Math.hypot(posX, posZ);

        let bHeight: number;
        let bWidth: number;
        let bDepth: number;
        let bName: string;
        let bFloors: number;
        let bStatus: string;
        let archetype: string = "spire";

        if (landmark) {
          bHeight = landmark.heightM * 0.45;
          bWidth = 18;
          bDepth = 18;
          bName = landmark.name;
          bFloors = landmark.floors;
          bStatus = landmark.type;
          archetype = landmark.archetype || "spire";
        } else {
          const heightMultiplier = Math.max(0.18, 1.0 - (distFromCenter / (originOffset * 1.35)));
          const randomBonus = Math.random() * 0.7 + 0.65;
          bHeight = Math.max(22, heightMultiplier * activeCity.tallestMeters * 0.38 * randomBonus);
          bWidth = 10 + Math.random() * 6;
          bDepth = 10 + Math.random() * 6;
          bName = `METROPOLIS NODE #${++bIdx} [${activeCity.country}]`;
          bFloors = Math.max(6, Math.round(bHeight / 3.0));
          bStatus = bHeight > 80 ? "CRITICAL SECTOR HUB" : "SECURE COMM ARRAY";
          archetype = bHeight > 90 ? "stepped" : "spire";
        }

        let bMesh: THREE.Mesh;

        if (archetype === "cylinder") {
          const bGeo = new THREE.CylinderGeometry(bWidth / 2, bWidth / 2, bHeight, 16);
          bMesh = new THREE.Mesh(bGeo, buildingSolidMat);
          bMesh.position.set(posX, bHeight / 2, posZ);

          const edgesGeo = new THREE.EdgesGeometry(bGeo);
          const edgesLine = new THREE.LineSegments(edgesGeo, edgeMat);
          bMesh.add(edgesLine);
        } else {
          const bGeo = new THREE.BoxGeometry(bWidth, bHeight, bDepth);
          bMesh = new THREE.Mesh(bGeo, buildingSolidMat);
          bMesh.position.set(posX, bHeight / 2, posZ);

          const edgesGeo = new THREE.EdgesGeometry(bGeo);
          const edgesLine = new THREE.LineSegments(edgesGeo, edgeMat);
          bMesh.add(edgesLine);

          // If stepped high-rise, add tier top
          if (archetype === "stepped" && bHeight > 55) {
            const tierHeight = bHeight * 0.28;
            const tierGeo = new THREE.BoxGeometry(bWidth * 0.65, tierHeight, bDepth * 0.65);
            const tierMesh = new THREE.Mesh(tierGeo, buildingSolidMat);
            tierMesh.position.set(0, bHeight / 2 + tierHeight / 2, 0);

            const tierEdges = new THREE.LineSegments(new THREE.EdgesGeometry(tierGeo), edgeMat);
            tierMesh.add(tierEdges);
            bMesh.add(tierMesh);
          }
        }

        // Spire & Strobe Beacon on tall buildings
        if (bHeight > 60 || landmark) {
          const spireHeight = landmark ? 28 : 16 + Math.random() * 14;
          const spireGeo = new THREE.ConeGeometry(1.4, spireHeight, 4);
          const spireMesh = new THREE.Mesh(spireGeo, edgeMat as any);
          spireMesh.position.set(0, bHeight / 2 + spireHeight / 2, 0);
          bMesh.add(spireMesh);

          const beaconGeo = new THREE.SphereGeometry(1.5, 8, 8);
          const beaconMesh = new THREE.Mesh(beaconGeo, rooftopBeaconMat);
          beaconMesh.position.set(0, bHeight / 2 + spireHeight, 0);
          bMesh.add(beaconMesh);
        }

        (bMesh as any).userData = {
          id: bIdx,
          name: bName,
          heightM: landmark ? landmark.heightM : Math.round(bHeight * 2.8),
          floors: bFloors,
          status: bStatus,
          energyMw: Math.round(bHeight * 14.2),
          lat: Number((activeCity.lat + gridRowOffset * 0.0025).toFixed(5)),
          lng: Number((activeCity.lng + gridColOffset * 0.0025).toFixed(5)),
        };

        cityGroup.add(bMesh);
        buildingMeshes.push(bMesh);
        buildingPositions.push({ x: posX, y: bHeight, z: posZ, height: bHeight, mesh: bMesh });
      }
    }

    // 5. Skybridges connecting high-rises
    for (let i = 0; i < buildingPositions.length; i++) {
      const b1 = buildingPositions[i];
      if (b1.height < 70) continue;
      for (let j = i + 1; j < buildingPositions.length; j++) {
        const b2 = buildingPositions[j];
        if (b2.height < 70) continue;
        const dist = Math.hypot(b1.x - b2.x, b1.z - b2.z);
        if (dist > 18 && dist < 32) {
          const bridgeHeight = Math.min(b1.height, b2.height) * 0.7;
          const midX = (b1.x + b2.x) / 2;
          const midZ = (b1.z + b2.z) / 2;
          const angle = Math.atan2(b2.z - b1.z, b2.x - b1.x);

          const bridgeGeo = new THREE.BoxGeometry(dist, 3, 3);
          const bridgeMesh = new THREE.Mesh(bridgeGeo, skybridgeMat);
          bridgeMesh.position.set(midX, bridgeHeight, midZ);
          bridgeMesh.rotation.y = -angle;
          cityGroup.add(bridgeMesh);
          break; // connect at most one
        }
      }
    }

    // 6. Streaming Highway Traffic Light Particles (Dual-lane headlights & taillights)
    const trafficCount = 240;
    const trafficGeo = new THREE.BufferGeometry();
    const trafficPositions = new Float32Array(trafficCount * 3);
    const trafficColors = new Float32Array(trafficCount * 3);
    const trafficSpeeds: number[] = [];
    const trafficAxes: ("x" | "z")[] = [];

    const cyanColor = new THREE.Color(0x00f0ff);
    const goldColor = new THREE.Color(0xfacc15);
    const redColor = new THREE.Color(0xf43f5e);

    for (let i = 0; i < trafficCount; i++) {
      const isX = Math.random() > 0.5;
      const isForward = Math.random() > 0.5;
      trafficAxes.push(isX ? "x" : "z");
      trafficSpeeds.push((Math.random() * 0.9 + 0.5) * (isForward ? 1 : -1));

      const col = isForward ? (Math.random() > 0.3 ? cyanColor : goldColor) : redColor;
      trafficColors[i * 3] = col.r;
      trafficColors[i * 3 + 1] = col.g;
      trafficColors[i * 3 + 2] = col.b;

      const roadLaneOffset = (Math.floor(Math.random() * 5) - 2) * spacing * 2;

      if (isX) {
        trafficPositions[i * 3] = (Math.random() - 0.5) * gridSize;
        trafficPositions[i * 3 + 1] = 0.9;
        trafficPositions[i * 3 + 2] = roadLaneOffset + (isForward ? 2 : -2);
      } else {
        trafficPositions[i * 3] = roadLaneOffset + (isForward ? 2 : -2);
        trafficPositions[i * 3 + 1] = 0.9;
        trafficPositions[i * 3 + 2] = (Math.random() - 0.5) * gridSize;
      }
    }

    trafficGeo.setAttribute("position", new THREE.BufferAttribute(trafficPositions, 3));
    trafficGeo.setAttribute("color", new THREE.BufferAttribute(trafficColors, 3));

    const trafficMat = new THREE.PointsMaterial({
      size: 4.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
    });
    const trafficPoints = new THREE.Points(trafficGeo, trafficMat);
    scene.add(trafficPoints);

    // 7. Vertical Laser Scanline Plane
    const scanGeo = new THREE.PlaneGeometry(gridSize * 1.3, gridSize * 1.3);
    const scanMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(activeCity.accentColor),
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    const scanPlane = new THREE.Mesh(scanGeo, scanMat);
    scanPlane.rotation.x = -Math.PI / 2;
    scanPlane.position.y = 10;
    scanPlane.visible = scanlineActiveRef.current;
    scene.add(scanPlane);
    scanPlaneRef.current = scanPlane;

    // 8. Mouse / Touch Controls
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const onPointerDown = (e: PointerEvent) => {
      if (e.button === 0) {
        isDragging = true;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - prevMouseX;
      const dy = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      cityGroup.rotation.y += dx * 0.005;
      camera.position.y = Math.max(25, Math.min(500, camera.position.y - dy * 0.7));
      camera.lookAt(0, 35, 0);
    };

    const onPointerUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY * 0.4;
      camera.position.z = Math.max(50, Math.min(700, camera.position.z + zoomFactor));
      camera.position.x = Math.max(40, Math.min(500, camera.position.x + zoomFactor * 0.7));
      camera.lookAt(0, 35, 0);
    };

    const domEl = renderer.domElement;
    domEl.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    domEl.addEventListener("wheel", onWheel, { passive: false });

    // 9. Raycaster Building Inspector
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onClick = (e: MouseEvent) => {
      const rect = domEl.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(buildingMeshes);

      if (intersects.length > 0) {
        const hit = intersects[0].object as THREE.Mesh;
        const data = (hit as any).userData;
        if (data && data.name) {
          setSelectedBuilding(data);

          if (highlightBoxRef.current) {
            scene.remove(highlightBoxRef.current);
          }
          const boxHelper = new THREE.BoxHelper(hit, new THREE.Color(0xffff00));
          scene.add(boxHelper);
          highlightBoxRef.current = boxHelper;
        }
      }
    };
    domEl.addEventListener("click", onClick);

    // 10. ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect;
        if (w > 0 && h > 0) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      }
    });
    resizeObserver.observe(container);

    // 11. Animation Loop
    let scanDirection = 1;
    let reqId: number;

    const animate = () => {
      reqId = requestAnimationFrame(animate);

      if (autoRotateRef.current && !isDragging) {
        cityGroup.rotation.y += 0.0012;
      }

      if (scanPlaneRef.current && scanlineActiveRef.current) {
        scanPlaneRef.current.position.y += 0.85 * scanDirection;
        if (scanPlaneRef.current.position.y > 175) {
          scanDirection = -1;
        } else if (scanPlaneRef.current.position.y < 4) {
          scanDirection = 1;
        }
      }

      // Traffic flow
      const posArr = trafficGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < trafficCount; i++) {
        if (trafficAxes[i] === "x") {
          posArr[i * 3] += trafficSpeeds[i];
          if (posArr[i * 3] > gridSize / 2) posArr[i * 3] = -gridSize / 2;
          if (posArr[i * 3] < -gridSize / 2) posArr[i * 3] = gridSize / 2;
        } else {
          posArr[i * 3 + 2] += trafficSpeeds[i];
          if (posArr[i * 3 + 2] > gridSize / 2) posArr[i * 3 + 2] = -gridSize / 2;
          if (posArr[i * 3 + 2] < -gridSize / 2) posArr[i * 3 + 2] = gridSize / 2;
        }
      }
      trafficGeo.attributes.position.needsUpdate = true;

      if (highlightBoxRef.current) {
        highlightBoxRef.current.update();
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(reqId);
      resizeObserver.disconnect();
      domEl.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      domEl.removeEventListener("wheel", onWheel);
      domEl.removeEventListener("click", onClick);
      if (highlightBoxRef.current) {
        scene.remove(highlightBoxRef.current);
      }
      renderer.dispose();
    };
  }, [activeCity]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden", background: "#010714" }}>
      {/* 3D WebGL Canvas */}
      <div ref={containerRef} style={{ width: "100%", height: "100%", cursor: "grab" }} />

      {/* Cyber Scanline Texture */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "linear-gradient(rgba(0, 240, 255, 0.02) 50%, rgba(0, 0, 0, 0.25) 50%)",
          backgroundSize: "100% 4px",
          pointerEvents: "none",
        }}
      />

      {/* Top Left: Real Geospatial Telemetry & Search Box */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          background: "rgba(1, 8, 20, 0.94)",
          border: `1.5px solid ${activeCity.accentColor}80`,
          borderRadius: "8px",
          padding: "12px 16px",
          color: activeCity.accentColor,
          fontFamily: "'Orbitron', monospace",
          fontSize: "11px",
          backdropFilter: "blur(10px)",
          boxShadow: `0 0 25px ${activeCity.accentColor}30`,
          zIndex: 10,
          minWidth: "280px",
          maxWidth: "340px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${activeCity.accentColor}35`, paddingBottom: "8px", marginBottom: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ width: "9px", height: "9px", borderRadius: "50%", background: activeCity.accentColor, boxShadow: `0 0 10px ${activeCity.accentColor}` }} />
            <span style={{ fontWeight: 800, letterSpacing: "1px", color: "#ffffff" }}>REAL 3D URBAN MATRIX</span>
          </div>
          <span style={{ fontSize: "9px", background: "rgba(0, 240, 255, 0.15)", padding: "2px 6px", borderRadius: "3px", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
            {activeCity.country}
          </span>
        </div>

        {/* Live Search */}
        <form onSubmit={handleSearchCity} style={{ display: "flex", gap: "4px", marginBottom: "8px" }}>
          <input
            type="text"
            placeholder="Search city/landmark (e.g. Paris, Sydney, Guindy)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              background: "rgba(0, 0, 0, 0.6)",
              border: `1px solid ${activeCity.accentColor}60`,
              color: "#ffffff",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "10px",
              fontFamily: "'Share Tech Mono', monospace",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={isSearching}
            style={{
              background: `linear-gradient(135deg, ${activeCity.accentColor}40, rgba(0,119,255,0.4))`,
              border: `1px solid ${activeCity.accentColor}`,
              color: "#ffffff",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            {isSearching ? "..." : "LOAD"}
          </button>
        </form>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "10.5px", color: "#94a3b8" }}>
          <div style={{ gridColumn: "span 2" }}>
            LOCATION: <span style={{ color: "#ffffff", fontWeight: "bold" }}>{customLocationName || activeCity.name}</span>
          </div>
          <div>GPS LAT: <span style={{ color: "#38bdf8" }}>{activeCity.lat}° N</span></div>
          <div>GPS LNG: <span style={{ color: "#38bdf8" }}>{activeCity.lng}° E</span></div>
          <div>DENSITY: <span style={{ color: "#34d399" }}>{activeCity.density} BLDGS/KM²</span></div>
          <div>PEAK HEIGHT: <span style={{ color: "#facc15" }}>{activeCity.tallestMeters}M</span></div>
        </div>
      </div>

      {/* Top Center: Camera View Angles Toolbar */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "50%",
          transform: "translateX(-50%)",
          background: "rgba(1, 8, 20, 0.94)",
          border: "1.5px solid rgba(0, 240, 255, 0.4)",
          borderRadius: "8px",
          padding: "5px 10px",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          backdropFilter: "blur(10px)",
          boxShadow: "0 0 20px rgba(0, 240, 255, 0.2)",
          zIndex: 10,
        }}
      >
        <span style={{ color: "#94a3b8", fontSize: "10px", fontFamily: "'Orbitron', monospace", marginRight: "4px" }}>CAMERA:</span>
        <button
          onClick={() => applyCameraPreset("isometric")}
          style={{
            background: cameraMode === "isometric" ? "rgba(0, 240, 255, 0.3)" : "transparent",
            border: cameraMode === "isometric" ? "1px solid #00f0ff" : "1px solid rgba(255,255,255,0.1)",
            color: cameraMode === "isometric" ? "#00f0ff" : "#94a3b8",
            fontSize: "10px",
            padding: "4px 8px",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          🎮 ISOMETRIC
        </button>
        <button
          onClick={() => applyCameraPreset("street")}
          style={{
            background: cameraMode === "street" ? "rgba(0, 240, 255, 0.3)" : "transparent",
            border: cameraMode === "street" ? "1px solid #00f0ff" : "1px solid rgba(255,255,255,0.1)",
            color: cameraMode === "street" ? "#00f0ff" : "#94a3b8",
            fontSize: "10px",
            padding: "4px 8px",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          🏙️ STREET CANYON
        </button>
        <button
          onClick={() => applyCameraPreset("topdown")}
          style={{
            background: cameraMode === "topdown" ? "rgba(0, 240, 255, 0.3)" : "transparent",
            border: cameraMode === "topdown" ? "1px solid #00f0ff" : "1px solid rgba(255,255,255,0.1)",
            color: cameraMode === "topdown" ? "#00f0ff" : "#94a3b8",
            fontSize: "10px",
            padding: "4px 8px",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          🛰️ TOP-DOWN
        </button>
      </div>

      {/* Top Right: Real City Presets & Controls */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          right: "16px",
          background: "rgba(1, 8, 20, 0.94)",
          border: "1.5px solid rgba(0, 240, 255, 0.4)",
          borderRadius: "8px",
          padding: "10px 14px",
          maxWidth: "310px",
          backdropFilter: "blur(10px)",
          boxShadow: "0 0 25px rgba(0, 240, 255, 0.2)",
          zIndex: 10,
        }}
      >
        <div style={{ color: "#00f0ff", fontFamily: "'Orbitron', monospace", fontSize: "11px", fontWeight: "bold", marginBottom: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>REAL CITY BLUEPRINTS</span>
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => setAutoRotate((r) => !r)}
              title="Toggle Auto Rotation (Position Preserved on Stop)"
              style={{
                background: autoRotate ? "rgba(0, 240, 255, 0.25)" : "rgba(255, 255, 255, 0.05)",
                border: `1px solid ${autoRotate ? "#00f0ff" : "rgba(255, 255, 255, 0.2)"}`,
                color: autoRotate ? "#00f0ff" : "#94a3b8",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "3px",
                cursor: "pointer",
              }}
            >
              {autoRotate ? "AUTO 🔄" : "MANUAL ✋"}
            </button>
            <button
              onClick={() => setWireframeMode((w) => !w)}
              title="Toggle Holographic Wireframe"
              style={{
                background: wireframeMode ? "rgba(0, 240, 255, 0.25)" : "rgba(255, 255, 255, 0.05)",
                border: `1px solid ${wireframeMode ? "#00f0ff" : "rgba(255, 255, 255, 0.2)"}`,
                color: wireframeMode ? "#00f0ff" : "#94a3b8",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "3px",
                cursor: "pointer",
              }}
            >
              {wireframeMode ? "WIRE" : "SOLID"}
            </button>
            <button
              onClick={() => setScanlineActive((p) => !p)}
              style={{
                background: scanlineActive ? "rgba(0, 240, 255, 0.2)" : "rgba(248, 113, 113, 0.2)",
                border: `1px solid ${scanlineActive ? "#00f0ff" : "#f87171"}`,
                color: scanlineActive ? "#00f0ff" : "#f87171",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "3px",
                cursor: "pointer",
              }}
            >
              {scanlineActive ? "LASER ON" : "LASER OFF"}
            </button>
          </div>
        </div>

        {/* Real City Blueprints List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "170px", overflowY: "auto" }}>
          {REAL_CITY_BLUEPRINTS.map((city) => {
            const isSelected = activeCity.id === city.id;
            return (
              <button
                key={city.id}
                onClick={() => {
                  setActiveCity(city);
                  setCustomLocationName(null);
                  setSelectedBuilding(null);
                }}
                style={{
                  background: isSelected ? "rgba(0, 240, 255, 0.25)" : "rgba(1, 8, 20, 0.6)",
                  border: isSelected ? `1.5px solid ${city.accentColor}` : "1px solid rgba(0, 240, 255, 0.15)",
                  color: isSelected ? "#ffffff" : "#94a3b8",
                  padding: "6px 9px",
                  borderRadius: "4px",
                  fontSize: "10.5px",
                  fontFamily: "'Inter', sans-serif",
                  textAlign: "left",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: city.accentColor }} />
                  <span style={{ fontWeight: isSelected ? "bold" : "normal" }}>{city.name}</span>
                </div>
                <span style={{ fontSize: "8.5px", color: city.accentColor, fontFamily: "monospace" }}>[{city.country}]</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Center: Real Selected Landmark / Skyscraper Telemetry HUD Card */}
      {selectedBuilding && (
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(1, 8, 20, 0.96)",
            border: `1.5px solid ${activeCity.accentColor}`,
            borderRadius: "8px",
            padding: "12px 24px",
            display: "flex",
            alignItems: "center",
            gap: "18px",
            backdropFilter: "blur(12px)",
            boxShadow: `0 0 30px ${activeCity.accentColor}50`,
            zIndex: 10,
          }}
        >
          <div style={{ width: "14px", height: "14px", borderRadius: "50%", background: activeCity.accentColor, boxShadow: `0 0 14px ${activeCity.accentColor}` }} />
          <div>
            <div style={{ color: "#ffffff", fontFamily: "'Orbitron', monospace", fontSize: "13px", fontWeight: "bold" }}>
              {selectedBuilding.name} // <span style={{ color: "#34d399" }}>{selectedBuilding.status}</span>
            </div>
            <div style={{ color: "#94a3b8", fontSize: "11px", fontFamily: "monospace", marginTop: "4px", display: "flex", gap: "12px" }}>
              <div>ELEVATION: <span style={{ color: "#38bdf8", fontWeight: "bold" }}>{selectedBuilding.heightM}M</span></div>
              <div>LEVELS: <span style={{ color: "#facc15", fontWeight: "bold" }}>{selectedBuilding.floors} FLOORS</span></div>
              <div>COORDINATES: <span style={{ color: "#34d399", fontWeight: "bold" }}>{selectedBuilding.lat}° N, {selectedBuilding.lng}° E</span></div>
              <div>REGION: <span style={{ color: activeCity.accentColor, fontWeight: "bold" }}>{activeCity.name}</span></div>
            </div>
          </div>
          <button
            onClick={() => setSelectedBuilding(null)}
            style={{
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.2)",
              color: "#94a3b8",
              cursor: "pointer",
              borderRadius: "4px",
              padding: "3px 8px",
              fontSize: "11px",
            }}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
};
