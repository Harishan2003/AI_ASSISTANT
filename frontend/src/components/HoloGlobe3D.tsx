/**
 * Friday AI Assistant - 3D Holographic Globe Component
 * ====================================================
 * High-performance Three.js WebGL Holographic Earth Globe with dynamic continent wireframes,
 * orbital satellite telemetry, inter-continental laser trajectory arcs, tactical radar rings,
 * live zoom telemetry (1x to 9x), and seamless animated transition to 2D Tactical Map.
 */

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

export interface HoloGlobe3DProps {
  onSectorSelect?: (sectorName: string, lat: number, lng: number) => void;
  onDiveIn?: (lat: number, lng: number, locationName?: string) => void;
  onZoomChange?: (zoomLevel: number) => void;
  selectedRegion?: string;
  initialLat?: number;
  initialLng?: number;
  isHybridMode?: boolean;
  isActive?: boolean;
}

interface StrategicNode {
  name: string;
  lat: number;
  lng: number;
  type: "HQ" | "HUB" | "NODE" | "RELAY";
  color: string;
}

const STRATEGIC_NODES: StrategicNode[] = [
  { name: "FRIDAY PRIME HQ // INDIA", lat: 20.5937, lng: 78.9629, type: "HQ", color: "#00f0ff" },
  { name: "CHENNAI QUANTUM NODE", lat: 13.0827, lng: 80.2707, type: "NODE", color: "#34d399" },
  { name: "NEW DELHI DEFENSE CORE", lat: 28.6139, lng: 77.209, type: "HUB", color: "#38bdf8" },
  { name: "TOKYO NEO-SECTOR", lat: 35.6762, lng: 139.6503, type: "HUB", color: "#facc15" },
  { name: "LONDON TACTICAL GRID", lat: 51.5074, lng: -0.1278, type: "HUB", color: "#00f0ff" },
  { name: "NEW YORK CYBER COMMAND", lat: 40.7128, lng: -74.006, type: "HUB", color: "#f87171" },
  { name: "SAN FRANCISCO AI CLUSTER", lat: 37.7749, lng: -122.4194, type: "NODE", color: "#a855f7" },
  { name: "DUBAI CYBER SPIRE", lat: 25.2048, lng: 55.2708, type: "RELAY", color: "#facc15" },
  { name: "SINGAPORE MARINA NODE", lat: 1.3521, lng: 103.8198, type: "RELAY", color: "#34d399" },
  { name: "SYDNEY PACIFIC RELAY", lat: -33.8688, lng: 151.2093, type: "RELAY", color: "#38bdf8" },
  { name: "BERLIN NEURAL ARRAY", lat: 52.52, lng: 13.405, type: "NODE", color: "#00f0ff" },
];

const TRAJECTORY_PAIRS: [number, number][] = [
  [0, 3], // India -> Tokyo
  [0, 4], // India -> London
  [0, 7], // India -> Dubai
  [0, 8], // India -> Singapore
  [4, 5], // London -> New York
  [5, 6], // New York -> San Francisco
  [6, 3], // San Francisco -> Tokyo
  [7, 10], // Dubai -> Berlin
  [8, 9], // Singapore -> Sydney
];

const GLOBE_RADIUS = 75;
const MIN_CAMERA_Z = 105; // 9.0x Max Globe Zoom
const MAX_CAMERA_Z = 380; // 1.0x Deep Orbit

