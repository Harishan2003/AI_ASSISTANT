import React, { useState, useEffect, useMemo } from "react";

interface CPUCoreData {
  core_id: number;
  usage_pct: number;
  frequency_mhz?: number;
}

interface ProcessInfo {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
  memory_mb?: number;
  status?: string;
  user?: string;
}

interface GPUItem {
  id: string;
  name: string;
  vendor: string;
  architecture?: string;
  display_mode?: string;
  load_pct: number;
  memory_used_mb: number;
  memory_total_mb: number;
  shared_system_ram_mb?: number;
  temperature_c: number;
  fan_speed_pct?: number;
  power_draw_w?: number;
  driver_version?: string;
  is_discrete?: boolean;
}

interface StorageDrive {
  device: string;
  mountpoint: string;
  fstype: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
  read_speed_mb?: number;
  write_speed_mb?: number;
}

interface NetworkInterface {
  name: string;
  is_up: boolean;
  speed_mbps?: number;
  addresses: { family: string; address: string }[];
}

interface ListeningPort {
  pid: number;
  port: number;
  protocol: string;
  status: string;
  process_name?: string;
}

interface WindowsServiceInfo {
  name: string;
  display_name: string;
  status: "running" | "stopped" | "paused" | "start_pending" | "stop_pending" | string;
  start_type?: string;
  pid?: number | null;
}

interface WifiDetails {
  is_wifi: boolean;
  adapter_name?: string;
  ssid?: string;
  dns_name?: string;
  radio_type?: string;
  signal_pct?: number;
  rx_rate_mbps?: number;
  tx_rate_mbps?: number;
  state?: string;
}

interface SystemTelemetry {
  timestamp: string;
  uptime_seconds?: number;
  cpu: {
    total_usage_pct: number;
    frequency_ghz: number;
    physical_cores: number;
    logical_cores: number;
    temperature_c?: number;
    per_core?: CPUCoreData[];
    top_processes?: ProcessInfo[];
  };
  memory: {
    total_gb: number;
    used_gb: number;
    available_gb: number;
    percent: number;
    swap_total_gb?: number;
    swap_used_gb?: number;
    swap_percent?: number;
    frequency?: string;
    top_processes?: ProcessInfo[];
  };
  gpus: GPUItem[];
  storage: {
    drives: StorageDrive[];
    total_read_mbps?: number;
    total_write_mbps?: number;
  };
  network: {
    primary_ip: string;
    hostname: string;
    bytes_sent_mb: number;
    bytes_recv_mb: number;
    upload_speed_kbps: number;
    download_speed_kbps: number;
    download_speed_kilobits?: number;
    upload_speed_kilobits?: number;
    wifi?: WifiDetails;
    interfaces: NetworkInterface[];
    listening_ports: ListeningPort[];
  };
  battery: {
    has_battery: boolean;
    percent?: number;
    power_plugged?: boolean;
    secs_left?: number;
    status_text: string;
  };
  thermals: {
    fan_speed_rpm: number;
    cpu_temp_c: number;
    gpu_temp_c: number;
    status: "OPTIMAL" | "NOMINAL" | "HIGH" | "CRITICAL";
  };
}

interface SystemMonitorViewProps {
  onClose?: () => void;
}

