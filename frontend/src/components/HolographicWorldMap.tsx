import React, { useState } from "react";

export interface HolographicWorldMapProps {
  onOpenRegionMap: (regionKey: string, regionName: string) => void;
  isHomeView?: boolean;
}

interface WorldNode {
  id: string;
  name: string;
  country: string;
  x: number;
  y: number;
  status: string;
  ping: string;
}

export const HolographicWorldMap: React.FC<HolographicWorldMapProps> = ({
  onOpenRegionMap,
  isHomeView = true,
}) => {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);

  // Key Global Cyber Nodes
  const globalNodes: WorldNode[] = [
    { id: "delhi", name: "New Delhi", country: "india", x: 672, y: 228, status: "ONLINE", ping: "4ms" },
    { id: "mumbai", name: "Mumbai", country: "india", x: 658, y: 252, status: "ONLINE", ping: "6ms" },
    { id: "chennai", name: "Chennai", country: "india", x: 675, y: 278, status: "ONLINE", ping: "5ms" },
    { id: "bengaluru", name: "Bengaluru", country: "india", x: 668, y: 284, status: "ONLINE", ping: "4ms" },
    { id: "kolkata", name: "Kolkata", country: "india", x: 700, y: 236, status: "ONLINE", ping: "7ms" },
    { id: "tokyo", name: "Tokyo Hub", country: "japan", x: 848, y: 202, status: "SYNCED", ping: "28ms" },
    { id: "singapore", name: "Singapore Gateway", country: "singapore", x: 746, y: 308, status: "SYNCED", ping: "18ms" },
    { id: "dubai", name: "Dubai Relay", country: "middle_east", x: 605, y: 232, status: "ONLINE", ping: "22ms" },
    { id: "london", name: "London Satellite", country: "europe", x: 480, y: 162, status: "ONLINE", ping: "45ms" },
    { id: "paris", name: "Paris Node", country: "europe", x: 488, y: 178, status: "ONLINE", ping: "42ms" },
    { id: "newyork", name: "New York Terminal", country: "usa", x: 280, y: 188, status: "ONLINE", ping: "65ms" },
    { id: "sanfrancisco", name: "San Francisco Node", country: "usa", x: 195, y: 195, status: "ONLINE", ping: "68ms" },
    { id: "sydney", name: "Sydney Station", country: "australia", x: 868, y: 375, status: "STANDBY", ping: "52ms" },
    { id: "saopaulo", name: "São Paulo Node", country: "south_america", x: 345, y: 358, status: "ONLINE", ping: "74ms" },
    { id: "cairo", name: "Cairo Gateway", country: "africa", x: 546, y: 218, status: "ONLINE", ping: "38ms" },
  ];

  const handleMouseEnter = (region: string) => {
    setHoveredRegion(region);
  };

  const handleMouseLeave = () => {
    setHoveredRegion(null);
  };

  const isIndiaHovered = hoveredRegion === "india";

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "auto",
        zIndex: 0,
        overflow: "hidden",
        userSelect: "none",
      }}
    >
      {/* High-Resolution Futuristic Luminous World Map Projection */}
      <svg
        viewBox="0 0 1000 480"
        style={{
          width: "100%",
          height: "100%",
          maxHeight: isHomeView ? "88vh" : "75vh",
          maxWidth: "1500px",
          filter: "drop-shadow(0 0 16px rgba(0, 140, 255, 0.4))",
          opacity: isHomeView ? 0.95 : 0.65,
          transition: "opacity 0.4s ease",
        }}
      >
        <defs>
          {/* Cyber Gradients */}
          <linearGradient id="cyberLandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0a2540" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#071d36" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#031024" stopOpacity="0.85" />
          </linearGradient>

          <linearGradient id="hoverLandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0055aa" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#0088ff" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.4" />
          </linearGradient>

          <linearGradient id="indiaHoverGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.95" />
            <stop offset="50%" stopColor="#0088ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0044aa" stopOpacity="0.7" />
          </linearGradient>

          <filter id="neonStrokeGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="indiaActiveGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="5" result="b1" />
            <feGaussianBlur stdDeviation="2" result="b2" />
            <feMerge>
              <feMergeNode in="b1" />
              <feMergeNode in="b2" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <pattern id="cyberWorldGrid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(0, 200, 255, 0.04)" strokeWidth="0.6" />
            <circle cx="0" cy="0" r="0.8" fill="rgba(0, 240, 255, 0.12)" />
          </pattern>
        </defs>

        {/* 1. Cyber Mesh Coordinate Background */}
        <rect width="1000" height="480" fill="url(#cyberWorldGrid)" />

        {/* 2. Global Curvature Ellipses & Latitude / Longitude Graticule Lines */}
        <g stroke="rgba(0, 200, 255, 0.12)" strokeWidth="0.6" strokeDasharray="3 4" fill="none">
          <ellipse cx="500" cy="240" rx="465" ry="215" />
          <ellipse cx="500" cy="240" rx="360" ry="165" />
          <ellipse cx="500" cy="240" rx="240" ry="110" />
          <line x1="35" y1="240" x2="965" y2="240" stroke="rgba(0, 240, 255, 0.22)" strokeDasharray="none" />
          <line x1="500" y1="25" x2="500" y2="455" stroke="rgba(0, 240, 255, 0.22)" strokeDasharray="none" />
          <line x1="35" y1="150" x2="965" y2="150" />
          <line x1="35" y1="330" x2="965" y2="330" />
          <line x1="260" y1="25" x2="260" y2="455" />
          <line x1="740" y1="25" x2="740" y2="455" />
        </g>

        {/* 3. Global Satellite / Flight Data Arc Connections */}
        <g stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" strokeDasharray="3 4" fill="none">
          <path d="M 672 228 Q 570 140 480 162" /> {/* Delhi - London */}
          <path d="M 672 228 Q 760 170 848 202" /> {/* Delhi - Tokyo */}
          <path d="M 658 252 Q 628 238 605 232" /> {/* Mumbai - Dubai */}
          <path d="M 675 278 Q 710 290 746 308" /> {/* Chennai - Singapore */}
          <path d="M 746 308 Q 805 330 868 375" /> {/* Singapore - Sydney */}
          <path d="M 480 162 Q 380 130 280 188" /> {/* London - New York */}
          <path d="M 280 188 Q 235 188 195 195" /> {/* New York - San Francisco */}
          <path d="M 280 188 Q 315 270 345 358" /> {/* New York - Sao Paulo */}
        </g>

        {/* 4. REALISTIC DETAILED WORLD CONTINENTS SILHOUETTES */}
        <g stroke="#0077dd" strokeWidth="0.9" filter="url(#neonStrokeGlow)">
          
          {/* North America (Detailed Silhouette: Alaska, Canada, USA, Florida, Mexico) */}
          <path
            d="M 115 105 
               C 130 88, 160 78, 195 72 
               C 235 68, 275 80, 298 108 
               C 318 130, 310 165, 290 185 
               C 295 198, 305 215, 295 230 
               C 285 240, 275 238, 270 248 
               C 260 265, 250 282, 235 300 
               C 225 308, 218 298, 215 285 
               C 205 260, 190 235, 175 210 
               C 160 188, 140 180, 125 155 
               C 110 135, 105 118, 115 105 Z"
            fill={hoveredRegion === "north_america" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "north_america" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "north_america" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("north_america")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("north_america", "North America Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* Greenland */}
          <path
            d="M 335 55 C 355 48, 385 52, 395 70 C 400 88, 385 105, 365 110 C 345 105, 330 85, 335 55 Z"
            fill="url(#cyberLandGrad)"
            stroke="#0066cc"
          />

          {/* South America (Detailed Silhouette: Brazil, Andes, Argentina) */}
          <path
            d="M 268 305 
               C 295 300, 335 308, 355 330 
               C 375 352, 368 395, 345 425 
               C 328 448, 315 470, 295 480 
               C 285 475, 280 440, 275 410 
               C 268 375, 255 340, 260 320 
               C 262 310, 265 306, 268 305 Z"
            fill={hoveredRegion === "south_america" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "south_america" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "south_america" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("south_america")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("south_america", "South America Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* Europe & Scandinavia & UK */}
          <path
            d="M 450 148 
               C 460 120, 490 100, 520 108 
               C 538 112, 545 135, 540 152 
               C 530 170, 510 182, 485 188 
               C 468 190, 452 178, 448 165 Z"
            fill={hoveredRegion === "europe" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "europe" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "europe" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("europe")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("europe", "Europe Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* UK & Ireland */}
          <path d="M 442 138 C 448 132, 455 136, 452 146 C 446 152, 438 145, 442 138 Z" fill="url(#cyberLandGrad)" />

          {/* Africa & Madagascar */}
          <path
            d="M 470 205 
               C 505 195, 545 200, 565 225 
               C 585 250, 595 295, 575 340 
               C 555 385, 530 420, 505 425 
               C 490 415, 482 375, 475 330 
               C 465 285, 455 240, 465 215 Z"
            fill={hoveredRegion === "africa" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "africa" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "africa" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("africa")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("africa", "Africa Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* Madagascar */}
          <path d="M 602 345 C 608 340, 615 358, 608 375 C 602 370, 598 355, 602 345 Z" fill="url(#cyberLandGrad)" />

          {/* Northern Eurasia / Russia */}
          <path
            d="M 545 105 
               C 610 80, 720 75, 840 92 
               C 890 102, 915 125, 885 155 
               C 845 168, 780 162, 715 168 
               C 650 172, 580 160, 555 135 Z"
            fill={hoveredRegion === "russia" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "russia" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "russia" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("russia")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("russia", "Eurasia Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* Middle East */}
          <path
            d="M 570 210 
               C 595 205, 625 210, 635 230 
               C 640 248, 620 262, 598 260 
               C 580 255, 565 235, 570 210 Z"
            fill="url(#cyberLandGrad)"
            stroke="#0066cc"
          />

          {/* East Asia & China */}
          <path
            d="M 720 170 
               C 770 165, 830 175, 855 205 
               C 865 235, 830 265, 785 272 
               C 750 265, 725 240, 718 200 Z"
            fill={hoveredRegion === "east_asia" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "east_asia" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "east_asia" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("east_asia")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("east_asia", "East Asia Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />

          {/* Japan Archipelago */}
          <path d="M 870 185 C 878 190, 874 212, 862 225 C 858 215, 862 195, 870 185 Z" fill="url(#cyberLandGrad)" stroke="#0088ff" />

          {/* Southeast Asia & Indonesia */}
          <path
            d="M 740 270 
               C 765 275, 785 295, 775 320 
               C 755 335, 735 325, 730 300 Z"
            fill="url(#cyberLandGrad)"
            stroke="#0066cc"
          />
          <path d="M 750 330 C 785 332, 815 340, 810 350 C 780 348, 750 342, 750 330 Z" fill="url(#cyberLandGrad)" />

          {/* Australia & New Zealand */}
          <path
            d="M 805 340 
               C 845 330, 895 338, 915 365 
               C 925 395, 895 435, 845 430 
               C 810 422, 792 385, 805 340 Z"
            fill={hoveredRegion === "australia" ? "url(#hoverLandGrad)" : "url(#cyberLandGrad)"}
            stroke={hoveredRegion === "australia" ? "#00f0ff" : "#0088ff"}
            strokeWidth={hoveredRegion === "australia" ? "1.6" : "0.9"}
            onMouseEnter={() => handleMouseEnter("australia")}
            onMouseLeave={handleMouseLeave}
            onClick={() => onOpenRegionMap("australia", "Australia Sector")}
            style={{ cursor: "pointer", transition: "all 0.25s ease" }}
          />
          <path d="M 935 410 C 942 405, 948 420, 940 435 C 932 428, 930 415, 935 410 Z" fill="url(#cyberLandGrad)" />
        </g>

        {/* 5. INDIA SUBCONTINENT (ACCURATE REALISTIC SHAPE & NATURAL INTEGRATION) */}
        <g
          id="india_map_group"
          style={{
            cursor: "pointer",
            transformOrigin: "672px 255px",
            transform: isIndiaHovered ? "scale(1.18) translateY(-3px)" : "scale(1.0)",
            transition: "transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)",
            filter: isIndiaHovered ? "url(#indiaActiveGlow)" : "url(#neonStrokeGlow)",
          }}
          onMouseEnter={() => handleMouseEnter("india")}
          onMouseLeave={handleMouseLeave}
          onClick={() => onOpenRegionMap("india", "India National Cyber Grid")}
        >
          {/* Detailed Subcontinent Polygon (Kashmir -> Gujarat -> Kanyakumari -> Bengal -> NE) */}
          <path
            d="M 662 195 
               L 675 188 
               L 685 198 
               L 680 210 
               L 702 215 
               L 718 222 
               L 700 236 
               L 692 255 
               L 678 290 
               L 672 295 
               L 666 288 
               L 652 258 
               L 642 240 
               L 648 215 
               Z"
            fill={isIndiaHovered ? "url(#indiaHoverGrad)" : "url(#cyberLandGrad)"}
            stroke={isIndiaHovered ? "#00f0ff" : "#0088ff"}
            strokeWidth={isIndiaHovered ? "2.2" : "1.1"}
          />

          {/* Sri Lanka Node */}
          <ellipse cx="678" cy="305" rx="3.5" ry="5" fill={isIndiaHovered ? "#00f0ff" : "#0088ff"} opacity={isIndiaHovered ? 1 : 0.7} />

          {/* India Regional City Dots (Delhi, Mumbai, Chennai, Bengaluru, Kolkata) */}
          <circle cx="672" cy="228" r={isIndiaHovered ? "3.5" : "2.5"} fill="#ffffff" stroke="#00f0ff" strokeWidth="1" />
          <circle cx="658" cy="252" r={isIndiaHovered ? "3" : "2"} fill="#38bdf8" />
          <circle cx="675" cy="278" r={isIndiaHovered ? "3" : "2"} fill="#38bdf8" />
          <circle cx="668" cy="284" r={isIndiaHovered ? "3" : "2"} fill="#38bdf8" />
          <circle cx="700" cy="236" r={isIndiaHovered ? "3" : "2"} fill="#38bdf8" />

          {/* Temporary Hover Label for India */}
          {isIndiaHovered && (
            <text
              x="672"
              y="256"
              textAnchor="middle"
              fill="#ffffff"
              fontSize="8.5"
              fontFamily="'Orbitron', sans-serif"
              fontWeight="bold"
              letterSpacing="1px"
              style={{ textShadow: "0 0 8px #00f0ff", pointerEvents: "none" }}
            >
              INDIA
            </text>
          )}
        </g>

        {/* 6. Subtle Cyber Night City Lights Scatter (Realistic World Illumination Dots) */}
        <g fill="#00f0ff" opacity="0.65">
          {/* North America lights */}
          <circle cx="280" cy="188" r="1.5" /><circle cx="265" cy="195" r="1.2" /><circle cx="240" cy="205" r="1.2" /><circle cx="195" cy="195" r="1.5" /><circle cx="205" cy="220" r="1.2" />
          {/* Europe lights */}
          <circle cx="480" cy="162" r="1.5" /><circle cx="488" cy="178" r="1.5" /><circle cx="510" cy="160" r="1.2" /><circle cx="525" cy="148" r="1.2" /><circle cx="465" cy="195" r="1.2" />
          {/* East Asia lights */}
          <circle cx="848" cy="202" r="1.6" /><circle cx="810" cy="225" r="1.4" /><circle cx="830" cy="245" r="1.4" /><circle cx="780" cy="230" r="1.2" />
          {/* Middle East & Africa */}
          <circle cx="605" cy="232" r="1.4" /><circle cx="546" cy="218" r="1.2" /><circle cx="515" cy="405" r="1.2" />
          {/* Australia & South America */}
          <circle cx="868" cy="375" r="1.5" /><circle cx="885" cy="405" r="1.3" /><circle cx="345" cy="358" r="1.4" /><circle cx="330" cy="410" r="1.2" />
        </g>

        {/* 7. Key Global Node Markers with Hover / Click */}
        {globalNodes.filter((n) => n.country !== "india").map((node) => (
          <g
            key={node.id}
            transform={`translate(${node.x}, ${node.y})`}
            style={{ cursor: "pointer" }}
            onClick={() => onOpenRegionMap(node.country, node.name)}
            onMouseEnter={() => handleMouseEnter(node.id)}
            onMouseLeave={handleMouseLeave}
          >
            <circle r="3" fill="#00f0ff" opacity="0.85" />
            <circle r="6" fill="none" stroke="#00f0ff" strokeWidth="0.8" opacity="0.4" />
          </g>
        ))}
      </svg>

      {/* Floating Futuristic HUD Tooltip */}
      {hoveredRegion && (
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(1, 10, 25, 0.92)",
            border: "1px solid var(--jarvis-cyan)",
            borderRadius: "6px",
            padding: "8px 18px",
            color: "#fff",
            boxShadow: "0 0 18px rgba(0, 240, 255, 0.5), inset 0 0 10px rgba(0, 240, 255, 0.2)",
            backdropFilter: "blur(10px)",
            pointerEvents: "none",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            zIndex: 10,
            animation: "fadeIn 0.2s ease",
          }}
        >
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00f0ff", boxShadow: "0 0 8px #00f0ff" }} />
          <div>
            <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11.5px", fontWeight: "bold", color: "#00f0ff", letterSpacing: "1px" }}>
              {hoveredRegion === "india"
                ? "🇮🇳 INDIA REGIONAL CYBER GRID"
                : `${hoveredRegion.toUpperCase().replace("_", " ")} SECTOR`}
            </div>
            <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px" }}>
              {hoveredRegion === "india"
                ? "STATUS: ONLINE • CLICK OR PRESS 'MAP' TO OPEN HOLOGRAPHIC REAL-WORLD MAP"
                : "STATUS: SYNCED • CLICK TO INSPECT SECTOR"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
