import React from "react";
import type { GpuInfo } from "../types/assistant";

interface TelemetryHudProps {
  cpuVal: number;
  ramUsedGb: number;
  ramTotalGb: number;
  diskUsedGb: number;
  diskTotalGb: number;
  wifiSpeed: string;
  fanSpeed: string;
  memFreq: string;
  gpus: GpuInfo[];
}

/**
 * What does this component do:
 * Renders the futuristic JARVIS cybernetic HUD panel featuring real-time concentric ring gauges
 * for CPU load, RAM allocation, Disk storage, Network throughput, Fan RPM, Memory Frequency,
 * and Dual GPU telemetry (NVIDIA RTX 3050 & AMD Radeon Graphics load/temperatures).
 */
export const TelemetryHud: React.FC<TelemetryHudProps> = ({
  cpuVal,
  ramUsedGb,
  ramTotalGb,
  diskUsedGb,
  diskTotalGb,
  wifiSpeed,
  fanSpeed,
  memFreq,
  gpus,
}) => {
  return (
    <div className="jarvis-glass-card jarvis-panel-box" style={{ height: "100%", display: "flex", flexDirection: "column", padding: "10px" }}>
      <div className="jarvis-panel-title" style={{ marginBottom: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>SYSTEM MONITOR</span>
        <span style={{ fontSize: "8px", color: "#34d399", letterSpacing: "1px" }}>LIVE ●</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 6px", alignItems: "center", justifyItems: "center", flex: 1, overflowY: "auto", paddingBottom: "6px" }}>

        {/* 1. CPU Load */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${cpuVal * 3.6}deg, rgba(0,240,255,0.12) ${cpuVal * 3.6}deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#00f0ff" }}>CPU</span>
                <span className="gauge-val">{cpuVal}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* 2. RAM Allocation */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${(ramUsedGb / ramTotalGb) * 360}deg, rgba(0,240,255,0.12) ${(ramUsedGb / ramTotalGb) * 360}deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#00f0ff" }}>RAM</span>
                <span className="gauge-val-small">{ramUsedGb}/{ramTotalGb}G</span>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Disk Space */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#38bdf8 0deg ${(diskUsedGb / diskTotalGb) * 360}deg, rgba(56,189,248,0.12) ${(diskUsedGb / diskTotalGb) * 360}deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#38bdf8" }}>DISK</span>
                <span className="gauge-val-small">{diskUsedGb}/{diskTotalGb}G</span>
              </div>
            </div>
          </div>
        </div>

        {/* 4. WiFi Throughput */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#38bdf8 0deg 240deg, rgba(56,189,248,0.12) 240deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#38bdf8" }}>NET I/O</span>
                <span className="gauge-val-small">{wifiSpeed}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 5. Hardware Fan Speed */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#34d399 0deg ${Math.min(360, (parseInt(fanSpeed) || 2800) / 4500 * 360)}deg, rgba(52,211,153,0.12) ${Math.min(360, (parseInt(fanSpeed) || 2800) / 4500 * 360)}deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#34d399" }}>FAN</span>
                <span className="gauge-val-tiny" style={{ color: "#fff", fontWeight: "bold" }}>{fanSpeed}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 6. RAM Frequency */}
        <div className="jarvis-gauge-card">
          <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#a78bfa 0deg ${Math.min(360, (parseInt(memFreq) || 4800) / 6400 * 360)}deg, rgba(167,139,250,0.12) ${Math.min(360, (parseInt(memFreq) || 4800) / 6400 * 360)}deg 360deg)` }}>
            <div className="jarvis-ring-layer-2">
              <div className="jarvis-gauge-inner">
                <span className="gauge-title" style={{ color: "#a78bfa" }}>MEM CLK</span>
                <span className="gauge-val-tiny" style={{ color: "#fff", fontWeight: "bold" }}>{memFreq}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 7. GPU 0 Load (RTX 3050) */}
        {gpus.filter(g => g.id === "gpu0").map((gpu) => (
          <div className="jarvis-gauge-card" key="gpu0-load">
            <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${gpu.load * 3.6}deg, rgba(0,240,255,0.12) ${gpu.load * 3.6}deg 360deg)` }}>
              <div className="jarvis-ring-layer-2">
                <div className="jarvis-gauge-inner">
                  <span className="gauge-title" style={{ color: "#00f0ff" }}>GPU 0</span>
                  <span className="gauge-val">{gpu.load}%</span>
                  <span className="gpu-subtitle">RTX</span>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* 8. GPU 0 Temp (RTX 3050) */}
        {gpus.filter(g => g.id === "gpu0").map((gpu) => (
          <div className="jarvis-gauge-card" key="gpu0-temp">
            <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#f87171 0deg ${Math.min(360, (gpu.temp / 100) * 360)}deg, rgba(248,113,113,0.12) ${Math.min(360, (gpu.temp / 100) * 360)}deg 360deg)` }}>
              <div className="jarvis-ring-layer-2">
                <div className="jarvis-gauge-inner">
                  <span className="gauge-title" style={{ color: "#f87171" }}>TEMP(G0)</span>
                  <span className="gauge-val">{gpu.temp}°C</span>
                  <span className="gpu-subtitle">RTX</span>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* 9. GPU 1 Load (AMD Radeon) */}
        {gpus.filter(g => g.id === "gpu1").map((gpu) => (
          <div className="jarvis-gauge-card" key="gpu1-load">
            <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#fb923c 0deg ${gpu.load * 3.6}deg, rgba(251,146,60,0.12) ${gpu.load * 3.6}deg 360deg)` }}>
              <div className="jarvis-ring-layer-2">
                <div className="jarvis-gauge-inner">
                  <span className="gauge-title" style={{ color: "#fb923c" }}>GPU 1</span>
                  <span className="gauge-val">{gpu.load}%</span>
                  <span className="gpu-subtitle">RADEON</span>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* 10. GPU 1 Temp (AMD Radeon) */}
        {gpus.filter(g => g.id === "gpu1").map((gpu) => (
          <div className="jarvis-gauge-card" key="gpu1-temp">
            <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#f87171 0deg ${Math.min(360, (gpu.temp / 100) * 360)}deg, rgba(248,113,113,0.12) ${Math.min(360, (gpu.temp / 100) * 360)}deg 360deg)` }}>
              <div className="jarvis-ring-layer-2">
                <div className="jarvis-gauge-inner">
                  <span className="gauge-title" style={{ color: "#f87171" }}>TEMP(G1)</span>
                  <span className="gauge-val">{gpu.temp}°C</span>
                  <span className="gpu-subtitle">RADEON</span>
                </div>
              </div>
            </div>
          </div>
        ))}

      </div>
    </div>
  );
};