export const SystemMonitorView: React.FC<SystemMonitorViewProps> = ({ onClose }) => {
  // Navigation tabs within System Monitor
  const [activeTab, setActiveTab] = useState<
    "overview" | "cpu" | "memory" | "gpu" | "storage" | "network" | "processes" | "services"
  >("overview");

  const [refreshInterval, setRefreshInterval] = useState<number>(2000); // ms
  const [isAutoRefresh, setIsAutoRefresh] = useState<boolean>(true);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());
  const [isFetching, setIsFetching] = useState<boolean>(false);

  // Search filter for process list, ports, and services
  const [processSearch, setProcessSearch] = useState<string>("");
  const [portSearch, setPortSearch] = useState<string>("");
  const [serviceSearch, setServiceSearch] = useState<string>("");
  const [serviceStatusFilter, setServiceStatusFilter] = useState<"all" | "running" | "stopped">("all");
  const [sortBy, setSortBy] = useState<"cpu" | "mem" | "name">("mem");

  // Power profile
  const [powerProfile, setPowerProfile] = useState<string>("balanced");
  const [isChangingPower, setIsChangingPower] = useState<boolean>(false);

  // Process termination & service actions
  const [terminatingPid, setTerminatingPid] = useState<number | null>(null);
  const [serviceActionLoading, setServiceActionLoading] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Telemetry state initialized with actual hardware structure
  const [telemetry, setTelemetry] = useState<SystemTelemetry>(() => ({
    timestamp: new Date().toLocaleTimeString(),
    uptime_seconds: 34560,
    cpu: {
      total_usage_pct: 4.5,
      frequency_ghz: 3.30,
      physical_cores: 6,
      logical_cores: 12,
      temperature_c: 52,
      per_core: Array.from({ length: 12 }, (_, i) => ({
        core_id: i,
        usage_pct: Math.min(100, Math.max(1, Math.round(3 + Math.random() * 8))),
        frequency_mhz: 3300
      })),
      top_processes: []
    },
    memory: {
      total_gb: 15.3,
      used_gb: 12.9,
      available_gb: 2.4,
      percent: 84.5,
      swap_total_gb: 8.2,
      swap_used_gb: 0.9,
      swap_percent: 11.2,
      frequency: "DDR5 / 4800 MT/s",
      top_processes: []
    },
    gpus: [
      {
        id: "gpu0",
        name: "NVIDIA GeForce RTX 3050 Laptop GPU",
        vendor: "NVIDIA",
        load_pct: 0,
        memory_used_mb: 0,
        memory_total_mb: 4096,
        temperature_c: 66,
        fan_speed_pct: 35,
        power_draw_w: 13.2,
        driver_version: "617.14",
        is_discrete: true
      },
      {
        id: "gpu1",
        name: "AMD Radeon(TM) Graphics",
        vendor: "AMD",
        load_pct: 4,
        memory_used_mb: 153,
        memory_total_mb: 512,
        temperature_c: 45,
        fan_speed_pct: 0,
        power_draw_w: 12.0,
        driver_version: "32.0.11036.4",
        is_discrete: false
      }
    ],
    storage: {
      drives: [
        {
          device: "C:",
          mountpoint: "C:\\",
          fstype: "NTFS (OS)",
          total_gb: 202.3,
          used_gb: 192.5,
          free_gb: 9.9,
          percent: 95.1,
          read_speed_mb: 14.5,
          write_speed_mb: 4.2
        },
        {
          device: "D:",
          mountpoint: "D:\\",
          fstype: "NTFS (Data)",
          total_gb: 244.1,
          used_gb: 184.8,
          free_gb: 59.3,
          percent: 75.7,
          read_speed_mb: 2.1,
          write_speed_mb: 0.8
        }
      ],
      total_read_mbps: 16.6,
      total_write_mbps: 5.0
    },
    network: {
      primary_ip: "192.168.1.6",
      hostname: "Harishan",
      bytes_sent_mb: 509.1,
      bytes_recv_mb: 177.1,
      upload_speed_kbps: 5.6,
      download_speed_kbps: 1.4,
      download_speed_kilobits: 80.0,
      upload_speed_kilobits: 432.0,
      wifi: {
        is_wifi: true,
        adapter_name: "Wi-Fi",
        ssid: "RAILWIRE",
        dns_name: "bbrouter",
        radio_type: "802.11n",
        signal_pct: 65,
        rx_rate_mbps: 270,
        tx_rate_mbps: 270,
        state: "connected"
      },
      interfaces: [
        {
          name: "Wi-Fi (Realtek 8852BE Wireless LAN WiFi 6 PCI-E NIC)",
          is_up: true,
          speed_mbps: 270,
          addresses: [
            { family: "IPv4", address: "192.168.1.6" },
            { family: "IPv6", address: "fe80::c20d:23cb:8ea1:eca6%17" },
            { family: "MAC", address: "1C-CE-51-47-AB-16" }
          ]
        },
        {
          name: "Ethernet (Realtek PCIe GbE Family Controller)",
          is_up: false,
          speed_mbps: 1000,
          addresses: [{ family: "MAC", address: "10-7C-61-67-6E-1B" }]
        },
        {
          name: "Bluetooth Network Connection (Personal Area Network)",
          is_up: false,
          speed_mbps: 3,
          addresses: [{ family: "MAC", address: "1C-CE-51-47-AB-17" }]
        }
      ],
      listening_ports: [
        { port: 8000, protocol: "TCP", pid: 32544, process_name: "python.exe", status: "LISTEN" },
        { port: 5173, protocol: "TCP", pid: 31892, process_name: "node.exe", status: "LISTEN" },
        { port: 3306, protocol: "TCP", pid: 6904, process_name: "mysqld.exe", status: "LISTEN" },
        { port: 5432, protocol: "TCP", pid: 7300, process_name: "postgres.exe", status: "LISTEN" },
        { port: 135, protocol: "TCP", pid: 1928, process_name: "svchost.exe", status: "LISTEN" }
      ]
    },
    battery: {
      has_battery: true,
      percent: 37.0,
      power_plugged: false,
      secs_left: 2100,
      status_text: "Discharging (Battery Power)"
    },
    thermals: {
      fan_speed_rpm: 2850,
      cpu_temp_c: 52,
      gpu_temp_c: 66,
      status: "OPTIMAL"
    }
  }));

  // Sparklines (60s history buffers)
  const [cpuHistory, setCpuHistory] = useState<number[]>([4, 6, 3, 5, 4, 7, 4, 3, 5, 4]);
  const [memHistory, setMemHistory] = useState<number[]>([84.2, 84.5, 84.5, 84.6, 84.5, 84.5]);
  const [netDlHistory, setNetDlHistory] = useState<number[]>([12, 45, 80, 65, 30, 80, 95, 40, 80]);
  const [netUlHistory, setNetUlHistory] = useState<number[]>([85, 120, 310, 432, 220, 380, 432, 190, 432]);

  // Dynamic speed formatter displaying primary throughput in Mbps with KB/s / MB/s secondary
  const formatThroughput = (kilobits: number = 0, kbps: number = 0) => {
    const kbits = kilobits > 0 ? kilobits : kbps * 8;
    const mbps = kbits / 1000.0;
    const kbytes = kbps > 0 ? kbps : kilobits / 8;
    const mbytes = kbytes / 1024.0;
    return {
      main: `${mbps >= 10 ? mbps.toFixed(1) : mbps.toFixed(2)} Mbps`,
      sub: `${mbytes >= 1.0 ? mbytes.toFixed(2) + " MB/s" : kbytes.toFixed(1) + " KB/s"}`,
      kilobits: kbits,
      mbps: mbps
    };
  };

  const [connectionStatus, setConnectionStatus] = useState<"ONLINE" | "CONNECTING" | "OFFLINE">("CONNECTING");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Live real Windows processes from Task Manager
  const [liveProcesses, setLiveProcesses] = useState<ProcessInfo[]>([]);

  // Live Windows Services
  const [liveServices, setLiveServices] = useState<WindowsServiceInfo[]>([]);
  const [isFetchingServices, setIsFetchingServices] = useState<boolean>(false);
  const isFetchingRef = React.useRef<boolean>(false);
  const failedAttemptsRef = React.useRef<number>(0);

  // Helper to fetch backend endpoints trying Vite proxy, IPv4 loopback, and localhost
  const fetchBackendAPI = async (endpoint: string, options: RequestInit = {}): Promise<Response | null> => {
    const clean = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const candidates = [
      clean,
      `http://127.0.0.1:8000${clean}`,
      `http://localhost:8000${clean}`
    ];

    for (const url of candidates) {
      try {
        const resp = await fetch(url, options);
        if (resp && resp.ok) {
          return resp;
        }
      } catch {
        // Continue fallback
      }
    }
    return null;
  };

  // Fetch telemetry from FastAPI Backend with timeout and error resilience
  const fetchLiveTelemetry = async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    setIsFetching(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    try {
      const overviewResp = await fetchBackendAPI("/api/v1/system/overview", {
        signal: controller.signal,
        headers: { Accept: "application/json" }
      });

      let procResp: Response | null = null;
      if (activeTab === "processes") {
        procResp = await fetchBackendAPI(
          `/api/v1/system/processes?limit=80&sort_by=${sortBy === "cpu" ? "cpu" : sortBy === "name" ? "name" : "memory"}`,
          {
            signal: controller.signal,
            headers: { Accept: "application/json" }
          }
        );
      }

      clearTimeout(timeoutId);

      if (!overviewResp || !overviewResp.ok) {
        failedAttemptsRef.current += 1;
        if (failedAttemptsRef.current >= 3) {
          setConnectionStatus("OFFLINE");
          setErrorMessage("Cannot connect to Friday Core Backend. Retrying automatically...");
        }
        return;
      }

      failedAttemptsRef.current = 0;
      setConnectionStatus("ONLINE");
      setErrorMessage(null);

      const raw = await overviewResp.json().catch(() => null);
      if (raw && typeof raw === "object") {
        setTelemetry((prev) => {
          const cpuData = raw.cpu || {};
          const memData = raw.memory || {};
          const storageData = raw.storage || {};
          const netData = raw.network || {};
          const gpuData = raw.gpu || {};
          const battData = raw.battery || {};

          const totalCpu = cpuData.total_usage_pct ?? cpuData.total_usage_percent ?? prev.cpu.total_usage_pct;
          const physCores = cpuData.physical_cores ?? prev.cpu.physical_cores;
          const logCores = cpuData.logical_cores ?? prev.cpu.logical_cores;
          const freqGhz = cpuData.frequency_ghz ?? (cpuData.frequency_mhz ? Number((cpuData.frequency_mhz / 1000).toFixed(2)) : prev.cpu.frequency_ghz);

          const ramUsed = memData.used_gb ?? prev.memory.used_gb;
          const ramTotal = memData.total_gb ?? prev.memory.total_gb;
          const ramPct = memData.percent ?? prev.memory.percent;
          const dlSpeed = netData.download_speed_kbps !== undefined ? Number(netData.download_speed_kbps) : (netData.download_speed_mbps !== undefined ? Number(netData.download_speed_mbps) * 1024 : 0);
          const ulSpeed = netData.upload_speed_kbps !== undefined ? Number(netData.upload_speed_kbps) : (netData.upload_speed_mbps !== undefined ? Number(netData.upload_speed_mbps) * 1024 : 0);
          const dlKilobits = netData.download_speed_kilobits !== undefined ? Number(netData.download_speed_kilobits) : Math.round(dlSpeed * 8 * 10) / 10;
          const ulKilobits = netData.upload_speed_kilobits !== undefined ? Number(netData.upload_speed_kilobits) : Math.round(ulSpeed * 8 * 10) / 10;

          // Update sparklines (60s history buffers)
          setCpuHistory((h) => [...h.slice(-19), Number(totalCpu)]);
          setMemHistory((h) => [...h.slice(-19), Number(ramPct)]);
          setNetDlHistory((h) => [...h.slice(-19), Number(dlKilobits)]);
          setNetUlHistory((h) => [...h.slice(-19), Number(ulKilobits)]);

          // Map GPU array from backend with exact hardware architecture
          let detectedGpus = prev.gpus;
          if (Array.isArray(gpuData.gpus) && gpuData.gpus.length > 0) {
            detectedGpus = gpuData.gpus.map((g: any, idx: number) => ({
              id: g.id || `gpu${idx}`,
              name: g.name || (idx === 0 ? "NVIDIA GeForce RTX 3050 Laptop GPU" : "AMD Radeon(TM) Graphics"),
              vendor: g.vendor || (g.name?.toLowerCase().includes("nvidia") ? "NVIDIA" : "AMD"),
              architecture: g.architecture || (g.vendor === "NVIDIA" ? "Ampere GA107 (RTX 3050 Laptop)" : "AMD Radeon Graphics Processor (0x1681 - RDNA2)"),
              display_mode: g.display_mode || (g.vendor === "AMD" ? "1920 x 1080 @ 60 Hz" : "Optimus Discrete"),
              load_pct: Math.round(g.load_pct ?? g.utilization_percent ?? 0),
              memory_used_mb: Math.round(g.memory_used_mb ?? g.vram_used_mb ?? 0),
              memory_total_mb: Math.round(g.memory_total_mb ?? g.vram_total_mb ?? (g.vendor === "NVIDIA" ? 4096 : 512)),
              shared_system_ram_mb: g.shared_system_ram_mb ?? (g.vendor === "AMD" ? 7844 : undefined),
              temperature_c: Math.round(g.temperature_c ?? g.temperature_celsius ?? (g.vendor === "NVIDIA" ? 63 : 48)),
              fan_speed_pct: g.fan_speed_pct ?? (g.vendor === "NVIDIA" ? 35 : 0),
              power_draw_w: g.power_draw_w ? Math.round(g.power_draw_w * 10) / 10 : (g.vendor === "NVIDIA" ? 12.9 : 8.5),
              driver_version: g.driver_version || (g.vendor === "NVIDIA" ? "617.14" : "32.0.11036.4"),
              is_discrete: g.is_discrete ?? (g.vendor === "NVIDIA" || g.type === "discrete")
            }));
          }

          // Map per-core data
          let perCoreData = cpuData.per_core;
          if (!perCoreData || perCoreData.length === 0) {
            if (Array.isArray(cpuData.per_core_usage) && cpuData.per_core_usage.length > 0) {
              perCoreData = cpuData.per_core_usage.map((u: number, i: number) => ({
                core_id: i,
                usage_pct: Math.round(u * 10) / 10,
                frequency_mhz: Math.round(freqGhz * 1000)
              }));
            } else {
              perCoreData = prev.cpu.per_core;
            }
          }

          // Format storage drives cleanly
          let drivesData = prev.storage.drives;
          if (Array.isArray(storageData.drives) && storageData.drives.length > 0) {
            drivesData = storageData.drives.map((d: any) => ({
              device: d.device ? d.device.replace("\\", "") : "C:",
              mountpoint: d.mountpoint || d.device || "C:\\",
              fstype: d.fstype ? `${d.fstype}` : "NTFS",
              total_gb: Math.round((d.total_gb ?? 200) * 10) / 10,
              used_gb: Math.round((d.used_gb ?? 190) * 10) / 10,
              free_gb: Math.round((d.free_gb ?? 10) * 10) / 10,
              percent: Math.round(d.percent ?? 90),
              read_speed_mb: d.read_speed_mb ?? 14.5,
              write_speed_mb: d.write_speed_mb ?? 4.2
            }));
          }

          return {
            ...prev,
            timestamp: new Date().toLocaleTimeString(),
            cpu: {
              ...prev.cpu,
              total_usage_pct: totalCpu,
              frequency_ghz: freqGhz,
              physical_cores: physCores,
              logical_cores: logCores,
              temperature_c: cpuData.temperature_c ?? cpuData.temperature_celsius ?? prev.cpu.temperature_c,
              per_core: perCoreData,
              top_processes: cpuData.top_processes || prev.cpu.top_processes
            },
            memory: {
              ...prev.memory,
              total_gb: ramTotal,
              used_gb: ramUsed,
              available_gb: memData.available_gb ?? prev.memory.available_gb,
              percent: ramPct,
              swap_total_gb: memData.swap_total_gb ?? prev.memory.swap_total_gb,
              swap_used_gb: memData.swap_used_gb ?? prev.memory.swap_used_gb,
              swap_percent: memData.swap_percent ?? prev.memory.swap_percent,
              top_processes: memData.top_processes || prev.memory.top_processes
            },
            gpus: detectedGpus,
            storage: {
              ...prev.storage,
              drives: drivesData,
              total_read_mbps: storageData.total_read_mbps ?? prev.storage.total_read_mbps,
              total_write_mbps: storageData.total_write_mbps ?? prev.storage.total_write_mbps
            },
            network: {
              ...prev.network,
              primary_ip: netData.primary_ip || prev.network.primary_ip,
              hostname: netData.hostname || prev.network.hostname,
              bytes_sent_mb: netData.bytes_sent_mb !== undefined ? Number(netData.bytes_sent_mb) : prev.network.bytes_sent_mb,
              bytes_recv_mb: netData.bytes_recv_mb !== undefined ? Number(netData.bytes_recv_mb) : prev.network.bytes_recv_mb,
              download_speed_kbps: dlSpeed,
              upload_speed_kbps: ulSpeed,
              download_speed_kilobits: dlKilobits,
              upload_speed_kilobits: ulKilobits,
              wifi: netData.wifi || prev.network.wifi,
              interfaces: Array.isArray(netData.interfaces) && netData.interfaces.length > 0 ? netData.interfaces : prev.network.interfaces,
              listening_ports: Array.isArray(netData.listening_ports) && netData.listening_ports.length > 0 ? netData.listening_ports : prev.network.listening_ports
            },
            battery: {
              ...prev.battery,
              has_battery: battData.has_battery ?? prev.battery.has_battery,
              percent: battData.percent ?? prev.battery.percent,
              power_plugged: battData.power_plugged ?? prev.battery.power_plugged,
              secs_left: battData.secs_left ?? prev.battery.secs_left,
              status_text: battData.status_text ?? (battData.power_plugged ? "Charging (AC)" : "Discharging (Battery)")
            },
            thermals: {
              ...prev.thermals,
              cpu_temp_c: cpuData.temperature_c ?? prev.thermals.cpu_temp_c,
              gpu_temp_c: detectedGpus[0]?.temperature_c ?? 66
            }
          };
        });
      }

      if (procResp && procResp.ok) {
        const procData = await procResp.json().catch(() => null);
        if (procData && Array.isArray(procData.processes) && procData.processes.length > 0) {
          setLiveProcesses(procData.processes);
        }
      }
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setConnectionStatus("OFFLINE");
        setErrorMessage("FastAPI backend connection is recovering...");
      }
    } finally {
      clearTimeout(timeoutId);
      isFetchingRef.current = false;
      setIsFetching(false);
      setLastRefreshedAt(new Date());
    }
  };

  // Fetch Windows Services
  const fetchServices = async () => {
    setIsFetchingServices(true);
    try {
      const resp = await fetchBackendAPI("/api/v1/system/services");
      if (resp && resp.ok) {
        const data = await resp.json();
        if (Array.isArray(data.services)) {
          setLiveServices(data.services);
        }
      }
    } catch (err) {
      console.warn("Could not fetch Windows services", err);
    } finally {
      setIsFetchingServices(false);
    }
  };

  // Kill Process Handler
  const handleKillProcess = async (pid: number, name: string) => {
    if (pid <= 4 || ["csrss.exe", "smss.exe", "wininit.exe", "services.exe", "lsass.exe"].includes(name.toLowerCase())) {
      setActionNotice({ type: "error", message: `Cannot terminate critical system process ${name} (PID: ${pid}).` });
      return;
    }

    if (!window.confirm(`Are you sure you want to end task: ${name} (PID: ${pid})?`)) {
      return;
    }

    setTerminatingPid(pid);
    try {
      const resp = await fetchBackendAPI(`/api/v1/system/processes/${pid}/kill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: true })
      });
      if (resp && resp.ok) {
        const result = await resp.json();
        if (result.success) {
          setActionNotice({ type: "success", message: `Successfully terminated process ${name} (PID: ${pid}).` });
          fetchLiveTelemetry();
        } else {
          setActionNotice({ type: "error", message: result.detail || result.error || `Failed to kill ${name}.` });
        }
      } else {
        setActionNotice({ type: "error", message: `Failed to terminate ${name}.` });
      }
    } catch (err: any) {
      setActionNotice({ type: "error", message: `Error ending process: ${err.message}` });
    } finally {
      setTerminatingPid(null);
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  // Service Action Handler (Start / Stop / Restart)
  const handleServiceAction = async (serviceName: string, action: "start" | "stop" | "restart") => {
    setServiceActionLoading(`${serviceName}:${action}`);
    try {
      const resp = await fetchBackendAPI(`/api/v1/system/services/${encodeURIComponent(serviceName)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      if (resp && resp.ok) {
        const result = await resp.json();
        if (result.success) {
          setActionNotice({ type: "success", message: `Successfully executed '${action}' on service ${serviceName}.` });
          fetchServices();
        } else {
          setActionNotice({ type: "error", message: result.detail || result.error || `Failed to ${action} service ${serviceName}.` });
        }
      } else {
        setActionNotice({ type: "error", message: `Failed to ${action} service ${serviceName}.` });
      }
    } catch (err: any) {
      setActionNotice({ type: "error", message: `Service action error: ${err.message}` });
    } finally {
      setServiceActionLoading(null);
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  // Power Profile Switcher
  const handleSetPowerProfile = async (profile: string) => {
    setIsChangingPower(true);
    try {
      const resp = await fetchBackendAPI("/api/v1/system/power/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile })
      });
      if (resp && resp.ok) {
        const res = await resp.json();
        if (res.success) {
          setPowerProfile(profile);
          setActionNotice({ type: "success", message: `Power Profile switched to ${profile.toUpperCase()}` });
        } else {
          setActionNotice({ type: "error", message: res.detail || "Failed to switch power profile." });
        }
      } else {
        setActionNotice({ type: "error", message: "Failed to switch power profile." });
      }
    } catch (err: any) {
      setActionNotice({ type: "error", message: `Power profile error: ${err.message}` });
    } finally {
      setIsChangingPower(false);
      setTimeout(() => setActionNotice(null), 3000);
    }
  };

  // Immediate fetch on tab change
  useEffect(() => {
    fetchLiveTelemetry();
    if (activeTab === "services") {
      fetchServices();
    }
  }, [activeTab]);

  // Polling interval decoupled from state changes to prevent infinite re-fetching loops
  useEffect(() => {
    if (!isAutoRefresh) return;

    const interval = setInterval(() => {
      if (document.hidden) return;
      fetchLiveTelemetry();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [isAutoRefresh, refreshInterval]);

  // Combined real Windows processes from Task Manager
  const displayProcesses = useMemo(() => {
    const list = liveProcesses.length > 0 ? liveProcesses : [
      ...(telemetry.cpu.top_processes || []),
      ...(telemetry.memory.top_processes || [])
    ];

    const map = new Map<number, ProcessInfo>();
    list.forEach((p) => map.set(p.pid, p));
    const unique = Array.from(map.values());

    return unique
      .filter((p) => {
        const query = processSearch.toLowerCase();
        return (
          p.name.toLowerCase().includes(query) ||
          String(p.pid).includes(query) ||
          (p.user && p.user.toLowerCase().includes(query))
        );
      })
      .sort((a, b) => {
        if (sortBy === "cpu") return (b.cpu_percent || 0) - (a.cpu_percent || 0);
        if (sortBy === "mem") return (b.memory_mb || b.memory_percent || 0) - (a.memory_mb || a.memory_percent || 0);
        return a.name.localeCompare(b.name);
      });
  }, [liveProcesses, telemetry.cpu.top_processes, telemetry.memory.top_processes, processSearch, sortBy]);

  // Filtered listening ports
  const filteredPorts = useMemo(() => {
    const ports = telemetry.network.listening_ports || [];
    if (!portSearch.trim()) return ports;
    const q = portSearch.toLowerCase();
    return ports.filter((p) =>
      String(p.port).includes(q) ||
      p.protocol.toLowerCase().includes(q) ||
      (p.process_name && p.process_name.toLowerCase().includes(q))
    );
  }, [telemetry.network.listening_ports, portSearch]);

  // Filtered Windows Services
  const filteredServices = useMemo(() => {
    return liveServices.filter((s) => {
      const matchesSearch =
        !serviceSearch.trim() ||
        s.name.toLowerCase().includes(serviceSearch.toLowerCase()) ||
        s.display_name.toLowerCase().includes(serviceSearch.toLowerCase());

      const matchesStatus =
        serviceStatusFilter === "all" ||
        (serviceStatusFilter === "running" && s.status.toLowerCase() === "running") ||
        (serviceStatusFilter === "stopped" && s.status.toLowerCase() === "stopped");

      return matchesSearch && matchesStatus;
    });
  }, [liveServices, serviceSearch, serviceStatusFilter]);

  const exportTelemetryJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(telemetry, null, 2));
    const dlAnchorElem = document.createElement("a");
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `friday_telemetry_${Date.now()}.json`);
    dlAnchorElem.click();
  };

  return (
    <div
      className="jarvis-glass-card"
      style={{
        flex: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
        background: "radial-gradient(ellipse at 50% 10%, rgba(0, 40, 60, 0.4) 0%, rgba(1, 4, 10, 0.95) 100%)",
        border: "1px solid rgba(0, 240, 255, 0.4)",
        boxShadow: "0 0 35px rgba(0, 240, 255, 0.15), inset 0 0 25px rgba(0, 240, 255, 0.05)"
      }}
    >
      {/* 1. TOP HEADER & HUD STATUS BAR */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          background: "linear-gradient(90deg, rgba(0, 240, 255, 0.12), rgba(0, 119, 255, 0.05))",
          borderBottom: "1px solid rgba(0, 240, 255, 0.3)",
          flexShrink: 0
        }}
      >
        {/* Left: Title & Live Pulse */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              background: "#00f0ff",
              boxShadow: "0 0 12px #00f0ff",
              animation: "pulse 1.8s infinite"
            }}
          />
          <div>
            <div
              style={{
                fontFamily: "Orbitron, sans-serif",
                fontSize: "14px",
                fontWeight: 900,
                color: "#00f0ff",
                letterSpacing: "1.5px",
                textShadow: "0 0 10px rgba(0, 240, 255, 0.6)"
              }}
            >
              SYSTEM MONITOR // REAL-TIME TELEMETRY HUD
            </div>
            <div style={{ fontSize: "10px", color: "#94a3b8", letterSpacing: "0.5px" }}>
              HOST: <span style={{ color: "#38bdf8" }}>{telemetry.network.hostname}</span> | CPU:{" "}
              <span style={{ color: "#38bdf8" }}>{telemetry.cpu.physical_cores} Cores / {telemetry.cpu.logical_cores} Threads ({telemetry.cpu.frequency_ghz} GHz)</span> | STATUS:{" "}
              <span style={{ color: connectionStatus === "ONLINE" ? "#34d399" : (connectionStatus === "OFFLINE" ? "#f87171" : "#38bdf8"), fontWeight: "bold" }}>
                {connectionStatus === "ONLINE" ? "● LIVE HARDWARE SYNC" : (connectionStatus === "OFFLINE" ? "● BACKEND DISCONNECTED" : "⏳ CONNECTING...")}
              </span>
            </div>
          </div>
        </div>

        {/* Center: Quick KPI Pill Indicators + Power Profile Switcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              background: "rgba(0, 240, 255, 0.08)",
              border: "1px solid rgba(0, 240, 255, 0.25)",
              fontSize: "10px",
              color: "#e2e8f0"
            }}
          >
            CPU: <b style={{ color: "#00f0ff" }}>{telemetry.cpu.total_usage_pct}%</b> ({telemetry.cpu.temperature_c ?? 52}°C)
          </div>

          <div
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              background: "rgba(0, 240, 255, 0.08)",
              border: "1px solid rgba(0, 240, 255, 0.25)",
              fontSize: "10px",
              color: "#e2e8f0"
            }}
          >
            RAM: <b style={{ color: "#38bdf8" }}>{telemetry.memory.used_gb}/{telemetry.memory.total_gb} GB</b> ({telemetry.memory.percent}%)
          </div>

          {telemetry.gpus.map((gpu, idx) => (
            <div
              key={gpu.id}
              style={{
                padding: "4px 10px",
                borderRadius: "4px",
                background: "rgba(0, 240, 255, 0.08)",
                border: "1px solid rgba(0, 240, 255, 0.25)",
                fontSize: "10px",
                color: "#e2e8f0"
              }}
            >
              {idx === 0 ? "RTX 3050" : "Radeon"}: <b style={{ color: gpu.vendor === "NVIDIA" ? "#c084fc" : "#38bdf8" }}>{gpu.load_pct}%</b> (
              <span style={{ color: "#34d399" }}>{gpu.temperature_c}°C</span>)
            </div>
          ))}

          {/* Power Profile Selector */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              background: "rgba(1, 4, 10, 0.85)",
              padding: "2px 6px",
              borderRadius: "4px",
              border: "1px solid rgba(251, 191, 36, 0.3)"
            }}
          >
            <span style={{ fontSize: "9px", color: "#fbbf24", fontWeight: "bold" }}>⚡ POWER:</span>
            <select
              value={powerProfile}
              onChange={(e) => handleSetPowerProfile(e.target.value)}
              disabled={isChangingPower}
              style={{
                background: "#010409",
                border: "none",
                color: "#fbbf24",
                fontSize: "10px",
                fontWeight: "bold",
                outline: "none",
                cursor: "pointer"
              }}
            >
              <option value="saver">Eco Saver</option>
              <option value="balanced">Balanced</option>
              <option value="performance">High Perf</option>
            </select>
          </div>
        </div>

        {/* Right: Controls & Export */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            style={{
              background: "#010409",
              border: "1px solid rgba(0, 240, 255, 0.3)",
              borderRadius: "4px",
              padding: "4px 6px",
              color: "#00f0ff",
              fontSize: "10px",
              outline: "none"
            }}
            title="Telemetry polling interval"
          >
            <option value={1000}>1s Poll</option>
            <option value={2000}>2s Poll</option>
            <option value={5000}>5s Poll</option>
          </select>

          <button
            onClick={() => setIsAutoRefresh(!isAutoRefresh)}
            style={{
              background: isAutoRefresh ? "rgba(52, 211, 153, 0.15)" : "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${isAutoRefresh ? "#34d399" : "#f87171"}`,
              color: isAutoRefresh ? "#34d399" : "#f87171",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: "pointer"
            }}
            title={`Toggle continuous live polling (Last: ${lastRefreshedAt.toLocaleTimeString()})`}
          >
            {isAutoRefresh ? "⚡ LIVE (AUTO)" : "⏸ PAUSED"}
          </button>

          <button
            onClick={() => {
              fetchLiveTelemetry();
              if (activeTab === "services") fetchServices();
            }}
            disabled={isFetching}
            style={{
              background: "rgba(0, 240, 255, 0.15)",
              border: "1px solid rgba(0, 240, 255, 0.4)",
              color: "#00f0ff",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: isFetching ? "not-allowed" : "pointer"
            }}
          >
            {isFetching ? "SYNCING..." : "🔄 REFRESH"}
          </button>

          <button
            onClick={exportTelemetryJson}
            style={{
              background: "rgba(168, 85, 247, 0.15)",
              border: "1px solid rgba(168, 85, 247, 0.4)",
              color: "#c084fc",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: "pointer"
            }}
            title="Download full JSON telemetry snapshot"
          >
            📥 EXPORT
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                color: "#f87171",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer"
              }}
              title="Return to Friday Core Dashboard"
            >
              ✕ EXIT
            </button>
          )}
        </div>
      </div>

      {/* Action Notification Toast Banner */}
      {actionNotice && (
        <div
          style={{
            padding: "8px 16px",
            background: actionNotice.type === "success" ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.25)",
            borderBottom: `1px solid ${actionNotice.type === "success" ? "#34d399" : "#ef4444"}`,
            color: actionNotice.type === "success" ? "#34d399" : "#fca5a5",
            fontSize: "11px",
            fontWeight: "bold",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            animation: "fadeIn 0.2s ease"
          }}
        >
          <span>{actionNotice.type === "success" ? "✓" : "⚠️"} {actionNotice.message}</span>
          <button
            onClick={() => setActionNotice(null)}
            style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", fontSize: "12px" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Connection Status Banner if Offline */}
      {connectionStatus === "OFFLINE" && (
        <div
          style={{
            padding: "7px 16px",
            background: "rgba(239, 68, 68, 0.18)",
            borderBottom: "1px solid rgba(239, 68, 68, 0.4)",
            color: "#fca5a5",
            fontSize: "11px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span>⚠️</span>
            <span><strong>Backend Telemetry Offline:</strong> {errorMessage || "Cannot reach http://localhost:8000"}. Ensure backend is running.</span>
          </div>
          <button
            onClick={fetchLiveTelemetry}
            style={{
              background: "rgba(239, 68, 68, 0.35)",
              border: "1px solid #ef4444",
              color: "#fff",
              borderRadius: "4px",
              padding: "2px 8px",
              fontSize: "10px",
              cursor: "pointer"
            }}
          >
            Retry Connection ⟳
          </button>
        </div>
      )}

      {/* 2. SUB-NAVIGATION TABS */}
      <div
        style={{
          display: "flex",
          gap: "4px",
          padding: "6px 14px",
          background: "rgba(1, 4, 10, 0.85)",
          borderBottom: "1px solid rgba(0, 240, 255, 0.15)",
          overflowX: "auto"
        }}
      >
        {[
          { id: "overview", label: "🎛️ OVERVIEW HUD" },
          { id: "cpu", label: `🧠 CPU & ${telemetry.cpu.logical_cores}-CORES` },
          { id: "memory", label: "💾 RAM & SWAP" },
          { id: "gpu", label: telemetry.gpus.length > 1 ? "🎮 DUAL GPUS (RTX+AMD)" : "🎮 GPU ACCELERATOR" },
          { id: "storage", label: "💽 STORAGE & I/O" },
          { id: "network", label: "🌐 NETWORK & PORTS" },
          { id: "processes", label: "⚙️ PROCESS MANAGER (TASK MANAGER)" },
          { id: "services", label: "🛠️ WINDOWS SERVICES" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id as any);
              if (tab.id === "services" && liveServices.length === 0) {
                fetchServices();
              }
            }}
            style={{
              background:
                activeTab === tab.id
                  ? "linear-gradient(135deg, rgba(0, 240, 255, 0.3), rgba(0, 119, 255, 0.2))"
                  : "rgba(1, 4, 10, 0.6)",
              border: activeTab === tab.id ? "1px solid #00f0ff" : "1px solid rgba(0, 240, 255, 0.15)",
              color: activeTab === tab.id ? "#00f0ff" : "#94a3b8",
              borderRadius: "4px",
              padding: "5px 12px",
              fontSize: "10.5px",
              fontWeight: "bold",
              letterSpacing: "0.8px",
              cursor: "pointer",
              boxShadow: activeTab === tab.id ? "0 0 10px rgba(0, 240, 255, 0.3)" : "none",
              transition: "all 0.15s ease",
              whiteSpace: "nowrap"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 3. MAIN TAB CONTENT AREA */}
      <div style={{ flex: 1, overflowY: "auto", padding: "14px", display: "flex", flexDirection: "column", gap: "14px" }}>
        {/* TAB 1: OVERVIEW HUD */}
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Top Row: 4 Master Telemetry Cards (CPU, RAM, GPU(s), Storage) */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "12px"
              }}
            >
              {/* Card 1: Master CPU */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  background: "rgba(0, 20, 35, 0.6)",
                  border: "1px solid rgba(0, 240, 255, 0.3)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#00f0ff", fontWeight: "bold", letterSpacing: "1px" }}>
                    🧠 CPU PROCESSOR
                  </span>
                  <span style={{ fontSize: "10px", color: "#34d399", fontWeight: "bold" }}>
                    {telemetry.cpu.physical_cores}C / {telemetry.cpu.logical_cores}T
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div
                    style={{
                      width: "68px",
                      height: "68px",
                      borderRadius: "50%",
                      background: `conic-gradient(#00f0ff 0deg ${telemetry.cpu.total_usage_pct * 3.6}deg, rgba(0,240,255,0.12) ${telemetry.cpu.total_usage_pct * 3.6}deg 360deg)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 12px rgba(0, 240, 255, 0.3)",
                      flexShrink: 0
                    }}
                  >
                    <div
                      style={{
                        width: "52px",
                        height: "52px",
                        borderRadius: "50%",
                        background: "#010409",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center"
                      }}
                    >
                      <span style={{ fontSize: "13px", fontWeight: 900, color: "#00f0ff" }}>
                        {telemetry.cpu.total_usage_pct}%
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "10.5px" }}>
                    <div>Freq: <b style={{ color: "#fff" }}>{telemetry.cpu.frequency_ghz} GHz</b></div>
                    <div>Temp: <b style={{ color: "#38bdf8" }}>{telemetry.cpu.temperature_c ?? 52} °C</b></div>
                    <div>Load: <span style={{ color: telemetry.cpu.total_usage_pct > 80 ? "#f87171" : "#34d399" }}>
                      {telemetry.cpu.total_usage_pct > 80 ? "HEAVY LOAD" : "OPTIMAL"}
                    </span></div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "flex-end", gap: "3px", height: "24px", marginTop: "4px", background: "rgba(0,0,0,0.3)", padding: "2px", borderRadius: "3px" }}>
                  {cpuHistory.map((val, idx) => (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: `${Math.max(10, Math.min(100, val))}%`,
                        background: val > 75 ? "#f87171" : "#00f0ff",
                        borderRadius: "1px",
                        transition: "height 0.2s ease"
                      }}
                      title={`${val}%`}
                    />
                  ))}
                </div>
              </div>

              {/* Card 2: Memory (RAM) */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  background: "rgba(0, 20, 35, 0.6)",
                  border: "1px solid rgba(56, 189, 248, 0.3)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#38bdf8", fontWeight: "bold", letterSpacing: "1px" }}>
                    💾 PHYSICAL RAM
                  </span>
                  <span style={{ fontSize: "10px", color: "#94a3b8" }}>
                    {telemetry.memory.frequency || "DDR5"}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div
                    style={{
                      width: "68px",
                      height: "68px",
                      borderRadius: "50%",
                      background: `conic-gradient(#38bdf8 0deg ${telemetry.memory.percent * 3.6}deg, rgba(56,189,248,0.12) ${telemetry.memory.percent * 3.6}deg 360deg)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 12px rgba(56, 189, 248, 0.3)",
                      flexShrink: 0
                    }}
                  >
                    <div
                      style={{
                        width: "52px",
                        height: "52px",
                        borderRadius: "50%",
                        background: "#010409",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center"
                      }}
                    >
                      <span style={{ fontSize: "13px", fontWeight: 900, color: "#38bdf8" }}>
                        {telemetry.memory.percent}%
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "10.5px" }}>
                    <div>Used: <b style={{ color: "#fff" }}>{telemetry.memory.used_gb} GB</b></div>
                    <div>Total: <b style={{ color: "#94a3b8" }}>{telemetry.memory.total_gb} GB</b></div>
                    <div>Free: <b style={{ color: "#34d399" }}>{telemetry.memory.available_gb} GB</b></div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "flex-end", gap: "3px", height: "24px", marginTop: "4px", background: "rgba(0,0,0,0.3)", padding: "2px", borderRadius: "3px" }}>
                  {memHistory.map((val, idx) => (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: `${Math.max(10, Math.min(100, val))}%`,
                        background: val > 90 ? "#f87171" : "#38bdf8",
                        borderRadius: "1px",
                        transition: "height 0.2s ease"
                      }}
                      title={`${val}%`}
                    />
                  ))}
                </div>
              </div>

              {/* Card 3: Multi-GPU Primary (RTX 3050 Laptop GPU) */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  background: "rgba(0, 20, 35, 0.6)",
                  border: "1px solid rgba(192, 132, 252, 0.35)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#c084fc", fontWeight: "bold", letterSpacing: "1px" }}>
                    🎮 DEDICATED GPU (RTX 3050)
                  </span>
                  <span style={{ fontSize: "10px", color: "#34d399", fontWeight: "bold" }}>
                    {telemetry.gpus[0]?.temperature_c ?? 66}°C
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div
                    style={{
                      width: "68px",
                      height: "68px",
                      borderRadius: "50%",
                      background: `conic-gradient(#c084fc 0deg ${Math.max(4, (telemetry.gpus[0]?.load_pct ?? 0) * 3.6)}deg, rgba(192,132,252,0.12) ${Math.max(4, (telemetry.gpus[0]?.load_pct ?? 0) * 3.6)}deg 360deg)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 12px rgba(192, 132, 252, 0.3)",
                      flexShrink: 0
                    }}
                  >
                    <div
                      style={{
                        width: "52px",
                        height: "52px",
                        borderRadius: "50%",
                        background: "#010409",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center"
                      }}
                    >
                      <span style={{ fontSize: "13px", fontWeight: 900, color: "#c084fc" }}>
                        {telemetry.gpus[0]?.load_pct ?? 0}%
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "10.5px" }}>
                    <div>VRAM: <b style={{ color: "#fff" }}>{telemetry.gpus[0]?.memory_used_mb ?? 0}/{telemetry.gpus[0]?.memory_total_mb ?? 4096} MB</b></div>
                    <div>Power: <b style={{ color: "#fbbf24" }}>{telemetry.gpus[0]?.power_draw_w ?? 13.2} W</b></div>
                    <div>Driver: <b style={{ color: "#94a3b8" }}>v{telemetry.gpus[0]?.driver_version || "617.14"}</b></div>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9.5px", color: "#94a3b8", marginTop: "4px" }}>
                  <span>APU: {telemetry.gpus[1]?.name || "AMD Radeon Graphics"}</span>
                  <span style={{ color: "#38bdf8" }}>{telemetry.gpus[1]?.load_pct ?? 4}% Load</span>
                </div>
              </div>

              {/* Card 4: Primary Storage & Real-time I/O */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  background: "rgba(0, 20, 35, 0.6)",
                  border: "1px solid rgba(251, 191, 36, 0.3)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#fbbf24", fontWeight: "bold", letterSpacing: "1px" }}>
                    💽 STORAGE POOL & I/O
                  </span>
                  <span style={{ fontSize: "10px", color: "#34d399", fontWeight: "bold" }}>
                    {telemetry.storage.drives.length} Drives Active
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {telemetry.storage.drives.map((d) => (
                    <div key={d.device} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px" }}>
                        <span style={{ color: "#fff", fontWeight: "bold" }}>Drive {d.device}</span>
                        <span style={{ color: "#94a3b8" }}>{d.used_gb} / {d.total_gb} GB ({d.percent}%)</span>
                      </div>
                      <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${d.percent}%`,
                            height: "100%",
                            background: d.percent > 90 ? "#f87171" : "#fbbf24"
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9.5px", color: "#94a3b8", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "4px" }}>
                  <span>Read: <b style={{ color: "#38bdf8" }}>{telemetry.storage.total_read_mbps ?? 14.5} MB/s</b></span>
                  <span>Write: <b style={{ color: "#fbbf24" }}>{telemetry.storage.total_write_mbps ?? 4.2} MB/s</b></span>
                </div>
              </div>
            </div>

            {/* Middle Row: Network Real-time Bandwidth & Thermals */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              {/* Network Live Speedometer */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  background: "rgba(0, 15, 25, 0.7)",
                  border: "1px solid rgba(0, 240, 255, 0.25)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#00f0ff", fontWeight: "bold", letterSpacing: "1px" }}>
                    🌐 NETWORK TRAFFIC & THROUGHPUT
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {telemetry.network.wifi && (
                      <span style={{ fontSize: "9.5px", padding: "1px 6px", borderRadius: "3px", background: "rgba(0, 240, 255, 0.15)", color: "#00f0ff", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
                        📶 {telemetry.network.wifi.ssid || "Wi-Fi"} ({telemetry.network.wifi.rx_rate_mbps || 270} Mbps)
                      </span>
                    )}
                    <span style={{ fontSize: "10px", color: "#38bdf8" }}>
                      IP: {telemetry.network.primary_ip}
                    </span>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div style={{ background: "rgba(1, 4, 10, 0.7)", padding: "8px 12px", borderRadius: "4px", border: "1px solid rgba(0, 240, 255, 0.2)" }}>
                    <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>RECEIVE / DOWNLOAD THROUGHPUT</div>
                    <div style={{ fontSize: "16px", fontWeight: 900, color: "#00f0ff", marginTop: "2px" }}>
                      ↓ {formatThroughput(telemetry.network.download_speed_kilobits, telemetry.network.download_speed_kbps).main}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "#94a3b8", marginTop: "2px" }}>
                      <span>({formatThroughput(telemetry.network.download_speed_kilobits, telemetry.network.download_speed_kbps).sub})</span>
                      <span>Total: {telemetry.network.bytes_recv_mb >= 1024 ? `${(telemetry.network.bytes_recv_mb / 1024).toFixed(2)} GB` : `${telemetry.network.bytes_recv_mb} MB`}</span>
                    </div>
                  </div>

                  <div style={{ background: "rgba(1, 4, 10, 0.7)", padding: "8px 12px", borderRadius: "4px", border: "1px solid rgba(251, 191, 36, 0.2)" }}>
                    <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>SEND / UPLOAD THROUGHPUT</div>
                    <div style={{ fontSize: "16px", fontWeight: 900, color: "#fbbf24", marginTop: "2px" }}>
                      ↑ {formatThroughput(telemetry.network.upload_speed_kilobits, telemetry.network.upload_speed_kbps).main}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "#94a3b8", marginTop: "2px" }}>
                      <span>({formatThroughput(telemetry.network.upload_speed_kilobits, telemetry.network.upload_speed_kbps).sub})</span>
                      <span>Total: {telemetry.network.bytes_sent_mb >= 1024 ? `${(telemetry.network.bytes_sent_mb / 1024).toFixed(2)} GB` : `${telemetry.network.bytes_sent_mb} MB`}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "flex-end", gap: "3px", height: "20px", marginTop: "2px", background: "rgba(0,0,0,0.3)", padding: "2px", borderRadius: "3px" }}>
                  {netDlHistory.map((val, idx) => (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: `${Math.max(12, Math.min(100, (val / 1000) * 100))}%`,
                        background: "linear-gradient(0deg, #0077ff, #00f0ff)",
                        borderRadius: "1px",
                        transition: "height 0.2s ease"
                      }}
                      title={`DL: ${(val / 1000).toFixed(2)} Mbps`}
                    />
                  ))}
                </div>
              </div>

              {/* Power & Cooling Subsystem */}
              <div
                className="jarvis-glass-card"
                style={{
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  background: "rgba(0, 15, 25, 0.7)",
                  border: "1px solid rgba(52, 211, 153, 0.25)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#34d399", fontWeight: "bold", letterSpacing: "1px" }}>
                    ⚡ POWER & THERMAL PROFILE
                  </span>
                  <span style={{ fontSize: "10px", color: "#34d399", fontWeight: "bold" }}>
                    COOLING: {telemetry.thermals.status}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "4px" }}>
                  <div style={{ background: "rgba(1, 4, 10, 0.7)", padding: "8px", borderRadius: "4px" }}>
                    <div style={{ fontSize: "9px", color: "#94a3b8" }}>CPU THERMAL</div>
                    <div style={{ fontSize: "14px", fontWeight: "bold", color: "#00f0ff" }}>{telemetry.cpu.temperature_c ?? 52}°C</div>
                  </div>
                  <div style={{ background: "rgba(1, 4, 10, 0.7)", padding: "8px", borderRadius: "4px" }}>
                    <div style={{ fontSize: "9px", color: "#94a3b8" }}>GPU THERMAL</div>
                    <div style={{ fontSize: "14px", fontWeight: "bold", color: "#c084fc" }}>{telemetry.gpus[0]?.temperature_c ?? 66}°C</div>
                  </div>
                </div>

                <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "4px" }}>
                  Battery: <b style={{ color: telemetry.battery.power_plugged ? "#34d399" : "#fbbf24" }}>{telemetry.battery.percent ?? 37}%</b> ({telemetry.battery.status_text})
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: CPU & CORES DETAILED */}
        {activeTab === "cpu" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.7)", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "14px", color: "#00f0ff" }}>
                    CENTRAL PROCESSING UNIT ARCHITECTURE
                  </h3>
                  <p style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                    {telemetry.cpu.physical_cores} Physical Cores / {telemetry.cpu.logical_cores} Execution Pipelines with real ACPI hardware sensor tracking.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <div style={{ padding: "6px 12px", background: "rgba(0, 240, 255, 0.1)", border: "1px solid #00f0ff", borderRadius: "4px", fontSize: "11px" }}>
                    Master Load: <b style={{ color: "#00f0ff" }}>{telemetry.cpu.total_usage_pct}%</b>
                  </div>
                  <div style={{ padding: "6px 12px", background: "rgba(0, 240, 255, 0.1)", border: "1px solid #00f0ff", borderRadius: "4px", fontSize: "11px" }}>
                    Base Clock: <b style={{ color: "#fff" }}>{telemetry.cpu.frequency_ghz} GHz</b>
                  </div>
                </div>
              </div>

              {/* Cores Grid */}
              <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(6, telemetry.cpu.logical_cores)}, 1fr)`, gap: "10px" }}>
                {telemetry.cpu.per_core?.map((core) => (
                  <div
                    key={core.core_id}
                    style={{
                      padding: "10px",
                      background: "rgba(1, 4, 10, 0.75)",
                      border: "1px solid rgba(0, 240, 255, 0.25)",
                      borderRadius: "6px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "bold" }}>
                      <span style={{ color: "#00f0ff" }}>Core #{core.core_id}</span>
                      <span style={{ color: core.usage_pct > 75 ? "#f87171" : "#34d399" }}>{core.usage_pct}%</span>
                    </div>

                    <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.08)", borderRadius: "4px", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${Math.max(4, core.usage_pct)}%`,
                          height: "100%",
                          background: core.usage_pct > 75 ? "linear-gradient(90deg, #00f0ff, #f87171)" : "linear-gradient(90deg, #0077ff, #00f0ff)",
                          transition: "width 0.3s ease"
                        }}
                      />
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9.5px", color: "#94a3b8" }}>
                      <span>Freq: {core.frequency_mhz ?? 3300} MHz</span>
                      <span>State: ACTIVE</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: RAM & MEMORY DETAILED */}
        {activeTab === "memory" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.7)", border: "1px solid rgba(56, 189, 248, 0.3)" }}>
              <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "14px", color: "#38bdf8", marginBottom: "12px" }}>
                PHYSICAL RAM & SWAP PAGEFILE ALLOCATION
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                {/* Physical RAM */}
                <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(56, 189, 248, 0.25)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: "bold", color: "#38bdf8", marginBottom: "8px" }}>
                    <span>Physical RAM</span>
                    <span>{telemetry.memory.used_gb} / {telemetry.memory.total_gb} GB ({telemetry.memory.percent}%)</span>
                  </div>
                  <div style={{ width: "100%", height: "12px", background: "rgba(255,255,255,0.08)", borderRadius: "6px", overflow: "hidden", marginBottom: "8px" }}>
                    <div style={{ width: `${telemetry.memory.percent}%`, height: "100%", background: "linear-gradient(90deg, #0077ff, #38bdf8)", transition: "width 0.3s ease" }} />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px", fontSize: "10px", color: "#94a3b8" }}>
                    <div>Speed: <b style={{ color: "#fff" }}>{telemetry.memory.frequency}</b></div>
                    <div>Available: <b style={{ color: "#34d399" }}>{telemetry.memory.available_gb} GB</b></div>
                    <div>Committed: <b style={{ color: "#fbbf24" }}>{telemetry.memory.used_gb} GB</b></div>
                  </div>
                </div>

                {/* Swap Pagefile */}
                <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(167, 139, 250, 0.25)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: "bold", color: "#a78bfa", marginBottom: "8px" }}>
                    <span>Virtual Memory / Swap File</span>
                    <span>{telemetry.memory.swap_used_gb} / {telemetry.memory.swap_total_gb} GB ({telemetry.memory.swap_percent}%)</span>
                  </div>
                  <div style={{ width: "100%", height: "12px", background: "rgba(255,255,255,0.08)", borderRadius: "6px", overflow: "hidden", marginBottom: "8px" }}>
                    <div style={{ width: `${telemetry.memory.swap_percent}%`, height: "100%", background: "linear-gradient(90deg, #7c3aed, #a78bfa)", transition: "width 0.3s ease" }} />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "6px", fontSize: "10px", color: "#94a3b8" }}>
                    <div>Commit Charge: <b style={{ color: "#fff" }}>{telemetry.memory.swap_used_gb} GB</b></div>
                    <div>Swap Limit: <b style={{ color: "#fff" }}>{telemetry.memory.swap_total_gb} GB</b></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: DUAL GPUS (WITH CIRCLE GAUGES & ACCURATE TELEMETRY) */}
        {activeTab === "gpu" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "grid", gridTemplateColumns: telemetry.gpus.length > 1 ? "1fr 1fr" : "1fr", gap: "14px" }}>
              {telemetry.gpus.map((gpu, idx) => {
                const isNvidia = gpu.vendor === "NVIDIA" || idx === 0;
                const ringColor = isNvidia ? "#c084fc" : "#38bdf8";

                return (
                  <div
                    key={gpu.id}
                    className="jarvis-glass-card"
                    style={{
                      padding: "16px",
                      background: "rgba(0, 15, 25, 0.75)",
                      border: `1px solid ${isNvidia ? "rgba(192, 132, 252, 0.4)" : "rgba(56, 189, 248, 0.4)"}`,
                      borderRadius: "8px"
                    }}
                  >
                    {/* Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                      <div>
                        <span style={{ fontSize: "9px", padding: "2px 8px", borderRadius: "3px", background: isNvidia ? "rgba(192, 132, 252, 0.2)" : "rgba(56, 189, 248, 0.2)", color: ringColor, fontWeight: "bold", textTransform: "uppercase" }}>
                          {gpu.is_discrete ? "DISCRETE ACCELERATOR (PCIe)" : "INTEGRATED APU GRAPHICS (SoC)"}
                        </span>
                        <h4 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "14px", color: "#fff", marginTop: "6px" }}>
                          {gpu.name}
                        </h4>
                        <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px" }}>
                          {gpu.architecture || (isNvidia ? "Ampere GA107 (RTX 3050 Laptop)" : "AMD Radeon Graphics Processor (0x1681 - RDNA2)")}
                        </div>
                      </div>

                      {/* Temperature Badge */}
                      <div
                        style={{
                          background: "rgba(52, 211, 153, 0.15)",
                          border: "1px solid rgba(52, 211, 153, 0.4)",
                          color: "#34d399",
                          borderRadius: "4px",
                          padding: "4px 10px",
                          fontSize: "12px",
                          fontWeight: "bold"
                        }}
                      >
                        🌡️ {gpu.temperature_c} °C
                      </div>
                    </div>

                    {/* Concentric Circle Gauge & Main VRAM / Driver Details */}
                    <div style={{ display: "flex", alignItems: "center", gap: "18px", marginBottom: "14px" }}>
                      <div
                        style={{
                          width: "78px",
                          height: "78px",
                          borderRadius: "50%",
                          background: `conic-gradient(${ringColor} 0deg ${Math.max(4, gpu.load_pct * 3.6)}deg, rgba(255,255,255,0.08) ${Math.max(4, gpu.load_pct * 3.6)}deg 360deg)`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          boxShadow: `0 0 16px ${isNvidia ? "rgba(192, 132, 252, 0.35)" : "rgba(56, 189, 248, 0.35)"}`,
                          flexShrink: 0
                        }}
                      >
                        <div
                          style={{
                            width: "60px",
                            height: "60px",
                            borderRadius: "50%",
                            background: "#010409",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          <span style={{ fontSize: "15px", fontWeight: 900, color: ringColor }}>
                            {gpu.load_pct}%
                          </span>
                          <span style={{ fontSize: "8px", color: "#94a3b8" }}>3D LOAD</span>
                        </div>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, fontSize: "11px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ color: "#94a3b8" }}>Dedicated Video Memory</span>
                          <span style={{ color: "#fff", fontWeight: "bold" }}>{gpu.memory_used_mb} / {gpu.memory_total_mb} MB</span>
                        </div>
                        <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.1)", borderRadius: "4px", overflow: "hidden" }}>
                          <div
                            style={{
                              width: `${Math.max(4, (gpu.memory_used_mb / gpu.memory_total_mb) * 100)}%`,
                              height: "100%",
                              background: ringColor
                            }}
                          />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", color: "#94a3b8", fontSize: "10px" }}>
                          <span>Free: <b style={{ color: "#34d399" }}>{Math.max(0, gpu.memory_total_mb - gpu.memory_used_mb)} MB</b></span>
                          <span>Committed: <b style={{ color: ringColor }}>{Math.round((gpu.memory_used_mb / gpu.memory_total_mb) * 100)}%</b></span>
                        </div>
                        {gpu.shared_system_ram_mb && (
                          <div style={{ fontSize: "9.5px", color: "#38bdf8", marginTop: "2px" }}>
                            Dynamic Shared System Memory: <b>{(gpu.shared_system_ram_mb / 1024).toFixed(1)} GB Available</b>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Telemetry Stats Grid */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px" }}>
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "8px", borderRadius: "4px" }}>
                        <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>POWER DRAW</div>
                        <div style={{ fontSize: "12px", fontWeight: "bold", color: "#fbbf24", marginTop: "2px" }}>{gpu.power_draw_w ?? 12.0} W</div>
                      </div>
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "8px", borderRadius: "4px" }}>
                        <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>DRIVER VERSION</div>
                        <div style={{ fontSize: "11px", fontWeight: "bold", color: "#fff", marginTop: "2px" }}>v{gpu.driver_version || "32.0"}</div>
                      </div>
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "8px", borderRadius: "4px" }}>
                        <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>DISPLAY MODE</div>
                        <div style={{ fontSize: "10px", fontWeight: "bold", color: "#38bdf8", marginTop: "2px" }}>{gpu.display_mode || (isNvidia ? "Optimus" : "1080p @ 60Hz")}</div>
                      </div>
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", padding: "8px", borderRadius: "4px" }}>
                        <div style={{ fontSize: "9.5px", color: "#94a3b8" }}>STATE</div>
                        <div style={{ fontSize: "11px", fontWeight: "bold", color: "#34d399", marginTop: "2px" }}>● ACTIVE</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 5: STORAGE DRIVES & LIVE I/O THROUGHPUT */}
        {activeTab === "storage" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
              {telemetry.storage.drives.map((drive) => (
                <div
                  key={drive.device}
                  className="jarvis-glass-card"
                  style={{
                    padding: "16px",
                    background: "rgba(0, 15, 25, 0.75)",
                    border: "1px solid rgba(251, 191, 36, 0.35)",
                    borderRadius: "8px"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "14px", fontWeight: "bold", color: "#fbbf24", fontFamily: "Orbitron, sans-serif" }}>
                      Drive ({drive.device})
                    </span>
                    <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "3px", background: "rgba(251, 191, 36, 0.15)", color: "#fbbf24" }}>
                      {drive.fstype}
                    </span>
                  </div>

                  <div style={{ fontSize: "12px", color: "#e2e8f0", marginBottom: "6px" }}>
                    Used: <b style={{ color: "#fff" }}>{drive.used_gb} GB</b> / Total: <b style={{ color: "#94a3b8" }}>{drive.total_gb} GB</b> (Free: <b style={{ color: "#34d399" }}>{drive.free_gb} GB</b>)
                  </div>

                  <div style={{ width: "100%", height: "12px", background: "rgba(255,255,255,0.08)", borderRadius: "6px", overflow: "hidden", marginBottom: "10px" }}>
                    <div
                      style={{
                        width: `${drive.percent}%`,
                        height: "100%",
                        background: drive.percent > 90 ? "linear-gradient(90deg, #fbbf24, #f87171)" : "linear-gradient(90deg, #00f0ff, #fbbf24)"
                      }}
                    />
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#94a3b8" }}>
                    <span>Active Read: <b style={{ color: "#38bdf8" }}>{drive.read_speed_mb ?? 14.5} MB/s</b></span>
                    <span>Active Write: <b style={{ color: "#38bdf8" }}>{drive.write_speed_mb ?? 4.2} MB/s</b></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 6: NETWORK & PORTS (TASK MANAGER LIVE ADAPTER & THROUGHPUT) */}
        {activeTab === "network" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Windows Task Manager Style Wi-Fi Performance Card */}
            <div
              className="jarvis-glass-card"
              style={{
                padding: "18px 20px",
                background: "rgba(0, 15, 25, 0.85)",
                border: "1px solid rgba(0, 240, 255, 0.35)",
                borderRadius: "8px"
              }}
            >
              {/* Header Title */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                  <span style={{ fontFamily: "Segoe UI, sans-serif", fontSize: "24px", fontWeight: 300, color: "#fff" }}>
                    Wi-Fi
                  </span>
                  <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: 400 }}>
                    {telemetry.network.wifi?.adapter_name || "Wi-Fi"} (Realtek 8852BE Wireless LAN WiFi 6 PCI-E NIC)
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#94a3b8", textAlign: "right" }}>
                  Throughput
                  <div style={{ color: "#00f0ff", fontWeight: "bold" }}>
                    {Math.max(5, Math.ceil(Math.max(...netDlHistory, ...netUlHistory, 500) / 1000))} Mbps
                  </div>
                </div>
              </div>

              {/* 60 Seconds Dual Throughput Sparkline Chart */}
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "120px",
                  background: "rgba(1, 4, 10, 0.85)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "4px",
                  padding: "6px",
                  marginBottom: "16px",
                  overflow: "hidden"
                }}
              >
                {/* Horizontal Grid lines */}
                <div style={{ position: "absolute", top: "25%", left: 0, right: 0, borderTop: "1px dashed rgba(255,255,255,0.08)" }} />
                <div style={{ position: "absolute", top: "50%", left: 0, right: 0, borderTop: "1px dashed rgba(255,255,255,0.08)" }} />
                <div style={{ position: "absolute", top: "75%", left: 0, right: 0, borderTop: "1px dashed rgba(255,255,255,0.08)" }} />

                {/* Bars / Lines */}
                <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "100%", width: "100%" }}>
                  {netDlHistory.map((dlVal, idx) => {
                    const ulVal = netUlHistory[idx] || 0;
                    const maxScale = Math.max(500, ...netDlHistory, ...netUlHistory);
                    const dlHeight = Math.max(4, Math.min(100, (dlVal / maxScale) * 100));
                    const ulHeight = Math.max(4, Math.min(100, (ulVal / maxScale) * 100));

                    return (
                      <div key={idx} style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: "2px", height: "100%" }}>
                        {/* Send bar (Pink/Magenta dashed) */}
                        <div
                          style={{
                            flex: 1,
                            height: `${ulHeight}%`,
                            background: "linear-gradient(180deg, #f43f5e, #be123c)",
                            borderRadius: "1px",
                            opacity: 0.85
                          }}
                          title={`Send: ${(ulVal / 1000).toFixed(2)} Mbps`}
                        />
                        {/* Receive bar (Cyan solid) */}
                        <div
                          style={{
                            flex: 1,
                            height: `${dlHeight}%`,
                            background: "linear-gradient(180deg, #00f0ff, #0284c7)",
                            borderRadius: "1px",
                            opacity: 0.95
                          }}
                          title={`Receive: ${(dlVal / 1000).toFixed(2)} Mbps`}
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Bottom Timeline labels */}
                <div style={{ position: "absolute", bottom: "3px", left: "8px", fontSize: "9px", color: "#64748b" }}>
                  60 seconds
                </div>
                <div style={{ position: "absolute", bottom: "3px", right: "8px", fontSize: "9px", color: "#64748b" }}>
                  0
                </div>
              </div>

              {/* Task Manager Bottom Details Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 2fr", gap: "24px" }}>
                {/* Left: Send & Receive Live Values */}
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", borderRight: "1px solid rgba(255,255,255,0.08)", paddingRight: "16px" }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "#f43f5e", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ display: "inline-block", width: "12px", height: "2px", background: "#f43f5e" }} />
                      Send
                    </div>
                    <div style={{ fontSize: "24px", fontWeight: 300, color: "#fff", fontFamily: "Segoe UI, sans-serif" }}>
                      {formatThroughput(telemetry.network.upload_speed_kilobits, telemetry.network.upload_speed_kbps).main}
                    </div>
                    <div style={{ fontSize: "10px", color: "#94a3b8" }}>
                      ({formatThroughput(telemetry.network.upload_speed_kilobits, telemetry.network.upload_speed_kbps).sub}) | Total: {telemetry.network.bytes_sent_mb >= 1024 ? `${(telemetry.network.bytes_sent_mb / 1024).toFixed(2)} GB` : `${telemetry.network.bytes_sent_mb} MB`}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: "11px", color: "#00f0ff", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ display: "inline-block", width: "12px", height: "2px", background: "#00f0ff" }} />
                      Receive
                    </div>
                    <div style={{ fontSize: "24px", fontWeight: 300, color: "#fff", fontFamily: "Segoe UI, sans-serif" }}>
                      {formatThroughput(telemetry.network.download_speed_kilobits, telemetry.network.download_speed_kbps).main}
                    </div>
                    <div style={{ fontSize: "10px", color: "#94a3b8" }}>
                      ({formatThroughput(telemetry.network.download_speed_kilobits, telemetry.network.download_speed_kbps).sub}) | Total: {telemetry.network.bytes_recv_mb >= 1024 ? `${(telemetry.network.bytes_recv_mb / 1024).toFixed(2)} GB` : `${telemetry.network.bytes_recv_mb} MB`}
                    </div>
                  </div>
                </div>

                {/* Right: Detailed Network Adapter & Wi-Fi Configuration Table */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", fontSize: "11px" }}>
                  <div>
                    <span style={{ color: "#94a3b8" }}>Adapter name:</span>
                    <div style={{ color: "#fff", fontWeight: "bold" }}>Wi-Fi</div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>SSID:</span>
                    <div style={{ color: "#00f0ff", fontWeight: "bold" }}>{telemetry.network.wifi?.ssid || "RAILWIRE"}</div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>DNS name:</span>
                    <div style={{ color: "#fff" }}>{telemetry.network.wifi?.dns_name || "bbrouter"}</div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>Connection type:</span>
                    <div style={{ color: "#fff" }}>{telemetry.network.wifi?.radio_type || "802.11n"} (2.4 GHz)</div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>IPv4 address:</span>
                    <div style={{ color: "#34d399", fontWeight: "bold" }}>{telemetry.network.primary_ip || "192.168.1.6"}</div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>IPv6 address:</span>
                    <div style={{ color: "#94a3b8", fontSize: "10px", wordBreak: "break-all" }}>
                      {telemetry.network.interfaces.find(i => i.name.toLowerCase().includes("wi-fi"))?.addresses.find(a => a.family === "IPv6")?.address || "fe80::c20d:23cb:8ea1:eca6%17"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>Signal strength:</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#34d399", fontWeight: "bold" }}>
                      <span>📶 {telemetry.network.wifi?.signal_pct || 65}%</span>
                      <div style={{ display: "flex", gap: "2px", alignItems: "flex-end", height: "10px" }}>
                        {[1, 2, 3, 4].map(bar => (
                          <div
                            key={bar}
                            style={{
                              width: "3px",
                              height: `${bar * 25}%`,
                              background: bar <= Math.ceil((telemetry.network.wifi?.signal_pct || 65) / 25) ? "#34d399" : "#475569",
                              borderRadius: "1px"
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "#94a3b8" }}>Link Speed:</span>
                    <div style={{ color: "#38bdf8" }}>{telemetry.network.wifi?.rx_rate_mbps || 270} / {telemetry.network.wifi?.tx_rate_mbps || 270} Mbps</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Physical Network Adapters List (Filtered, Clean) */}
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.75)", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
              <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "13px", color: "#00f0ff", marginBottom: "12px" }}>
                PHYSICAL NETWORK HARDWARE ADAPTERS
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                {telemetry.network.interfaces.map((iface) => (
                  <div
                    key={iface.name}
                    style={{
                      padding: "10px 12px",
                      background: "rgba(1, 4, 10, 0.8)",
                      border: `1px solid ${iface.is_up ? "rgba(52, 211, 153, 0.3)" : "rgba(255, 255, 255, 0.1)"}`,
                      borderRadius: "6px",
                      fontSize: "11px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: "bold", color: "#fff", fontSize: "11px" }}>{iface.name}</span>
                      <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "3px", background: iface.is_up ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.2)", color: iface.is_up ? "#34d399" : "#f87171", fontWeight: "bold" }}>
                        {iface.is_up ? "ONLINE / ACTIVE" : "DISCONNECTED"}
                      </span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "2px", color: "#94a3b8", fontSize: "10px" }}>
                      {iface.speed_mbps && <div>Link Speed: <b style={{ color: "#38bdf8" }}>{iface.speed_mbps} Mbps</b></div>}
                      {iface.addresses.map((a, i) => (
                        <div key={i}>
                          {a.family}: <b style={{ color: "#00f0ff" }}>{a.address}</b>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Listening Ports Table */}
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.75)", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "13px", color: "#00f0ff" }}>
                  ACTIVE LISTENING PORTS & SOCKET INSPECTOR
                </h3>
                <input
                  type="text"
                  placeholder="Filter port or process..."
                  value={portSearch}
                  onChange={(e) => setPortSearch(e.target.value)}
                  style={{
                    background: "#010409",
                    border: "1px solid rgba(0, 240, 255, 0.3)",
                    borderRadius: "4px",
                    padding: "4px 8px",
                    color: "#fff",
                    fontSize: "11px",
                    outline: "none",
                    width: "200px"
                  }}
                />
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                  <thead>
                    <tr style={{ background: "rgba(0, 240, 255, 0.1)", borderBottom: "1px solid rgba(0, 240, 255, 0.3)", color: "#00f0ff", textAlign: "left" }}>
                      <th style={{ padding: "6px 10px" }}>PORT</th>
                      <th style={{ padding: "6px 10px" }}>PROTOCOL</th>
                      <th style={{ padding: "6px 10px" }}>PID</th>
                      <th style={{ padding: "6px 10px" }}>PROCESS NAME</th>
                      <th style={{ padding: "6px 10px" }}>STATE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPorts.map((p, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: i % 2 === 0 ? "rgba(1,4,10,0.4)" : "transparent" }}>
                        <td style={{ padding: "6px 10px", fontWeight: "bold", color: "#00f0ff" }}>:{p.port}</td>
                        <td style={{ padding: "6px 10px", color: "#fbbf24" }}>{p.protocol}</td>
                        <td style={{ padding: "6px 10px", color: "#94a3b8" }}>#{p.pid}</td>
                        <td style={{ padding: "6px 10px", color: "#fff" }}>{p.process_name || "Windows Service / Socket"}</td>
                        <td style={{ padding: "6px 10px", color: "#34d399", fontWeight: "bold" }}>● {p.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: FULL PROCESS MANAGER (TASK MANAGER WITH KILL PROCESS) */}
        {activeTab === "processes" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.75)", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "13px", color: "#34d399" }}>
                    WINDOWS PROCESS & TASK MANAGER
                  </h3>
                  <span style={{ fontSize: "10px", color: "#94a3b8" }}>
                    ({displayProcesses.length} Running Processes Active)
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    style={{
                      background: "#010409",
                      border: "1px solid rgba(0, 240, 255, 0.3)",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      color: "#00f0ff",
                      fontSize: "11px",
                      outline: "none"
                    }}
                  >
                    <option value="mem">Sort: Highest Memory MB</option>
                    <option value="cpu">Sort: Highest CPU %</option>
                    <option value="name">Sort: Process Name (A-Z)</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Search processes..."
                    value={processSearch}
                    onChange={(e) => setProcessSearch(e.target.value)}
                    style={{
                      background: "#010409",
                      border: "1px solid rgba(0, 240, 255, 0.3)",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      color: "#fff",
                      fontSize: "11px",
                      outline: "none",
                      width: "180px"
                    }}
                  />
                </div>
              </div>

              <div style={{ overflowX: "auto", maxHeight: "480px", overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                  <thead>
                    <tr style={{ background: "rgba(0, 240, 255, 0.1)", borderBottom: "1px solid rgba(0, 240, 255, 0.3)", color: "#00f0ff", textAlign: "left", position: "sticky", top: 0, zIndex: 2 }}>
                      <th style={{ padding: "6px 10px" }}>PID</th>
                      <th style={{ padding: "6px 10px" }}>PROCESS NAME</th>
                      <th style={{ padding: "6px 10px" }}>USER / SESSION</th>
                      <th style={{ padding: "6px 10px" }}>CPU %</th>
                      <th style={{ padding: "6px 10px" }}>MEMORY (MB / %)</th>
                      <th style={{ padding: "6px 10px" }}>STATUS</th>
                      <th style={{ padding: "6px 10px", textAlign: "right" }}>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayProcesses.map((p, i) => (
                      <tr key={p.pid} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: i % 2 === 0 ? "rgba(1,4,10,0.4)" : "transparent" }}>
                        <td style={{ padding: "6px 10px", color: "#94a3b8" }}>#{p.pid}</td>
                        <td style={{ padding: "6px 10px", fontWeight: "bold", color: "#fff" }}>{p.name}</td>
                        <td style={{ padding: "6px 10px", color: "#94a3b8" }}>{p.user || "Harishan"}</td>
                        <td style={{ padding: "6px 10px", color: p.cpu_percent > 5 ? "#f87171" : "#00f0ff", fontWeight: "bold" }}>
                          {p.cpu_percent}%
                        </td>
                        <td style={{ padding: "6px 10px", color: "#38bdf8", fontWeight: "bold" }}>
                          {p.memory_mb ? `${p.memory_mb} MB` : `${p.memory_percent}%`}
                        </td>
                        <td style={{ padding: "6px 10px", color: "#34d399", fontWeight: "bold" }}>
                          ● {p.status || "RUNNING"}
                        </td>
                        <td style={{ padding: "6px 10px", textAlign: "right" }}>
                          <button
                            onClick={() => handleKillProcess(p.pid, p.name)}
                            disabled={terminatingPid === p.pid || p.pid <= 4}
                            style={{
                              background: "rgba(239, 68, 68, 0.15)",
                              border: "1px solid rgba(239, 68, 68, 0.4)",
                              color: "#f87171",
                              borderRadius: "4px",
                              padding: "2px 8px",
                              fontSize: "10px",
                              fontWeight: "bold",
                              cursor: terminatingPid === p.pid || p.pid <= 4 ? "not-allowed" : "pointer"
                            }}
                            title={`End task ${p.name} (PID: ${p.pid})`}
                          >
                            {terminatingPid === p.pid ? "ENDING..." : "✕ END TASK"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: WINDOWS SERVICES MANAGER */}
        {activeTab === "services" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="jarvis-glass-card" style={{ padding: "16px", background: "rgba(0, 15, 25, 0.75)", border: "1px solid rgba(0, 240, 255, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <h3 style={{ fontFamily: "Orbitron, sans-serif", fontSize: "13px", color: "#00f0ff" }}>
                    WINDOWS SERVICES CONTROLLER
                  </h3>
                  <span style={{ fontSize: "10px", color: "#94a3b8" }}>
                    ({filteredServices.length} Services Listed)
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <select
                    value={serviceStatusFilter}
                    onChange={(e) => setServiceStatusFilter(e.target.value as any)}
                    style={{
                      background: "#010409",
                      border: "1px solid rgba(0, 240, 255, 0.3)",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      color: "#00f0ff",
                      fontSize: "11px",
                      outline: "none"
                    }}
                  >
                    <option value="all">All Statuses</option>
                    <option value="running">Running Only</option>
                    <option value="stopped">Stopped Only</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Search services..."
                    value={serviceSearch}
                    onChange={(e) => setServiceSearch(e.target.value)}
                    style={{
                      background: "#010409",
                      border: "1px solid rgba(0, 240, 255, 0.3)",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      color: "#fff",
                      fontSize: "11px",
                      outline: "none",
                      width: "180px"
                    }}
                  />

                  <button
                    onClick={fetchServices}
                    disabled={isFetchingServices}
                    style={{
                      background: "rgba(0, 240, 255, 0.15)",
                      border: "1px solid rgba(0, 240, 255, 0.4)",
                      color: "#00f0ff",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      fontSize: "10px",
                      cursor: "pointer"
                    }}
                  >
                    {isFetchingServices ? "LOADING..." : "⟳ REFRESH"}
                  </button>
                </div>
              </div>

              <div style={{ overflowX: "auto", maxHeight: "480px", overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                  <thead>
                    <tr style={{ background: "rgba(0, 240, 255, 0.1)", borderBottom: "1px solid rgba(0, 240, 255, 0.3)", color: "#00f0ff", textAlign: "left", position: "sticky", top: 0, zIndex: 2 }}>
                      <th style={{ padding: "6px 10px" }}>SERVICE NAME</th>
                      <th style={{ padding: "6px 10px" }}>DISPLAY NAME</th>
                      <th style={{ padding: "6px 10px" }}>START TYPE</th>
                      <th style={{ padding: "6px 10px" }}>STATUS</th>
                      <th style={{ padding: "6px 10px", textAlign: "right" }}>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredServices.map((s, i) => {
                      const isRunning = s.status.toLowerCase() === "running";
                      const isLoadingThis = serviceActionLoading?.startsWith(`${s.name}:`);

                      return (
                        <tr key={s.name} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: i % 2 === 0 ? "rgba(1,4,10,0.4)" : "transparent" }}>
                          <td style={{ padding: "6px 10px", fontWeight: "bold", color: "#00f0ff" }}>{s.name}</td>
                          <td style={{ padding: "6px 10px", color: "#e2e8f0" }}>{s.display_name || s.name}</td>
                          <td style={{ padding: "6px 10px", color: "#94a3b8" }}>{s.start_type || "manual"}</td>
                          <td style={{ padding: "6px 10px", color: isRunning ? "#34d399" : "#94a3b8", fontWeight: "bold" }}>
                            {isRunning ? "● RUNNING" : "○ STOPPED"}
                          </td>
                          <td style={{ padding: "6px 10px", textAlign: "right" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                              {isRunning ? (
                                <>
                                  <button
                                    onClick={() => handleServiceAction(s.name, "stop")}
                                    disabled={isLoadingThis}
                                    style={{
                                      background: "rgba(239, 68, 68, 0.15)",
                                      border: "1px solid rgba(239, 68, 68, 0.4)",
                                      color: "#f87171",
                                      borderRadius: "3px",
                                      padding: "2px 6px",
                                      fontSize: "9.5px",
                                      cursor: "pointer"
                                    }}
                                  >
                                    STOP
                                  </button>
                                  <button
                                    onClick={() => handleServiceAction(s.name, "restart")}
                                    disabled={isLoadingThis}
                                    style={{
                                      background: "rgba(251, 191, 36, 0.15)",
                                      border: "1px solid rgba(251, 191, 36, 0.4)",
                                      color: "#fbbf24",
                                      borderRadius: "3px",
                                      padding: "2px 6px",
                                      fontSize: "9.5px",
                                      cursor: "pointer"
                                    }}
                                  >
                                    RESTART
                                  </button>
                                </>
                              ) : (
                                <button
                                  onClick={() => handleServiceAction(s.name, "start")}
                                  disabled={isLoadingThis}
                                  style={{
                                    background: "rgba(52, 211, 153, 0.15)",
                                    border: "1px solid rgba(52, 211, 153, 0.4)",
                                    color: "#34d399",
                                    borderRadius: "3px",
                                    padding: "2px 6px",
                                    fontSize: "9.5px",
                                    cursor: "pointer"
                                  }}
                                >
                                  START
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