export const HoloGlobe3D: React.FC<HoloGlobe3DProps> = ({
  onSectorSelect,
  onDiveIn,
  onZoomChange,
  selectedRegion,
  initialLat,
  initialLng,
  isHybridMode = true,
  isActive = true,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [selectedNode, setSelectedNode] = useState<StrategicNode | null>(STRATEGIC_NODES[0]);
  const [isRotating, setIsRotating] = useState<boolean>(true);
  const [rotationSpeed] = useState<number>(0.0018);
  const [currentZoom, setCurrentZoom] = useState<number>(5.0);
  const [hoveredCoords, setHoveredCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [isDiving, setIsDiving] = useState<boolean>(false);
  const activeSatellites = 14;

  const isRotatingRef = useRef<boolean>(true);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const globeGroupRef = useRef<THREE.Group | null>(null);
  const isDivingRef = useRef<boolean>(false);
  const isActiveRef = useRef<boolean>(isActive);

  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  useEffect(() => {
    isRotatingRef.current = isRotating;
  }, [isRotating]);

  // Coordinate conversion helper (lat/lng to 3D Sphere Vector)
  const latLngToVector3 = (lat: number, lng: number, radius: number = GLOBE_RADIUS): THREE.Vector3 => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
  };

  // Convert 3D Point on Sphere back to Latitude & Longitude
  const vector3ToLatLng = (localPoint: THREE.Vector3): { lat: number; lng: number } => {
    const phi = Math.acos(Math.max(-1, Math.min(1, localPoint.y / GLOBE_RADIUS)));
    const lat = 90 - (phi * 180) / Math.PI;
    const theta = Math.atan2(localPoint.z, -localPoint.x);
    let lng = (theta * 180) / Math.PI - 180;
    while (lng < -180) lng += 360;
    while (lng > 180) lng -= 360;
    return { lat: Number(lat.toFixed(4)), lng: Number(lng.toFixed(4)) };
  };

  // Get current center GPS coordinate under crosshair
  const getCurrentCenterCoords = (): { lat: number; lng: number } => {
    if (!globeGroupRef.current) return { lat: 20.5937, lng: 78.9629 };
    const localFacingVector = new THREE.Vector3(0, 0, GLOBE_RADIUS);
    globeGroupRef.current.worldToLocal(localFacingVector);
    return vector3ToLatLng(localFacingVector);
  };

  // Trigger smooth transition into 2D Tactical Map
  const trigger2DDive = (lat?: number, lng?: number, label?: string) => {
    if (isDivingRef.current) return;
    isDivingRef.current = true;
    setIsDiving(true);

    const targetCoords =
      lat !== undefined && lng !== undefined
        ? { lat, lng }
        : hoveredCoords || getCurrentCenterCoords();
    const targetName = label || selectedNode?.name || `Target Sector (${targetCoords.lat}°, ${targetCoords.lng}°)`;

    // Smooth camera surge animation
    let frames = 0;
    const diveAnim = () => {
      if (cameraRef.current && frames < 12) {
        cameraRef.current.position.z = Math.max(78, cameraRef.current.position.z - 4.5);
        frames++;
        requestAnimationFrame(diveAnim);
      } else {
        if (onDiveIn) {
          onDiveIn(targetCoords.lat, targetCoords.lng, targetName);
        } else if (onSectorSelect) {
          onSectorSelect(targetName, targetCoords.lat, targetCoords.lng);
        }
      }
    };
    diveAnim();
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 550;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x01040a, 0.0012);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
    // Initial camera distance mapped to zoom ~5x
    camera.position.set(0, 0, 240);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 2. Globe Group
    const globeGroup = new THREE.Group();
    scene.add(globeGroup);
    globeGroupRef.current = globeGroup;

    // Inner Glowing Core Sphere
    const innerSphereGeo = new THREE.SphereGeometry(GLOBE_RADIUS * 0.98, 48, 48);
    const innerSphereMat = new THREE.MeshBasicMaterial({
      color: 0x021324,
      transparent: true,
      opacity: 0.85,
    });
    const innerSphere = new THREE.Mesh(innerSphereGeo, innerSphereMat);
    globeGroup.add(innerSphere);

    // Glowing Holographic Wireframe Sphere
    const wireframeGeo = new THREE.WireframeGeometry(new THREE.SphereGeometry(GLOBE_RADIUS, 32, 32));
    const wireframeMat = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.14,
    });
    const wireframeMesh = new THREE.LineSegments(wireframeGeo, wireframeMat);
    globeGroup.add(wireframeMesh);

    // Latitude & Longitude Tactical Ring Grids
    const gridGroup = new THREE.Group();
    for (let lat = -60; lat <= 60; lat += 30) {
      const ringRadius = GLOBE_RADIUS * Math.cos((lat * Math.PI) / 180);
      const ringY = GLOBE_RADIUS * Math.sin((lat * Math.PI) / 180);
      const ringGeo = new THREE.BufferGeometry();
      const points: THREE.Vector3[] = [];
      for (let i = 0; i <= 64; i++) {
        const angle = (i / 64) * Math.PI * 2;
        points.push(new THREE.Vector3(Math.cos(angle) * ringRadius, ringY, Math.sin(angle) * ringRadius));
      }
      ringGeo.setFromPoints(points);
      const ringMat = new THREE.LineBasicMaterial({
        color: lat === 0 ? 0x00f0ff : 0x0077ff,
        transparent: true,
        opacity: lat === 0 ? 0.45 : 0.2,
      });
      gridGroup.add(new THREE.Line(ringGeo, ringMat));
    }
    globeGroup.add(gridGroup);

    // Outer Atmospheric Particle Cloud
    const particleCount = 750;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = GLOBE_RADIUS * (1.03 + Math.random() * 0.12);
      particlePos[i] = r * Math.sin(phi) * Math.cos(theta);
      particlePos[i + 1] = r * Math.sin(phi) * Math.sin(theta);
      particlePos[i + 2] = r * Math.cos(phi);
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 1.6,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    globeGroup.add(particles);

    // 3. Load Country & Continent Outlines from GeoJSON
    fetch("/world-continents.json")
      .then((res) => res.json())
      .then((geoData) => {
        if (!geoData || !geoData.features) return;

        const lineMaterial = new THREE.LineBasicMaterial({
          color: 0x00f0ff,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending,
        });

        const continentLinesGroup = new THREE.Group();

        geoData.features.forEach((feature: any) => {
          const geom = feature.geometry;
          if (!geom) return;

          const coordinates = geom.type === "Polygon" ? [geom.coordinates] : geom.type === "MultiPolygon" ? geom.coordinates : [];

          coordinates.forEach((poly: any) => {
            poly.forEach((ring: any) => {
              const points: THREE.Vector3[] = [];
              for (let i = 0; i < ring.length; i++) {
                const lng = ring[i][0];
                const lat = ring[i][1];
                if (typeof lat === "number" && typeof lng === "number") {
                  points.push(latLngToVector3(lat, lng, GLOBE_RADIUS * 1.002));
                }
              }
              if (points.length > 1) {
                const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
                const lineMesh = new THREE.Line(lineGeo, lineMaterial);
                continentLinesGroup.add(lineMesh);
              }
            });
          });
        });

        globeGroup.add(continentLinesGroup);
      })
      .catch(() => {});

    // 4. Strategic Tactical Node Markers & Glowing Beacons
    const nodesGroup = new THREE.Group();
    const nodeMeshes: { mesh: THREE.Mesh; node: StrategicNode }[] = [];

    STRATEGIC_NODES.forEach((node) => {
      const pos = latLngToVector3(node.lat, node.lng, GLOBE_RADIUS * 1.015);

      // Pin Core Dot
      const dotGeo = new THREE.SphereGeometry(1.6, 16, 16);
      const dotMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(node.color) });
      const dotMesh = new THREE.Mesh(dotGeo, dotMat);
      dotMesh.position.copy(pos);
      (dotMesh as any).userData = { node };
      nodesGroup.add(dotMesh);
      nodeMeshes.push({ mesh: dotMesh, node });

      // Pin Vertical Laser Spire
      const normal = pos.clone().normalize();
      const spireEnd = pos.clone().add(normal.clone().multiplyScalar(9));
      const spireGeo = new THREE.BufferGeometry().setFromPoints([pos, spireEnd]);
      const spireMat = new THREE.LineBasicMaterial({ color: new THREE.Color(node.color), transparent: true, opacity: 0.9 });
      const spireMesh = new THREE.Line(spireGeo, spireMat);
      nodesGroup.add(spireMesh);

      // Spire Cap Pulse
      const capGeo = new THREE.SphereGeometry(1.0, 12, 12);
      const capMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const capMesh = new THREE.Mesh(capGeo, capMat);
      capMesh.position.copy(spireEnd);
      nodesGroup.add(capMesh);
    });
    globeGroup.add(nodesGroup);

    // 5. Inter-Continental Bézier Laser Trajectory Arcs
    const arcsGroup = new THREE.Group();
    const photons: { mesh: THREE.Mesh; curve: THREE.QuadraticBezierCurve3; t: number; speed: number }[] = [];

    TRAJECTORY_PAIRS.forEach(([fromIdx, toIdx]) => {
      const startNode = STRATEGIC_NODES[fromIdx];
      const endNode = STRATEGIC_NODES[toIdx];
      if (!startNode || !endNode) return;

      const p1 = latLngToVector3(startNode.lat, startNode.lng, GLOBE_RADIUS * 1.01);
      const p2 = latLngToVector3(endNode.lat, endNode.lng, GLOBE_RADIUS * 1.01);

      const mid = p1.clone().add(p2).multiplyScalar(0.5);
      const dist = p1.distanceTo(p2);
      const altitude = GLOBE_RADIUS * (1.18 + dist * 0.0016);
      mid.normalize().multiplyScalar(altitude);

      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const curvePoints = curve.getPoints(50);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const arcMat = new THREE.LineBasicMaterial({
        color: 0x00f0ff,
        transparent: true,
        opacity: 0.45,
        blending: THREE.AdditiveBlending,
      });
      arcsGroup.add(new THREE.Line(arcGeo, arcMat));

      const photonGeo = new THREE.SphereGeometry(1.4, 8, 8);
      const photonMat = new THREE.MeshBasicMaterial({ color: 0xffffff, blending: THREE.AdditiveBlending });
      const photonMesh = new THREE.Mesh(photonGeo, photonMat);
      arcsGroup.add(photonMesh);

      photons.push({
        mesh: photonMesh,
        curve,
        t: Math.random(),
        speed: 0.004 + Math.random() * 0.003,
      });
    });
    globeGroup.add(arcsGroup);

    // 6. Orbital Satellite Rings
    const orbitalGroup = new THREE.Group();
    const orbitAngles = [0, 45, -35];
    const satellites: THREE.Mesh[] = [];

    orbitAngles.forEach((tilt, idx) => {
      const orbitR = GLOBE_RADIUS * (1.28 + idx * 0.1);
      const ringGeo = new THREE.BufferGeometry();
      const pts: THREE.Vector3[] = [];
      for (let i = 0; i <= 80; i++) {
        const a = (i / 80) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(a) * orbitR, 0, Math.sin(a) * orbitR));
      }
      ringGeo.setFromPoints(pts);
      const ringMat = new THREE.LineBasicMaterial({
        color: idx === 0 ? 0x00f0ff : idx === 1 ? 0xfacc15 : 0x34d399,
        transparent: true,
        opacity: 0.35,
      });
      const ringMesh = new THREE.Line(ringGeo, ringMat);
      ringMesh.rotation.x = THREE.MathUtils.degToRad(tilt);
      ringMesh.rotation.z = THREE.MathUtils.degToRad(idx * 60);
      orbitalGroup.add(ringMesh);

      const satGeo = new THREE.BoxGeometry(2.0, 1.2, 1.2);
      const satMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const satMesh = new THREE.Mesh(satGeo, satMat);
      (satMesh as any).userData = { radius: orbitR, angle: idx * 2.0, tilt, speed: 0.006 + idx * 0.002 };
      orbitalGroup.add(satMesh);
      satellites.push(satMesh);
    });
    globeGroup.add(orbitalGroup);

    // 7. Raycaster for Mouse Hover, Click & Dive
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    // 8. Mouse Drag & Orbit Interaction
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

    const updateZoomTelemetry = (cameraZ: number) => {
      // Map camera Z (380 to 105) to 1.0x - 9.0x zoom
      const normalized = Math.max(0, Math.min(1, (MAX_CAMERA_Z - cameraZ) / (MAX_CAMERA_Z - MIN_CAMERA_Z)));
      const zoom = Number((1.0 + normalized * 8.0).toFixed(1));
      setCurrentZoom(zoom);
      if (onZoomChange) {
        onZoomChange(zoom);
      }
      return zoom;
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Update hovered latitude / longitude
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObject(innerSphere);
      if (intersects.length > 0) {
        const localHit = intersects[0].point.clone();
        globeGroup.worldToLocal(localHit);
        const coords = vector3ToLatLng(localHit);
        setHoveredCoords(coords);
      }

      if (!isDragging) return;
      const dx = e.clientX - prevMouseX;
      const dy = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      globeGroup.rotation.y += dx * 0.005;
      globeGroup.rotation.x += dy * 0.005;
      globeGroup.rotation.x = Math.max(-Math.PI / 2.2, Math.min(Math.PI / 2.2, globeGroup.rotation.x));
    };

    const onPointerUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (isDivingRef.current) return;

      const delta = e.deltaY * 0.35;
      const newZ = camera.position.z + delta;

      if (newZ < MIN_CAMERA_Z) {
        // Zoom threshold reached (Exceeded 9.0x) -> Animate & Transition to 2D Map!
        camera.position.z = MIN_CAMERA_Z;
        updateZoomTelemetry(MIN_CAMERA_Z);
        if (isHybridMode) {
          trigger2DDive();
        }
      } else if (newZ > MAX_CAMERA_Z) {
        camera.position.z = MAX_CAMERA_Z;
        updateZoomTelemetry(MAX_CAMERA_Z);
      } else {
        camera.position.z = newZ;
        updateZoomTelemetry(newZ);
      }
    };

    // Double-click to dive into target sector
    const onDblClick = (e: MouseEvent) => {
      if (isDivingRef.current) return;
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObject(innerSphere);
      if (intersects.length > 0) {
        const localHit = intersects[0].point.clone();
        globeGroup.worldToLocal(localHit);
        const coords = vector3ToLatLng(localHit);
        trigger2DDive(coords.lat, coords.lng, `Target Location (${coords.lat}°, ${coords.lng}°)`);
      }
    };

    const domEl = renderer.domElement;
    domEl.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    domEl.addEventListener("wheel", onWheel, { passive: false });
    domEl.addEventListener("dblclick", onDblClick);

    // Focus region initial rotation
    if (initialLat !== undefined && initialLng !== undefined) {
      globeGroup.rotation.y = THREE.MathUtils.degToRad(-initialLng - 90);
      globeGroup.rotation.x = THREE.MathUtils.degToRad(initialLat);
    } else if (selectedRegion === "north_america" || selectedRegion === "usa") {
      globeGroup.rotation.y = THREE.MathUtils.degToRad(100);
      globeGroup.rotation.x = THREE.MathUtils.degToRad(25);
    } else if (selectedRegion === "europe") {
      globeGroup.rotation.y = THREE.MathUtils.degToRad(-10);
      globeGroup.rotation.x = THREE.MathUtils.degToRad(35);
    } else if (selectedRegion === "east_asia" || selectedRegion === "japan") {
      globeGroup.rotation.y = THREE.MathUtils.degToRad(-140);
      globeGroup.rotation.x = THREE.MathUtils.degToRad(25);
    } else {
      // Default: India
      globeGroup.rotation.y = THREE.MathUtils.degToRad(-80);
      globeGroup.rotation.x = THREE.MathUtils.degToRad(15);
    }

    updateZoomTelemetry(camera.position.z);

    // 9. Animation Loop
    let reqId: number;
    const animate = () => {
      reqId = requestAnimationFrame(animate);

      // If component is inactive (user in 2D map), bypass render loop to save 100% CPU/GPU
      if (!isActiveRef.current) return;

      // Auto-rotation if enabled
      if (isRotatingRef.current && !isDragging && !isDivingRef.current) {
        globeGroup.rotation.y += rotationSpeed;
      }

      // Update trajectory photons
      photons.forEach((p) => {
        p.t = (p.t + p.speed) % 1.0;
        const pos = p.curve.getPointAt(p.t);
        p.mesh.position.copy(pos);
      });

      // Update satellites
      satellites.forEach((sat) => {
        const u = (sat as any).userData;
        u.angle += u.speed;
        const x = Math.cos(u.angle) * u.radius;
        const z = Math.sin(u.angle) * u.radius;
        sat.position.set(x, 0, z);
        sat.rotation.y = u.angle;
      });

      // Atmospheric particle pulse
      particles.rotation.y -= 0.0005;

      renderer.render(scene, camera);
    };

    animate();

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

    return () => {
      cancelAnimationFrame(reqId);
      resizeObserver.disconnect();
      domEl.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      domEl.removeEventListener("wheel", onWheel);
      domEl.removeEventListener("dblclick", onDblClick);
      renderer.dispose();
    };
  }, [selectedRegion, initialLat, initialLng]);

  // Step zoom in / out with buttons
  const handleZoomStep = (delta: number) => {
    if (!cameraRef.current || isDivingRef.current) return;
    const currentZ = cameraRef.current.position.z;
    const targetZ = currentZ + delta;

    if (targetZ <= MIN_CAMERA_Z) {
      cameraRef.current.position.z = MIN_CAMERA_Z;
      setCurrentZoom(9.0);
      if (isHybridMode) {
        trigger2DDive();
      }
    } else if (targetZ >= MAX_CAMERA_Z) {
      cameraRef.current.position.z = MAX_CAMERA_Z;
      setCurrentZoom(1.0);
    } else {
      cameraRef.current.position.z = targetZ;
      const normalized = Math.max(0, Math.min(1, (MAX_CAMERA_Z - targetZ) / (MAX_CAMERA_Z - MIN_CAMERA_Z)));
      setCurrentZoom(Number((1.0 + normalized * 8.0).toFixed(1)));
    }
  };

  const selectNode = (node: StrategicNode) => {
    setSelectedNode(node);
    if (globeGroupRef.current) {
      // Smoothly rotate globe to face node
      globeGroupRef.current.rotation.y = THREE.MathUtils.degToRad(-node.lng - 90);
      globeGroupRef.current.rotation.x = THREE.MathUtils.degToRad(node.lat);
    }
    if (onSectorSelect) {
      onSectorSelect(node.name, node.lat, node.lng);
    }
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        background: "radial-gradient(circle at 50% 50%, rgba(1, 15, 30, 0.95) 0%, rgba(1, 4, 10, 0.98) 100%)",
      }}
    >
      {/* Three.js Canvas Container */}
      <div ref={containerRef} style={{ width: "100%", height: "100%", cursor: isDiving ? "wait" : "grab" }} />

      {/* Futuristic Holographic Grid Lines Overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.04) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }}
      />

      {/* Central Crosshair & Reticle */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          pointerEvents: "none",
          zIndex: 5,
        }}
      >
        <div style={{ width: "40px", height: "40px", border: "1px dashed rgba(0, 240, 255, 0.35)", borderRadius: "50%" }} />
        <div style={{ position: "absolute", top: "20px", left: "-10px", width: "60px", height: "1px", background: "rgba(0, 240, 255, 0.25)" }} />
        <div style={{ position: "absolute", top: "-10px", left: "20px", width: "1px", height: "60px", background: "rgba(0, 240, 255, 0.25)" }} />
      </div>

      {/* Top Left: Planetary Telemetry Card */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          background: "rgba(1, 4, 10, 0.92)",
          border: "1px solid rgba(0, 240, 255, 0.35)",
          borderRadius: "6px",
          padding: "10px 14px",
          color: "#00f0ff",
          fontFamily: "'Orbitron', monospace",
          fontSize: "11px",
          backdropFilter: "blur(8px)",
          boxShadow: "0 0 20px rgba(0, 240, 255, 0.15)",
          pointerEvents: "none",
          minWidth: "240px",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", borderBottom: "1px solid rgba(0, 240, 255, 0.2)", paddingBottom: "6px", marginBottom: "6px" }}>
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00f0ff", boxShadow: "0 0 8px #00f0ff", animation: "pulse 1.5s infinite" }} />
          <span style={{ fontWeight: 700, letterSpacing: "1px" }}>HOLOGRAPHIC ORBITAL RADAR</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", fontSize: "10px", color: "#94a3b8" }}>
          <div>ORBIT ALT: <span style={{ color: "#38bdf8" }}>35,786 KM</span></div>
          <div>SATS ACTIVE: <span style={{ color: "#34d399" }}>{activeSatellites} NODES</span></div>
          <div>ROTATION: <span style={{ color: "#facc15" }}>{isRotating ? "SYNC LOCK" : "MANUAL HOLD"}</span></div>
          <div>PROJECTION: <span style={{ color: "#00f0ff" }}>WGS-84 3D</span></div>
          {hoveredCoords && (
            <div style={{ gridColumn: "span 2", color: "#38bdf8", borderTop: "1px dashed rgba(0, 240, 255, 0.2)", paddingTop: "4px", marginTop: "2px" }}>
              TARGET REF: {hoveredCoords.lat.toFixed(2)}° N, {hoveredCoords.lng.toFixed(2)}° E
            </div>
          )}
        </div>
      </div>

      {/* Top Center: Live Zoom Telemetry Gauge & Hybrid Threshold Indicator */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "50%",
          transform: "translateX(-50%)",
          background: "rgba(1, 6, 18, 0.95)",
          border: "1.5px solid rgba(0, 240, 255, 0.5)",
          borderRadius: "8px",
          padding: "8px 16px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          backdropFilter: "blur(10px)",
          boxShadow: "0 0 25px rgba(0, 240, 255, 0.25)",
          zIndex: 10,
          fontFamily: "'Orbitron', monospace",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "11px", color: "#8ab4f8", letterSpacing: "0.5px" }}>GLOBE ZOOM:</span>
          <span style={{ fontSize: "13px", fontWeight: "bold", color: currentZoom >= 8.5 ? "#facc15" : "#00f0ff" }}>
            {currentZoom.toFixed(1)}x / 9.0x
          </span>
        </div>

        {/* Dynamic Zoom Level Progress Bar */}
        <div style={{ width: "100px", height: "6px", background: "rgba(0, 240, 255, 0.15)", borderRadius: "3px", overflow: "hidden", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
          <div
            style={{
              width: `${(currentZoom / 9.0) * 100}%`,
              height: "100%",
              background: currentZoom >= 8.5 ? "linear-gradient(90deg, #00f0ff, #facc15)" : "linear-gradient(90deg, #0077ff, #00f0ff)",
              boxShadow: "0 0 8px #00f0ff",
              transition: "width 0.15s ease",
            }}
          />
        </div>

        {/* Transition Badge */}
        {currentZoom >= 8.5 ? (
          <div style={{ fontSize: "10px", color: "#facc15", background: "rgba(250, 204, 21, 0.2)", padding: "2px 8px", borderRadius: "4px", border: "1px solid #facc15", animation: "pulse 1.2s infinite" }}>
            ⚡ 9x LIMIT ➔ DIVE TO 2D
          </div>
        ) : (
          <div style={{ fontSize: "9.5px", color: "#64748b" }}>
            SCROLL IN TO DIVE
          </div>
        )}
      </div>

      {/* Floating Interactive Zoom Buttons (+ / - / Dive) */}
      <div
        style={{
          position: "absolute",
          right: "20px",
          top: "50%",
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          zIndex: 15,
        }}
      >
        <button
          onClick={() => handleZoomStep(-35)}
          style={{
            width: "38px",
            height: "38px",
            background: "rgba(1, 6, 18, 0.9)",
            border: "1.5px solid #00f0ff",
            color: "#00f0ff",
            borderRadius: "6px",
            fontSize: "18px",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 15px rgba(0, 240, 255, 0.3)",
            transition: "all 0.2s ease",
          }}
          title="Zoom In (Scroll Closer / Dive Past 9x)"
        >
          +
        </button>

        <button
          onClick={() => handleZoomStep(35)}
          style={{
            width: "38px",
            height: "38px",
            background: "rgba(1, 6, 18, 0.9)",
            border: "1.5px solid #00f0ff",
            color: "#00f0ff",
            borderRadius: "6px",
            fontSize: "18px",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 15px rgba(0, 240, 255, 0.3)",
            transition: "all 0.2s ease",
          }}
          title="Zoom Out (Orbital View)"
        >
          -
        </button>

        <button
          onClick={() => trigger2DDive()}
          style={{
            background: "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.35))",
            border: "1.5px solid #00f0ff",
            color: "#ffffff",
            borderRadius: "6px",
            padding: "8px 6px",
            fontSize: "9px",
            fontFamily: "'Orbitron', monospace",
            fontWeight: "bold",
            cursor: "pointer",
            writingMode: "vertical-rl",
            letterSpacing: "1.5px",
            boxShadow: "0 0 20px rgba(0, 240, 255, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Dive Directly into 2D Tactical Map"
        >
          🚀 2D DIVE
        </button>
      </div>

      {/* Top Right: Quick Strategic Node Selector */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          right: "16px",
          background: "rgba(1, 4, 10, 0.92)",
          border: "1px solid rgba(0, 240, 255, 0.35)",
          borderRadius: "6px",
          padding: "10px 12px",
          maxWidth: "280px",
          backdropFilter: "blur(8px)",
          boxShadow: "0 0 20px rgba(0, 240, 255, 0.15)",
          zIndex: 10,
        }}
      >
        <div style={{ color: "#00f0ff", fontFamily: "'Orbitron', monospace", fontSize: "11px", fontWeight: "bold", marginBottom: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>STRATEGIC SECTORS</span>
          <button
            onClick={() => setIsRotating((p) => !p)}
            style={{
              background: isRotating ? "rgba(0, 240, 255, 0.2)" : "rgba(248, 113, 113, 0.2)",
              border: `1px solid ${isRotating ? "#00f0ff" : "#f87171"}`,
              color: isRotating ? "#00f0ff" : "#f87171",
              fontSize: "9px",
              padding: "2px 6px",
              borderRadius: "3px",
              cursor: "pointer",
            }}
          >
            {isRotating ? "PAUSE ROTATION" : "RESUME"}
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "150px", overflowY: "auto" }}>
          {STRATEGIC_NODES.map((node) => {
            const isSelected = selectedNode?.name === node.name;
            return (
              <button
                key={node.name}
                onClick={() => selectNode(node)}
                onDoubleClick={() => trigger2DDive(node.lat, node.lng, node.name)}
                style={{
                  background: isSelected ? "rgba(0, 240, 255, 0.25)" : "rgba(1, 4, 10, 0.6)",
                  border: isSelected ? `1px solid ${node.color}` : "1px solid rgba(0, 240, 255, 0.15)",
                  color: isSelected ? "#ffffff" : "#94a3b8",
                  padding: "5px 8px",
                  borderRadius: "4px",
                  fontSize: "10px",
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
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: node.color }} />
                  <span style={{ fontWeight: isSelected ? "bold" : "normal" }}>{node.name}</span>
                </div>
                <span style={{ fontSize: "8.5px", color: node.color, fontFamily: "monospace" }}>[{node.type}]</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Center: Selected Node Focus Card & Direct Dive Action */}
      {selectedNode && (
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(1, 4, 10, 0.95)",
            border: `1.5px solid ${selectedNode.color}`,
            borderRadius: "8px",
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            gap: "18px",
            backdropFilter: "blur(10px)",
            boxShadow: `0 0 25px ${selectedNode.color}40`,
            zIndex: 10,
          }}
        >
          <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: selectedNode.color, boxShadow: `0 0 12px ${selectedNode.color}` }} />
          <div>
            <div style={{ color: "#ffffff", fontFamily: "'Orbitron', monospace", fontSize: "12px", fontWeight: "bold" }}>
              {selectedNode.name}
            </div>
            <div style={{ color: "#94a3b8", fontSize: "10px", fontFamily: "monospace", marginTop: "2px" }}>
              LAT: {selectedNode.lat.toFixed(4)}° // LNG: {selectedNode.lng.toFixed(4)}° // CLASSIFICATION: {selectedNode.type}
            </div>
          </div>

          <button
            onClick={() => trigger2DDive(selectedNode.lat, selectedNode.lng, selectedNode.name)}
            style={{
              background: `linear-gradient(135deg, ${selectedNode.color}50, rgba(0, 119, 255, 0.35))`,
              border: `1.5px solid ${selectedNode.color}`,
              color: "#ffffff",
              padding: "6px 14px",
              borderRadius: "5px",
              fontSize: "11px",
              fontWeight: "bold",
              fontFamily: "'Orbitron', monospace",
              cursor: "pointer",
              boxShadow: `0 0 15px ${selectedNode.color}50`,
              letterSpacing: "0.5px",
              whiteSpace: "nowrap",
            }}
          >
            ⚡ DIVE TO 2D SECTOR
          </button>
        </div>
      )}
    </div>
  );
};
