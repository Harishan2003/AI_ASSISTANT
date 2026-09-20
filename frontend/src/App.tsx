/**
 * Friday AI Assistant - Main Application Interface
 * ================================================
 * Futuristic JARVIS-inspired user interface for Friday AI Assistant.
 * Restores the authentic Friday Central Neural Core glowing circle, dynamic rotating arcs,
 * circular wave mesh, bottom frequency canvas, STOP execution button, staged file attachment chips,
 * real-time telemetry HUD, 24-hour conversational memory sessions, and 7-box configuration center.
 */

import React, { useState, useEffect, useRef } from "react";
import "./App.css";

// Shared Types & Interfaces
import type {
  Message,
  ConversationItem,
  UserProfile,
  GpuInfo,
  PowerSettings,
  BatteryState,
  WhatsAppSettings,
  WhatsAppLog,
  UrgentAlert,
  FeatureScanResult,
  DeviceMonitoringSettings
} from "./types/assistant";


// Modular UI Components
import { ProcessingIndicator } from "./components/ProcessingIndicator";
import { UrgentAlertBanner } from "./components/UrgentAlertBanner";
import { SettingsModal } from "./components/SettingsModal";
import { BlueLightMapModal } from "./components/BlueLightMapModal";

export const App: React.FC = () => {
  // ---------------------------------------------------------------------------
  // 1. STATE DEFINITIONS
  // ---------------------------------------------------------------------------

  // Conversation & Chat History States
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>(() => {
    return localStorage.getItem("friday_active_conv_id") || "";
  });
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [chatSearchQuery, setChatSearchQuery] = useState<string>("");
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitleText, setEditingTitleText] = useState<string>("");

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      sender: "system",
      text: "SYSTEM ONLINE // NEURAL CORE ENGAGED",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [inputText, setInputText] = useState<string>("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [assistantState, setAssistantState] = useState<"idle" | "listening" | "speaking" | "thinking">("idle");
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isTerminalCollapsed, setIsTerminalCollapsed] = useState<boolean>(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("english");
  const [isGlobalMuted, setIsGlobalMuted] = useState<boolean>(false);

  // Real-Time Hardware Telemetry States
  const [cpuVal, setCpuVal] = useState<number>(48);
  const [ramUsedGb, setRamUsedGb] = useState<number>(12.2);
  const [ramTotalGb] = useState<number>(15.3);
  const [diskUsedGb, setDiskUsedGb] = useState<number>(353.4);
  const [diskTotalGb, setDiskTotalGb] = useState<number>(446.5);
  const [wifiSpeed, setWifiSpeed] = useState<string>("0.0M");
  const [fanSpeed, setFanSpeed] = useState<string>("2800 RPM");
  const [memFreq, setMemFreq] = useState<string>("4800 MT/s");

  const [gpus, setGpus] = useState<GpuInfo[]>([
    { id: "gpu0", label: "GPU 0", shortName: "RTX", load: 0, temp: 50 },
    { id: "gpu1", label: "GPU 1", shortName: "Radeon", load: 4, temp: 45 }
  ]);

  // Settings & Modal States
  const [currentView, setCurrentView] = useState<"home" | "chat" | "map">("home");
  const [isMapModalOpen, setIsMapModalOpen] = useState<boolean>(false);
  const [selectedMapRegion, setSelectedMapRegion] = useState<string>("india");
  const [selectedMapTitle, setSelectedMapTitle] = useState<string>("Real Holographic Cyber Map");
  const [mapSearchTrigger, setMapSearchTrigger] = useState<string | null>(null);
  const [mapRouteTrigger, setMapRouteTrigger] = useState<{ from: string; to: string } | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isBox1Open, setIsBox1Open] = useState<boolean>(false);
  const [isBox2Open, setIsBox2Open] = useState<boolean>(false);
  const [isBox3Open, setIsBox3Open] = useState<boolean>(false);
  const [isBox4Open, setIsBox4Open] = useState<boolean>(false);
  const [isBoxScanOpen, setIsBoxScanOpen] = useState<boolean>(false);
  const [isBox6Open, setIsBox6Open] = useState<boolean>(false);
  const [isBox7Open, setIsBox7Open] = useState<boolean>(false);
  const [isBox8Open, setIsBox8Open] = useState<boolean>(false);

  // Device Monitoring States
  const [deviceSettings, setDeviceSettings] = useState<DeviceMonitoringSettings>({
    device_monitoring_enabled: false,
    ocr_enabled: true,
    action_delay_ms: 100,
    verification_enabled: true,
    privacy_blur_sensitive: true,
  });
  const [isUpdatingDevice, setIsUpdatingDevice] = useState<boolean>(false);

  // Power & Battery Saver States

  const [powerSettings, setPowerSettings] = useState<PowerSettings>({
    eco_mode: true,
    auto_battery_saver: true,
    telemetry_interval_battery: 6.0,
    telemetry_interval_ac: 2.0,
  });
  const [batteryState, setBatteryState] = useState<BatteryState | null>(null);
  const [isEcoActive, setIsEcoActive] = useState<boolean>(false);
  const [isUpdatingPower, setIsUpdatingPower] = useState<boolean>(false);

  // WhatsApp Plugin States
  const [whatsappSettings, setWhatsappSettings] = useState<WhatsAppSettings>({
    enabled: false,
    auto_reply: true,
    monitoring_active: false,
    custom_auto_reply_message: "",
    replied_count: 0,
  });
  const [customAutoReplyText, setCustomAutoReplyText] = useState<string>("");
  const [whatsappLogs, setWhatsappLogs] = useState<WhatsAppLog[]>([]);
  const [whatsappRecipient, setWhatsappRecipient] = useState<string>("");
  const [whatsappMsgText, setWhatsappMsgText] = useState<string>("");
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState<boolean>(false);
  const [isUpdatingWhatsApp, setIsUpdatingWhatsApp] = useState<boolean>(false);

  // Feature Health Scanner States
  const [isScanningFeatures, setIsScanningFeatures] = useState<boolean>(false);
  const [featureScanResults, setFeatureScanResults] = useState<FeatureScanResult[]>([]);
  const [featureSearchQuery, setFeatureSearchQuery] = useState<string>("");

  // Custom Paths & Security States
  const [savedPaths, setSavedPaths] = useState<{ route_name: string; path: string }[]>([]);
  const [addRoute, setAddRoute] = useState<string>("");
  const [addPathLoc, setAddPathLoc] = useState<string>("");

  const [masterPasswordInput, setMasterPasswordInput] = useState<string>("");
  const [newMasterPasswordInput, setNewMasterPasswordInput] = useState<string>("");
  const [isLockAuthenticated, setIsLockAuthenticated] = useState<boolean>(false);
  const [lockMappings, setLockMappings] = useState<{ keyword: string; password: string }[]>([]);
  const [urgentAlert, setUrgentAlert] = useState<UrgentAlert | null>(null);

  const [profile, setProfile] = useState<UserProfile>({
    name: "Harishan",
    agent_name: "Friday",
    age: "",
    email: "",
    city: "",
    voice_gender: "female",
    languages: ["english", "tamil", "tanglish"],
  });

  const [settingsForm, setSettingsForm] = useState<UserProfile>({
    name: "Harishan",
    agent_name: "Friday",
    age: "",
    email: "",
    city: "",
    voice_gender: "female",
    languages: ["english", "tamil", "tanglish"],
  });

  // DOM & Execution Canvas Refs
  const centerCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isListeningDesiredRef = useRef<boolean>(true);
  const isSpeakingRef = useRef<boolean>(false);
  const profileRef = useRef<UserProfile>(profile);

  const assistantStateRef = useRef(assistantState);
  const isThinkingRef = useRef(isThinking);
  const isListeningRef = useRef(isListening);

  useEffect(() => {
    assistantStateRef.current = assistantState;
    isThinkingRef.current = isThinking;
    isListeningRef.current = isListening;
  }, [assistantState, isThinking, isListening]);

  useEffect(() => {
    profileRef.current = profile;
  }, [profile]);

  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem("friday_active_conv_id", activeConversationId);
    }
  }, [activeConversationId]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isThinking]);

  useEffect(() => {
    if (isGlobalMuted) {
      if (activeAudioRef.current) {
        try {
          activeAudioRef.current.pause();
          activeAudioRef.current.currentTime = 0;
        } catch (e) { }
        activeAudioRef.current = null;
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      isSpeakingRef.current = false;
      setAssistantState("idle");
    }
  }, [isGlobalMuted]);

  // ---------------------------------------------------------------------------
  // 2. INITIAL DATA LOADING & TELEMETRY WEBSOCKET
  // ---------------------------------------------------------------------------

  const fetchProfile = () => {
    fetch("http://localhost:8000/api/profile")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.name) {
          const loaded: UserProfile = {
            name: data.name,
            agent_name: data.agent_name || data.wake_word || "Friday",
            age: data.age || "",
            email: data.email || "",
            city: data.city || "",
            voice_gender: (data.voice_gender || "female") as "female" | "male",
            languages: Array.isArray(data.languages) ? data.languages : ["english", "tamil", "tanglish"],
          };
          setProfile(loaded);
          setSettingsForm(loaded);
        }
      })
      .catch(() => { });
  };

  useEffect(() => {
    fetchProfile();
    fetchConversations();
    fetchPowerSettings();
    fetchWhatsAppSettings();
    fetchLockConfig();
    fetchPaths();
  }, []);

  useEffect(() => {
    /**
     * What does this function do:
     * Connects to the backend WebSocket telemetry stream (/ws/voice) to receive real-time
     * CPU, RAM, Disk, Wi-Fi, Fan, Memory Frequency, and Dual GPU hardware data.
     */
    let activeWs: WebSocket | null = null;
    let isMounted = true;

    const connectTelemetry = () => {
      try {
        activeWs = new WebSocket("ws://localhost:8000/ws/voice");
        activeWs.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === "telemetry" && payload.data) {
              const d = payload.data;
              if (typeof d.cpu === "number") setCpuVal(d.cpu);
              if (typeof d.mem === "number") {
                const total = 15.3;
                setRamUsedGb(Number(((d.mem / 100) * total).toFixed(1)));
              }
              if (typeof d.diskUsed === "number") setDiskUsedGb(d.diskUsed);
              if (typeof d.diskTotal === "number") setDiskTotalGb(d.diskTotal);
              if (Array.isArray(d.gpus) && d.gpus.length > 0) {
                setGpus(d.gpus);
              }
              if (d.net) setWifiSpeed(d.net);
              if (d.fan) setFanSpeed(d.fan);
              if (d.memFreq) setMemFreq(d.memFreq);
            }
          } catch (err) { }
        };
      } catch (e) { }
    };

    connectTelemetry();

    return () => {
      isMounted = false;
      if (activeWs) activeWs.close();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // 3. CANVAS ANIMATIONS: CENTRAL NEURAL CORE & BOTTOM FREQUENCY WAVE
  // ---------------------------------------------------------------------------

  // Central Neural Core Dynamic Concentric Arc & Mesh Renderer
  useEffect(() => {
    /**
     * What does this function do:
     * Renders the authentic animated Friday Central Neural Core circle inside the center canvas,
     * including rotating segmented neon arcs, 28-strand organic circular wave mesh, and glowing reactor pulse.
     */
    const canvas = centerCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let angle = 0;
    let meshStep = 0;

    const drawSegmentedArc = (
      cx: number,
      cy: number,
      radius: number,
      segments: number,
      gap: number,
      color: string,
      lineWidth: number,
      rot: number
    ) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;

      const segAngle = (Math.PI * 2) / segments;
      for (let i = 0; i < segments; i++) {
        ctx.beginPath();
        ctx.arc(0, 0, radius, i * segAngle, (i + 1) * segAngle - gap);
        ctx.stroke();
      }
      ctx.restore();
    };

    const drawCircularWaveMesh = (
      cx: number,
      cy: number,
      isSpeaking: boolean,
      isThinkingActive: boolean,
      isBlue: boolean
    ) => {
      ctx.save();

      const numStrands = 28;
      const pointsPerRing = 130;
      const baseAmp = isSpeaking ? 22 : isThinkingActive ? 8 : 2.5;
      const speed = isSpeaking ? 0.055 : isThinkingActive ? 0.025 : 0.012;

      meshStep += speed;

      for (let s = 0; s < numStrands; s++) {
        const offsetFraction = (s / numStrands) - 0.5;
        const radiusOffset = offsetFraction * (isSpeaking ? 56 : 22);
        const baseR = 106 + radiusOffset;
        const phaseShift = s * 0.22;

        ctx.beginPath();
        for (let i = 0; i <= pointsPerRing; i++) {
          const theta = (i / pointsPerRing) * Math.PI * 2;
          const waveHarmonic1 = Math.sin(theta * 4 + meshStep + phaseShift) * baseAmp;
          const waveHarmonic2 = Math.cos(theta * 7 - meshStep * 0.8 + phaseShift * 0.6) * (baseAmp * 0.45);
          const r = Math.max(20, baseR + waveHarmonic1 + waveHarmonic2);

          const x = cx + Math.cos(theta) * r;
          const y = cy + Math.sin(theta) * r;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();

        const alpha = Math.max(0.12, 1 - Math.abs(offsetFraction) * 1.8) * (isSpeaking ? 0.85 : 0.35);
        const primaryColor = isBlue ? `rgba(0, 240, 255, ${alpha})` : `rgba(248, 113, 113, ${alpha})`;
        const secondaryColor = isBlue ? `rgba(0, 140, 255, ${alpha * 0.85})` : `rgba(239, 68, 68, ${alpha * 0.85})`;
        ctx.strokeStyle = s % 2 === 0 ? primaryColor : secondaryColor;
        ctx.lineWidth = s % 4 === 0 ? 1.4 : 0.8;

        if (isSpeaking && s % 5 === 0) {
          ctx.shadowColor = isBlue ? "#00f0ff" : "#ef4444";
          ctx.shadowBlur = 12;
        } else {
          ctx.shadowBlur = 0;
        }

        ctx.stroke();
      }

      ctx.restore();
    };

    const render = () => {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;

      const isSpeaking = assistantStateRef.current === "speaking";
      const isThinkingActive = isThinkingRef.current;
      const isBlue = isSpeaking || isListeningRef.current;

      const arcCol1 = isBlue ? "rgba(0, 240, 255, 0.88)" : "rgba(248, 113, 113, 0.88)";
      const arcCol2 = isBlue ? "rgba(0, 140, 255, 0.45)" : "rgba(239, 68, 68, 0.45)";
      const arcCol3 = isBlue ? "rgba(0, 240, 255, 0.65)" : "rgba(248, 113, 113, 0.65)";
      const arcCol4 = isBlue ? "rgba(0, 240, 255, 0.95)" : "rgba(239, 68, 68, 0.95)";

      drawSegmentedArc(cx, cy, 125, 4, 0.45, arcCol1, 2.5, angle * 0.6);
      drawSegmentedArc(cx, cy, 112, 24, 0.08, arcCol2, 1.8, -angle * 0.8);
      drawSegmentedArc(cx, cy, 96, 40, 0.05, arcCol3, 2.5, angle * 0.5);
      drawSegmentedArc(cx, cy, 76, 8, 0.25, arcCol4, 1.8, -angle * 1.3);

      const pulse = isSpeaking ? 1.6 : isThinkingActive ? 1.25 : 1.0;
      const coreR = Math.max(10, 18 + Math.sin(angle * 6) * (2.5 * pulse));

      const radGrad = ctx.createRadialGradient(cx, cy, 1.5, cx, cy, coreR);
      radGrad.addColorStop(0, "#ffffff");
      radGrad.addColorStop(0.35, isBlue ? (isSpeaking ? "#38bdf8" : "#00f0ff") : "#ef4444");
      radGrad.addColorStop(0.85, isBlue ? "rgba(0, 119, 255, 0.35)" : "rgba(239, 68, 68, 0.35)");
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fillStyle = radGrad;
      ctx.fill();

      drawCircularWaveMesh(cx, cy, isSpeaking, isThinkingActive, isBlue);

      angle += isSpeaking ? 0.045 : isThinkingActive ? 0.025 : 0.012;
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [currentView]);

  // ---------------------------------------------------------------------------
  // 4. POWER & BATTERY SAVER CONTROLS
  // ---------------------------------------------------------------------------

  const fetchPowerSettings = async () => {
    /**
     * What does this function do:
     * Queries backend GET /api/v1/settings/power to retrieve Eco Mode and battery state.
     */
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/power");
      const data = await res.json();
      if (data && data.status === "success") {
        if (data.settings) setPowerSettings(data.settings);
        if (data.battery) setBatteryState(data.battery);
        setIsEcoActive(Boolean(data.is_eco_active));
      }
    } catch (e) { }
  };

  const updatePowerSettings = async (eco: boolean, autoBattery: boolean) => {
    /**
     * What does this function do:
     * Saves updated Eco Mode or battery saver intervals to the backend.
     */
    setIsUpdatingPower(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/power", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ eco_mode: eco, auto_battery_saver: autoBattery }),
      });
      const data = await res.json();
      if (data && data.status === "success") {
        if (data.settings) setPowerSettings(data.settings);
        if (data.battery) setBatteryState(data.battery);
        setIsEcoActive(Boolean(data.is_eco_active));
      }
    } catch (e) {
      alert("Failed to update power settings.");
    } finally {
      setIsUpdatingPower(false);
    }
  };

  // ---------------------------------------------------------------------------
  // 5. CONVERSATION MANAGEMENT & MEMORY
  // ---------------------------------------------------------------------------

  const fetchConversations = async (targetToSelect?: string) => {
    /**
     * What does this function do:
     * Retrieves the list of active 24-hour conversational sessions from backend storage.
     */
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations");
      const data = await res.json();
      if (data && data.status === "success" && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
        if (targetToSelect) {
          loadConversation(targetToSelect);
        } else if (!activeConversationId && data.conversations.length > 0) {
          loadConversation(data.conversations[0].conversation_id);
        } else if (!activeConversationId && data.conversations.length === 0) {
          createNewConversation();
        }
      }
    } catch (e) { }
  };

  const createNewConversation = async () => {
    /**
     * What does this function do:
     * Creates a fresh conversational session and registers it with the memory service.
     */
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New chat" }),
      });
      const data = await res.json();
      if (data && data.status === "success" && data.conversation) {
        const newConv = data.conversation;
        setConversations((prev) => [
          {
            conversation_id: newConv.conversation_id,
            title: newConv.title,
            created_at: newConv.created_at,
            updated_at: newConv.updated_at,
            message_count: 0,
          },
          ...prev,
        ]);
        setActiveConversationId(newConv.conversation_id);
        setMessages([
          {
            id: Math.random().toString(36).substring(2, 9),
            sender: "system",
            text: "NEW SESSION ENGAGED // MEMORY CONNECTED",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      }
    } catch {
      const fallbackId = "conv_" + Math.random().toString(36).substring(2, 9);
      setActiveConversationId(fallbackId);
      setConversations((prev) => [
        {
          conversation_id: fallbackId,
          title: "New chat",
          created_at: Date.now(),
          updated_at: Date.now(),
          message_count: 0,
        },
        ...prev,
      ]);
    }
  };

  const loadConversation = async (convId: string) => {
    /**
     * What does this function do:
     * Loads previous messages from conversation file storage into the active chat window.
     */
    setActiveConversationId(convId);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/conversations/${convId}`);
      const data = await res.json();
      if (data && data.status === "success" && data.conversation) {
        const msgs = data.conversation.messages || [];
        if (msgs.length > 0) {
          setMessages(
            msgs.map((m: any) => ({
              id: m.message_id || Math.random().toString(36).substring(2, 9),
              sender: m.role === "user" ? "user" : m.role === "assistant" ? "friday" : "system",
              text: m.content,
              timestamp: new Date((m.created_at || Date.now() / 1000) * 1000).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
            }))
          );
        } else {
          setMessages([
            {
              id: "1",
              sender: "system",
              text: `LOADED SESSION ${convId} // MEMORY SYNCED`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
        }
      }
    } catch (e) { }
  };

  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    /**
     * What does this function do:
     * Deletes a conversation file permanently from memory storage.
     */
    e.stopPropagation();
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await fetch(`http://localhost:8000/api/v1/conversations/${convId}`, { method: "DELETE" });
      const remaining = conversations.filter((c) => c.conversation_id !== convId);
      setConversations(remaining);
      if (activeConversationId === convId) {
        if (remaining.length > 0) {
          loadConversation(remaining[0].conversation_id);
        } else {
          createNewConversation();
        }
      }
    } catch {
      alert("Failed to delete conversation.");
    }
  };

  const renameConversation = async (convId: string, newTitle: string) => {
    /**
     * What does this function do:
     * Renames an active conversation session title in persistent storage.
     */
    if (!newTitle.trim()) return;
    try {
      await fetch(`http://localhost:8000/api/v1/conversations/${convId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      setConversations((prev) =>
        prev.map((c) => (c.conversation_id === convId ? { ...c, title: newTitle.trim() } : c))
      );
    } catch (e) { }
  };

  const clearCurrentHistory = async () => {
    /**
     * What does this function do:
     * Clears all message logs from the active conversation while preserving the session ID.
     */
    if (!activeConversationId || !window.confirm("Clear all messages in this conversation?")) return;
    try {
      await fetch(`http://localhost:8000/api/v1/conversations/${activeConversationId}/messages`, {
        method: "DELETE",
      });
      setMessages([
        {
          id: "1",
          sender: "system",
          text: "HISTORY CLEARED",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      fetchConversations();
    } catch {
      alert("Failed to clear messages.");
    }
  };

  // ---------------------------------------------------------------------------
  // 6. VOICE RECOGNITION, SPEECH SYNTHESIS & STOP EXECUTION
  // ---------------------------------------------------------------------------

  const sanitizeDisplayMessage = (text: string): string => {
    /**
     * What does this function do:
     * Strips <think> tags, action tags, and cleans reasoning block text from display output.
     */
    if (!text || typeof text !== "string") return "Processing complete.";
    let clean = text;
    if (clean.toLowerCase().includes("</think>")) {
      const parts = clean.split(/<\/think>/i);
      clean = parts[parts.length - 1];
    }
    clean = clean.replace(/<think>[\s\S]*?<\/think>/gi, "");
    clean = clean.replace(/\[\[ACTION:.*?\]\]/gi, "");
    return clean.trim() || text.trim() || "Ready.";
  };

  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    /**
     * What does this function do:
     * Pre-caches browser Text-To-Speech voices immediately when available (including Tamil and Indian English voices).
     */
    if ("speechSynthesis" in window) {
      const updateVoices = () => {
        try {
          const list = window.speechSynthesis.getVoices();
          if (list && list.length > 0) {
            voicesRef.current = list;
          }
        } catch (e) { }
      };
      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  const selectOptimalVoice = (text: string) => {
    /**
     * What does this function do:
     * Analyzes text to dynamically select optimal TTS voice engine, locale, pitch, and speech rate,
     * strictly honoring the user's selected gender (Female vs Male) so the voice identity NEVER drifts.
     */
    const clean = text.trim();
    const isTamil = /[\u0B80-\u0BFF]/.test(clean);
    const isTanglish = /\b(vanakkam|nandri|epdi|eppadi|irukinga|irukeenga|irukken|irukku|solunga|sollunga|pannunga|panren|panniten|romba|seri|theriyuma|kudunga|enna|enga|yaar|ungalukku|enakku|tamil|tanglish|tamilnadu|illai|aama|illa|machan|thala|bro|vaanga|ponga|sollu|theriyum|varaverpu|anbu|nanba|nanbargale|amma|appa|anna|thambi|thangachi|akka)\b/i.test(clean);

    const gender = (profileRef.current.voice_gender || "female").toLowerCase();
    const isFemale = gender === "female";

    let allVoices: SpeechSynthesisVoice[] = [];
    try {
      if (voicesRef.current && voicesRef.current.length > 0) {
        allVoices = voicesRef.current;
      } else if (typeof window !== "undefined" && "speechSynthesis" in window) {
        allVoices = window.speechSynthesis.getVoices() || [];
        if (allVoices.length > 0) {
          voicesRef.current = allVoices;
        }
      }
    } catch (e) { }

    const femaleKeywords = [
      "female", "zira", "jenny", "samantha", "victoria", "karen", "aria", "sara", "eva", "neerja",
      "saranya", "pallavi", "heera", "veena", "latha", "catherine", "hazel", "susan", "serena",
      "anita", "julie", "joana", "helena", "alice", "agnes", "emma", "amy", "olivia", "soprano",
      "woman", "girl", "microsoft zira", "microsoft aria", "google uk english female"
    ];
    const maleKeywords = [
      "male", "david", "guy", "mark", "george", "daniel", "james", "alex", "prabhat", "ravi",
      "valluvar", "richard", "oliver", "stefan", "cosimo", "lee", "alva", "fred", "eric", "claude",
      "sean", "brian", "ryan", "andrew", "sam", "mike", "paul", "john", "peter", "tom", "chris",
      "man", "boy", "microsoft david", "microsoft mark", "google uk english male"
    ];

    const isVoiceMatchingGender = (v: SpeechSynthesisVoice) => {
      const name = (v.name || "").toLowerCase();
      if (isFemale) {
        if (maleKeywords.some((mk) => name.includes(mk))) return false;
        if (femaleKeywords.some((fk) => name.includes(fk))) return true;
        return !name.includes("male") && !name.includes("david") && !name.includes("mark") && !name.includes("george");
      } else {
        if (femaleKeywords.some((fk) => name.includes(fk))) return false;
        if (maleKeywords.some((mk) => name.includes(mk))) return true;
        return !name.includes("female") && !name.includes("zira") && !name.includes("samantha") && !name.includes("jenny");
      }
    };

    const findBestVoice = (candidates: SpeechSynthesisVoice[]): { voice: SpeechSynthesisVoice | null; isExactGender: boolean } => {
      // 1. First priority: Exact gender match in target language candidates
      const exactCandidate = candidates.find((v) => {
        const name = (v.name || "").toLowerCase();
        return isFemale ? femaleKeywords.some((fk) => name.includes(fk)) : maleKeywords.some((mk) => name.includes(mk));
      });
      if (exactCandidate) return { voice: exactCandidate, isExactGender: true };

      // 2. Second priority: Compatible gender match in candidates
      const compatibleCandidate = candidates.find(isVoiceMatchingGender);
      if (compatibleCandidate) return { voice: compatibleCandidate, isExactGender: true };

      // 3. Third priority: Exact gender match across ALL available browser voices (prevents gender switching across languages)
      const globalExact = allVoices.find((v) => {
        const name = (v.name || "").toLowerCase();
        return isFemale ? femaleKeywords.some((fk) => name.includes(fk)) : maleKeywords.some((mk) => name.includes(mk));
      });
      if (globalExact) return { voice: globalExact, isExactGender: true };

      const globalCompatible = allVoices.find(isVoiceMatchingGender);
      if (globalCompatible) return { voice: globalCompatible, isExactGender: true };

      // 4. Last resort: candidate voice or default voice
      return { voice: candidates[0] || allVoices[0] || null, isExactGender: false };
    };

    if (isTamil) {
      const tamilVoices = allVoices.filter((v) => {
        const langLower = (v.lang || "").toLowerCase().replace("_", "-");
        const nameLower = (v.name || "").toLowerCase();
        return langLower.startsWith("ta") || nameLower.includes("tamil");
      });
      const best = findBestVoice(tamilVoices);
      return {
        voice: best.voice,
        lang: best.voice?.lang || "ta-IN",
        rate: isFemale ? 0.95 : 0.90,
        pitch: isFemale ? (best.isExactGender ? 1.10 : 1.30) : (best.isExactGender ? 0.85 : 0.70)
      };
    }

    if (isTanglish) {
      const indianVoices = allVoices.filter((v) => {
        const langLower = (v.lang || "").toLowerCase().replace("_", "-");
        const nameLower = (v.name || "").toLowerCase();
        return langLower.includes("en-in") || langLower.startsWith("ta") || nameLower.includes("india");
      });
      const best = findBestVoice(indianVoices);
      return {
        voice: best.voice,
        lang: best.voice?.lang || "en-IN",
        rate: isFemale ? 0.98 : 0.92,
        pitch: isFemale ? (best.isExactGender ? 1.12 : 1.32) : (best.isExactGender ? 0.85 : 0.70)
      };
    }

    // Default English Voice
    const engVoices = allVoices.filter((v) => {
      const langLower = (v.lang || "").toLowerCase().replace("_", "-");
      return langLower.includes("en-us") || langLower.includes("en-gb") || langLower.includes("en-in") || langLower.startsWith("en");
    });
    const best = findBestVoice(engVoices);

    return {
      voice: best.voice,
      lang: best.voice?.lang || "en-US",
      rate: isFemale ? 1.05 : 0.98,
      pitch: isFemale ? (best.isExactGender ? 1.15 : 1.35) : (best.isExactGender ? 0.82 : 0.68)
    };
  };

  const cleanTextForVoice = (rawText?: string): string => {
    /**
     * What does this function do:
     * Cleans markdown syntax, links, emojis, and code blocks for fluid text-to-speech output in English, Tamil, and Tanglish.
     */
    if (!rawText || typeof rawText !== "string") return "";
    let text = sanitizeDisplayMessage(rawText);
    const isTamilText = /[\u0B80-\u0BFF]/.test(text);

    text = text.replace(/```[\s\S]*?```/g, isTamilText ? " குறியீட்டு விவரம் இணைக்கப்பட்டுள்ளது. " : " Here is the requested snippet, boss. ");
    text = text.replace(/`([^`]+)`/g, "$1");
    text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
    text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
    text = text.replace(/\*([^*]+)\*/g, "$1");
    text = text.replace(/#+\s+/g, "");
    text = text.replace(/\|/g, " ");

    // Remove UI emojis and decorative unicode symbols that trip up TTS engines
    text = text.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}]/gu, "");

    return text.replace(/\s+/g, " ").trim();
  };

  const safeStartRecognition = () => {
    /**
     * What does this function do:
     * Starts web speech recognition safely if mic input is enabled and Friday is not speaking.
     */
    if (!recognitionRef.current || !isListeningDesiredRef.current || isSpeakingRef.current || isThinking) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) { }
  };

  const safeStopRecognition = () => {
    /**
     * What does this function do:
     * Stops web speech recognition cleanly.
     */
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {
      try {
        recognitionRef.current.abort();
      } catch (err) { }
    }
    setIsListening(false);
  };

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";

    let restartTimer: any = null;

    recognition.onstart = () => {
      if (!isSpeakingRef.current && !isThinking) {
        setIsListening(true);
      }
    };

    recognition.onresult = (event: any) => {
      if (isSpeakingRef.current || isThinking) return;
      const transcript = event.results[event.results.length - 1][0].transcript.trim();

      const currentWakeWord = (profileRef.current.agent_name || "Friday").trim().toLowerCase();
      const wakeRegex = new RegExp(`\\b${currentWakeWord}\\b`, "i");

      if (!wakeRegex.test(transcript)) {
        return;
      }

      let cleanCommand = transcript
        .replace(new RegExp(`^(?:hey|hi|hello|vanakkam|வணக்கம்|ok)?\\s*${currentWakeWord}[,:\\s]*`, "i"), "")
        .trim();

      if (!cleanCommand) {
        cleanCommand = currentWakeWord;
      }

      if (cleanCommand) {
        setInputText(cleanCommand);
        handleSendMessage(undefined, cleanCommand);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      if (isListeningDesiredRef.current && !isSpeakingRef.current && !isThinking) {
        if (restartTimer) clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          safeStartRecognition();
        }, 300);
      }
    };

    recognitionRef.current = recognition;
    safeStartRecognition();

    return () => {
      if (restartTimer) clearTimeout(restartTimer);
      safeStopRecognition();
    };
  }, [isThinking]);

  const toggleListening = () => {
    /**
     * What does this function do:
     * Toggles continuous microphone listening ON / OFF.
     */
    if (!recognitionRef.current) {
      alert("Speech recognition is supported in Chrome or Edge.");
      return;
    }

    if (isListening) {
      isListeningDesiredRef.current = false;
      safeStopRecognition();
      setAssistantState("idle");
    } else {
      isListeningDesiredRef.current = true;
      safeStartRecognition();
    }
  };

  const handleTestVoice = (lang: "english" | "tamil" | "tanglish", gender: "female" | "male") => {
    /**
     * What does this function do:
     * Plays an instant voice sample in the selected language and gender (Female / Male) for operator evaluation.
     */
    let testMsg = "Hello Harishan! Friday voice synthesis is operating at peak performance.";
    if (lang === "tamil") {
      testMsg = "வணக்கம் ஹரிஷன்! தமிழ் குரல் வெளியீடு மிகச் சிறப்பாக இயங்குகிறது.";
    } else if (lang === "tanglish") {
      testMsg = "Vanakkam boss! Tanglish voice output super ah work aagudhu.";
    }

    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
      } catch (e) { }
      activeAudioRef.current = null;
    }
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) { }
    }

    const ttsUrl = `http://localhost:8000/api/tts?text=${encodeURIComponent(testMsg)}&gender=${gender}&language=${lang}`;
    fetch(ttsUrl)
      .then((res) => {
        if (!res.ok) throw new Error("TTS fetch failed");
        return res.blob();
      })
      .then((blob) => {
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        audio.preload = "auto";
        activeAudioRef.current = audio;
        audio.onended = () => URL.revokeObjectURL(audioUrl);
        audio.onerror = () => URL.revokeObjectURL(audioUrl);
        audio.play().catch(() => { });
      })
      .catch(() => { });
  };

  const speakSpecificMessage = (text?: string) => {
    /**
     * What does this function do:
     * High-fidelity speech synthesizer supporting Tamil, Tanglish, and English with Male/Female voice selection.
     * Uses backend neural TTS (/api/tts) with low-latency memory buffer, with transparent fallback to browser SpeechSynthesis.
     */
    if (!text) return;

    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
      } catch (e) { }
      activeAudioRef.current = null;
    }

    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) { }
    }

    const cleaned = cleanTextForVoice(text);
    if (!cleaned) return;

    isSpeakingRef.current = true;
    setAssistantState("speaking");
    safeStopRecognition();

    let hasEnded = false;
    const resumeListening = () => {
      if (hasEnded) return;
      hasEnded = true;
      activeAudioRef.current = null;
      isSpeakingRef.current = false;
      setAssistantState("idle");
      if (isListeningDesiredRef.current) {
        setTimeout(safeStartRecognition, 300);
      }
    };

    const fallbackToSpeechSynthesis = () => {
      if (hasEnded) return;

      if (!("speechSynthesis" in window)) {
        resumeListening();
        return;
      }

      const voiceConfig = selectOptimalVoice(cleaned);
      const utterance = new SpeechSynthesisUtterance(cleaned);
      utterance.lang = voiceConfig.lang;
      utterance.rate = voiceConfig.rate;
      utterance.pitch = voiceConfig.pitch;
      if (voiceConfig.voice) {
        utterance.voice = voiceConfig.voice;
      }

      utterance.onend = resumeListening;
      utterance.onerror = (e) => {
        console.warn("[SpeechSynthesis fallback] error:", e);
        resumeListening();
      };

      try {
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        resumeListening();
      }
    };

    // Optimize voice text: For long responses, synthesize key concise sentences for snappy speech response
    let speechInput = cleaned;
    if (speechInput.length > 320) {
      const sentenceMatch = speechInput.match(/^(?:.*?[.!?]\s+){1,2}/);
      if (sentenceMatch && sentenceMatch[0].length >= 35) {
        speechInput = sentenceMatch[0].trim();
      } else {
        speechInput = speechInput.slice(0, 260).replace(/\s+\S*$/, "") + ".";
      }
    }

    // 1. Primary: High-fidelity, low-latency Neural TTS with 7.0s timeout fallback to avoid any voice stalls
    try {
      const gender = (profileRef.current.voice_gender || "female").toLowerCase();
      const ttsUrl = `http://localhost:8000/api/tts?text=${encodeURIComponent(speechInput)}&gender=${gender}`;

      const ttsAbort = new AbortController();
      const timeoutId = setTimeout(() => ttsAbort.abort(), 7000);

      fetch(ttsUrl, { signal: ttsAbort.signal })
        .then((res) => {
          clearTimeout(timeoutId);
          if (!res.ok || res.status === 204) throw new Error("TTS fetch failed");
          return res.blob();
        })
        .then((blob) => {
          if (hasEnded) return;
          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          audio.preload = "auto";
          activeAudioRef.current = audio;

          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            resumeListening();
          };

          audio.onerror = () => {
            URL.revokeObjectURL(audioUrl);
            fallbackToSpeechSynthesis();
          };

          audio.play().catch(() => {
            fallbackToSpeechSynthesis();
          });
        })
        .catch(() => {
          clearTimeout(timeoutId);
          fallbackToSpeechSynthesis();
        });
    } catch (e) {
      fallbackToSpeechSynthesis();
    }
  };

  const speakText = (text?: string, forceMuted: boolean = false) => {
    /**
     * What does this function do:
     * Speaks the assistant's response unless global audio mute is toggled ON.
     */
    if (forceMuted || isGlobalMuted || !text) return;
    speakSpecificMessage(text);
  };

  const handleStopExecution = () => {
    /**
     * What does this function do:
     * HALT BUTTON: Instantly aborts ongoing network requests, cancels speech synthesis / audio playback,
     * resets thinking indicators to idle, and logs 'EXECUTION HALTED BY OPERATOR.'
     */
    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
      } catch (e) { }
      activeAudioRef.current = null;
    }
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    isSpeakingRef.current = false;
    setAssistantState("idle");
    setIsThinking(false);
    addMessage("system", "EXECUTION HALTED BY OPERATOR.");
    safeStartRecognition();
  };

  // ---------------------------------------------------------------------------
  // 7. MESSAGE DISPATCH & DOCUMENT UPLOAD
  // ---------------------------------------------------------------------------

  const addMessage = async (sender: "user" | "friday" | "system", text: string) => {
    /**
     * What does this function do:
     * Appends a message to local state and persists it to the active memory session backend.
     */
    const sanitizedText = sender === "friday" ? sanitizeDisplayMessage(text) : text;
    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        sender,
        text: sanitizedText || "Ready.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);

    if (activeConversationId && sender !== "system") {
      try {
        await fetch(`http://localhost:8000/api/v1/conversations/${activeConversationId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: sender === "user" ? "user" : "assistant", content: sanitizedText }),
        });

        if (sender === "user") {
          const currentConv = conversations.find((c) => c.conversation_id === activeConversationId);
          if (currentConv && (currentConv.title === "New chat" || currentConv.title.startsWith("Session "))) {
            const newTitle = sanitizedText.slice(0, 30);
            renameConversation(activeConversationId, newTitle);
          }
        }
      } catch (e) { }
    }
  };

  const handleSendMessage = async (e?: React.FormEvent, overrideText?: string) => {
    /**
     * What does this function do:
     * Master user input dispatcher. Sends plain text queries to /api/chat or multi-file
     * uploads (PDF, code, CSV, images) to /api/analyze-files.
     */
    if (e) e.preventDefault();
    const clean = (overrideText !== undefined ? overrideText : inputText).trim();
    if (!clean && selectedFiles.length === 0) return;

    const filesToUpload = [...selectedFiles];
    const messagePayload = clean || `[Uploaded ${filesToUpload.length} file(s)]`;

    setInputText("");
    setSelectedFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";

    await addMessage("user", messagePayload);
    setAssistantState("thinking");
    setIsThinking(true);

    abortControllerRef.current = new AbortController();

    const detectedLang = /[\u0B80-\u0BFF]/.test(clean)
      ? "tamil"
      : /\b(vanakkam|nandri|epdi|eppadi|irukinga|irukeenga|irukken|irukku|solunga|sollunga|pannunga|panren|panniten|romba|seri|theriyuma|kudunga|enna|enga|yaar|ungalukku|enakku|tanglish|tamilnadu)\b/i.test(clean)
        ? "tanglish"
        : selectedLanguage;

    if (detectedLang !== selectedLanguage) {
      setSelectedLanguage(detectedLang);
    }

    try {
      let res;
      if (filesToUpload.length > 0) {
        const formData = new FormData();
        filesToUpload.forEach((f) => formData.append("files", f));
        formData.append("prompt", messagePayload);
        formData.append("language", detectedLang);
        formData.append("session_id", activeConversationId || "default");

        res = await fetch("http://localhost:8000/api/analyze-files", {
          method: "POST",
          body: formData,
          signal: abortControllerRef.current.signal,
        });
      } else {
        res = await fetch("http://localhost:8000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: messagePayload,
            language: detectedLang,
            session_id: activeConversationId || "default",
          }),
          signal: abortControllerRef.current.signal,
        });
      }

      const data = await res.json();
      const rawReply = data?.response || data?.message || "Command executed.";

      // Dispatch Internal Action Tags
      if (rawReply.includes("[[ACTION:")) {
        if (rawReply.includes("[[ACTION:OPEN_FRIDAY_MAP]]")) {
          setCurrentView("map");
        }
        const searchMatch = rawReply.match(/\[\[ACTION:FRIDAY_MAP_SEARCH:(.+?)\]\]/);
        if (searchMatch) {
          setCurrentView("map");
          setMapSearchTrigger(searchMatch[1]);
        }
        const routeMatch = rawReply.match(/\[\[ACTION:FRIDAY_MAP_ROUTE:(.+?):(.+?)\]\]/);
        if (routeMatch) {
          setCurrentView("map");
          setMapRouteTrigger({ from: routeMatch[1], to: routeMatch[2] });
        }
        const voiceMatch = rawReply.match(/\[\[ACTION:SET_VOICE_GENDER:(female|male)\]\]/i);
        if (voiceMatch) {
          const newGender = voiceMatch[1].toLowerCase() as "female" | "male";
          profileRef.current.voice_gender = newGender;
          setProfile((prev) => ({ ...prev, voice_gender: newGender }));
        }
        const deviceMatch = rawReply.match(/\[\[ACTION:SET_DEVICE_MONITOR:(true|false)\]\]/i);
        if (deviceMatch) {
          setDeviceSettings((prev) => ({ ...prev, device_monitoring_enabled: deviceMatch[1].toLowerCase() === "true" }));
        }
        const powerMatch = rawReply.match(/\[\[ACTION:SET_POWER_SETTINGS:(.+?)\]\]/);
        if (powerMatch) {
          try {
            const parsedPower = JSON.parse(powerMatch[1]);
            setPowerSettings((prev) => ({ ...prev, ...parsedPower }));
            if (parsedPower.eco_mode !== undefined) {
              setIsEcoActive(Boolean(parsedPower.eco_mode));
            }
          } catch (e) { }
        }
        const waMatch = rawReply.match(/\[\[ACTION:SET_WHATSAPP_SETTINGS:(.+?)\]\]/);
        if (waMatch) {
          try {
            const parsedWa = JSON.parse(waMatch[1]);
            setWhatsappSettings((prev) => ({ ...prev, ...parsedWa }));
          } catch (e) { }
        }
        if (rawReply.includes("[[ACTION:REFRESH_SETTINGS]]")) {
          fetchProfile();
          fetchWhatsAppSettings();
          fetchPowerSettings();
        }
      }

      const replyText = sanitizeDisplayMessage(rawReply);
      setIsThinking(false);
      setAssistantState("idle");
      await addMessage("friday", replyText);
      if (!isGlobalMuted) speakText(replyText, false);
    } catch (err: any) {
      if (err.name === "AbortError") {
        return; // Halted by user
      }
      setIsThinking(false);
      setAssistantState("idle");
      addMessage("system", "Target connection failure.");
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    /**
     * What does this function do:
     * Stages up to 6 selected local files (PDFs, images, code files) for multi-modal analysis.
     */
    const files = e.target.files;
    if (files && files.length > 0) {
      const fileArr = Array.from(files).slice(0, 6);
      setSelectedFiles(fileArr);
      addMessage("system", `ATTACHED FILE(S): ${fileArr.map((f) => f.name).join(", ")}`);
    }
  };

  const handleRemoveFile = (indexToRemove: number) => {
    /**
     * What does this function do:
     * Removes a staged file chip from the bottom attachment bar before sending.
     */
    const updatedFiles = selectedFiles.filter((_, idx) => idx !== indexToRemove);
    setSelectedFiles(updatedFiles);
    if (updatedFiles.length === 0 && fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // ---------------------------------------------------------------------------
  // 8. SETTINGS & CONFIGURATION ACTIONS
  // ---------------------------------------------------------------------------

  const fetchPaths = () => {
    fetch("http://localhost:8000/api/add-path")
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.paths)) {
          setSavedPaths(data.paths);
        } else if (Array.isArray(data)) {
          setSavedPaths(data);
        }
      })
      .catch(() => { });
  };

  const addCustomPath = async () => {
    if (!addRoute.trim() || !addPathLoc.trim()) return;
    try {
      await fetch("http://localhost:8000/api/add-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_name: addRoute.trim(), path: addPathLoc.trim() }),
      });
      setAddRoute("");
      setAddPathLoc("");
      fetchPaths();
    } catch (e) {
      alert("Failed to add custom path.");
    }
  };

  const deleteCustomPath = async (routeName: string) => {
    try {
      await fetch(`http://localhost:8000/api/add-path/${routeName}`, { method: "DELETE" });
      fetchPaths();
    } catch (e) {
      alert("Failed to delete custom path.");
    }
  };

  const fetchLockConfig = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/security/lock-folders");
      const data = await res.json();
      if (data && data.status === "success") {
        setLockMappings(data.lock_folders || []);
      }
    } catch (e) { }
  };

  const verifyMasterPassword = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/security/lock-folders/verify-master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: masterPasswordInput }),
      });
      const data = await res.json();
      if (data && data.authenticated) {
        setIsLockAuthenticated(true);
        fetchLockConfig();
      } else {
        alert("Incorrect Master Password.");
      }
    } catch {
      alert("Verification failed.");
    }
  };

  const saveLockConfig = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/security/lock-folders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_password: masterPasswordInput, lock_folders: lockMappings }),
      });
      alert("Folder security rules updated!");
    } catch {
      alert("Failed to save folder security rules.");
    }
  };

  const saveMasterPassword = async () => {
    if (!newMasterPasswordInput.trim()) return;
    try {
      await fetch("http://localhost:8000/api/v1/security/lock-folders/set-master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_master: masterPasswordInput, new_master: newMasterPasswordInput }),
      });
      setMasterPasswordInput(newMasterPasswordInput);
      setNewMasterPasswordInput("");
      alert("Master Password successfully updated!");
    } catch {
      alert("Failed to update master password.");
    }
  };

  const saveUserProfile = async () => {
    try {
      await fetch("http://localhost:8000/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsForm),
      });
      setProfile(settingsForm);
      alert("Profile updated!");
    } catch {
      alert("Failed to update profile.");
    }
  };

  const runFeatureScan = async () => {
    setIsScanningFeatures(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/scan-agent-features", {
        method: "POST"
      });
      const data = await res.json();
      const list = data?.features || data?.results || [];
      if (Array.isArray(list)) {
        setFeatureScanResults(list);
      }
    } catch {
      try {
        const fallbackRes = await fetch("http://localhost:8000/api/v1/system/features-scan");
        const fallbackData = await fallbackRes.json();
        const fallbackList = fallbackData?.features || fallbackData?.results || [];
        if (Array.isArray(fallbackList)) {
          setFeatureScanResults(fallbackList);
        }
      } catch (err) {
        alert("Feature scanner failed.");
      }
    } finally {
      setIsScanningFeatures(false);
    }
  };

  const fetchWhatsAppSettings = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/whatsapp");
      const data = await res.json();
      if (data && data.status === "success") {
        setWhatsappSettings(data.settings || data);
        setCustomAutoReplyText(data.custom_auto_reply_message || "");
      }
      const logsRes = await fetch("http://localhost:8000/api/v1/whatsapp/logs");
      const logsData = await logsRes.json();
      if (logsData && Array.isArray(logsData.logs)) {
        setWhatsappLogs(logsData.logs);
      }
    } catch (e) { }
  };

  const updateWhatsAppSettings = async (enabled: boolean, auto_reply: boolean, custom_msg?: string) => {
    setIsUpdatingWhatsApp(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/whatsapp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled,
          auto_reply,
          custom_auto_reply_message: custom_msg !== undefined ? custom_msg : customAutoReplyText,
        }),
      });
      const data = await res.json();
      if (data && data.status === "success") {
        setWhatsappSettings(data.settings || data);
      }
    } catch {
      alert("Failed to update WhatsApp settings.");
    } finally {
      setIsUpdatingWhatsApp(false);
    }
  };

  const sendTestWhatsAppMessage = async () => {
    if (!whatsappRecipient.trim() || !whatsappMsgText.trim()) {
      alert("Recipient contact name and message text are required.");
      return;
    }
    setIsSendingWhatsApp(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/whatsapp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact: whatsappRecipient.trim(), message: whatsappMsgText.trim() }),
      });
      const data = await res.json();
      if (data && data.status === "success") {
        alert(`Dispatched WhatsApp message to ${whatsappRecipient}!`);
        setWhatsappMsgText("");
      } else {
        alert(data.message || "Failed to send WhatsApp message.");
      }
    } catch {
      alert("Failed to send WhatsApp message.");
    } finally {
      setIsSendingWhatsApp(false);
    }
  };

  const cleanAgentDisplay = (profile.agent_name || "FRIDAY").toUpperCase();

  // ---------------------------------------------------------------------------
  // 9. AUTHENTIC JARVIS DASHBOARD UI RENDERING
  // ---------------------------------------------------------------------------

  return (
    <div className="jarvis-root-layout">
      {/* 1. Global Top Navbar: Spans 100% Full Width across ALL pages (HOME, CHAT AGENT & MAP) */}
      <header
        className={`jarvis-top-header ${currentView === "home" ? "" : "jarvis-glass-card"}`}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          minHeight: "50px",
          flexShrink: 0,
          background: currentView === "home" ? "transparent" : undefined,
          border: currentView === "home" ? "none" : undefined,
          boxShadow: currentView === "home" ? "none" : undefined
        }}
      >
        {/* Navigation Mode Buttons: HOME, CHAT AGENT & MAP */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div className="jarvis-logo-area" style={{ paddingBottom: 0, borderBottom: "none", marginRight: "4px" }}>
            <div className="jarvis-logo-icon" style={{ width: "26px", height: "26px", fontSize: "11px" }}>▲</div>
            <div className="jarvis-logo-text" style={{ fontSize: "0.85rem" }}>{cleanAgentDisplay}</div>
          </div>

          <button
            onClick={() => {
              setCurrentView("home");
              setIsMapModalOpen(false);
            }}
            style={{
              background: currentView === "home" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.2))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "home" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.25)",
              color: currentView === "home" ? "#00f0ff" : "#94a3b8",
              borderRadius: "6px",
              padding: "6px 14px",
              fontSize: "11px",
              fontWeight: "bold",
              letterSpacing: "1px",
              cursor: "pointer",
              boxShadow: currentView === "home" ? "0 0 12px rgba(0, 240, 255, 0.4), inset 0 0 8px rgba(0, 240, 255, 0.2)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            ⌂ HOME
          </button>

          <button
            onClick={() => {
              setCurrentView("chat");
              setIsMapModalOpen(false);
            }}
            style={{
              background: currentView === "chat" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.2))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "chat" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.25)",
              color: currentView === "chat" ? "#00f0ff" : "#94a3b8",
              borderRadius: "6px",
              padding: "6px 14px",
              fontSize: "11px",
              fontWeight: "bold",
              letterSpacing: "1px",
              cursor: "pointer",
              boxShadow: currentView === "chat" ? "0 0 12px rgba(0, 240, 255, 0.4), inset 0 0 8px rgba(0, 240, 255, 0.2)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            💬 CHAT AGENT
          </button>

          <button
            onClick={() => {
              setSelectedMapRegion("india");
              setSelectedMapTitle("Real Holographic Cyber Map");
              setCurrentView("map");
              setIsMapModalOpen(false);
            }}
            style={{
              background: currentView === "map" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.3))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "map" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.35)",
              color: currentView === "map" ? "#00f0ff" : "#38bdf8",
              borderRadius: "6px",
              padding: "6px 14px",
              fontSize: "11px",
              fontWeight: "bold",
              letterSpacing: "1px",
              cursor: "pointer",
              boxShadow: currentView === "map" ? "0 0 14px rgba(0, 240, 255, 0.5), inset 0 0 8px rgba(0, 240, 255, 0.2)" : "0 0 6px rgba(0, 240, 255, 0.15)",
              transition: "all 0.2s ease"
            }}
            title="Open Real Holographic Map (Street / City / Country)"
          >
            🌐 MAP
          </button>
        </div>

        {/* Right Controls: Search, Mute, Settings */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="text"
            placeholder="Search chat stream..."
            value={chatSearchQuery}
            onChange={(e) => setChatSearchQuery(e.target.value)}
            style={{
              background: "#010409",
              border: "1px solid rgba(0, 240, 255, 0.25)",
              borderRadius: "4px",
              padding: "4px 8px",
              color: "#fff",
              fontSize: "11px",
              outline: "none",
              width: "160px"
            }}
          />

          <button
            onClick={() => setIsGlobalMuted((prev) => !prev)}
            style={{
              background: isGlobalMuted ? "rgba(239, 68, 68, 0.2)" : "rgba(0, 240, 255, 0.15)",
              border: `1px solid ${isGlobalMuted ? "#f87171" : "rgba(0, 240, 255, 0.4)"}`,
              borderRadius: "4px",
              padding: "4px 8px",
              color: isGlobalMuted ? "#f87171" : "var(--jarvis-cyan)",
              cursor: "pointer",
              fontWeight: "bold",
              fontSize: "11px"
            }}
          >
            {isGlobalMuted ? "🔇 Mute" : "🔊 Audio"}
          </button>

          <button
            onClick={() => setIsSettingsOpen(true)}
            style={{
              background: "rgba(0, 240, 255, 0.15)",
              border: "1px solid rgba(0, 240, 255, 0.4)",
              color: "var(--jarvis-cyan)",
              borderRadius: "4px",
              padding: "4px 8px",
              cursor: "pointer",
              fontWeight: "bold",
              fontSize: "12px"
            }}
            title="Agent Settings"
          >
            ⚙️
          </button>
        </div>
      </header>

      {/* 2. Main Content Row: Sidebar (on Chat view) + Workspace */}
      <div style={{ flex: 1, display: "flex", gap: "10px", overflow: "hidden", position: "relative" }}>
        {/* Left Sidebar: Memory Sessions & Quick Controls (Only in CHAT AGENT view) */}
        {currentView === "chat" && (
          <aside className="jarvis-sidebar jarvis-glass-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
              <span style={{ fontSize: "10px", color: "var(--jarvis-cyan)", fontWeight: "bold", textTransform: "uppercase" }}>
                CONVERSATIONS
              </span>
              <button
                onClick={createNewConversation}
                style={{
                  background: "rgba(0, 240, 255, 0.15)",
                  border: "1px solid rgba(0, 240, 255, 0.4)",
                  color: "var(--jarvis-cyan)",
                  borderRadius: "4px",
                  padding: "2px 6px",
                  fontSize: "10px",
                  cursor: "pointer",
                  fontWeight: "bold"
                }}
              >
                + NEW
              </button>
            </div>

            <input
              type="text"
              placeholder="Filter sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: "#010409",
                border: "1px solid rgba(0, 240, 255, 0.25)",
                borderRadius: "4px",
                padding: "4px 8px",
                color: "#fff",
                fontSize: "11px",
                outline: "none"
              }}
            />

            <div className="jarvis-nav-list">
              {conversations
                .filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
                .map((c) => {
                  const isActive = c.conversation_id === activeConversationId;
                  return (
                    <div
                      key={c.conversation_id}
                      onClick={() => loadConversation(c.conversation_id)}
                      className={`jarvis-nav-item ${isActive ? "active" : ""}`}
                      style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                    >
                      {editingConvId === c.conversation_id ? (
                        <input
                          type="text"
                          value={editingTitleText}
                          onChange={(e) => setEditingTitleText(e.target.value)}
                          onBlur={() => {
                            renameConversation(c.conversation_id, editingTitleText);
                            setEditingConvId(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              renameConversation(c.conversation_id, editingTitleText);
                              setEditingConvId(null);
                            }
                          }}
                          autoFocus
                          style={{
                            background: "#010409",
                            border: "1px solid #00f0ff",
                            borderRadius: "3px",
                            color: "#fff",
                            padding: "2px 4px",
                            fontSize: "10px",
                            width: "80%"
                          }}
                        />
                      ) : (
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                          💬 {c.title}
                        </div>
                      )}

                      <div style={{ display: "flex", gap: "2px", marginLeft: "4px" }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingConvId(c.conversation_id);
                            setEditingTitleText(c.title);
                          }}
                          style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "9px" }}
                          title="Rename"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={(e) => deleteConversation(c.conversation_id, e)}
                          style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: "9px" }}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>

            <button
              onClick={clearCurrentHistory}
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                color: "#f87171",
                borderRadius: "4px",
                padding: "6px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer"
              }}
            >
              CLEAR SESSION HISTORY
            </button>

            <div style={{ fontSize: "10px", color: isEcoActive ? "#34d399" : "var(--jarvis-cyan)", opacity: 0.8, textAlign: "center" }}>
              {isEcoActive ? "🍃 ECO POWER SAVER ACTIVE" : "⚡ FULL POWER MODE"}
            </div>
          </aside>
        )}

        {/* 3. Main Workspace */}
        <div className="jarvis-workspace" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Urgent Emergency Alert Banner */}
          <UrgentAlertBanner
            alert={urgentAlert}
            onCallSender={(sender) => {
              fetch("http://localhost:8000/api/v1/whatsapp/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ contact: sender, message: "Calling you right now." }),
              });
              setUrgentAlert(null);
            }}
            onDismiss={() => setUrgentAlert(null)}
          />

        {/* 3. Main Content Views */}
        {currentView === "map" ? (
          /* Full Embedded Holographic Cyber Map View */
          <div style={{ flex: 1, height: "100%", overflow: "hidden", display: "flex", flexDirection: "column", marginTop: "4px" }}>
            <BlueLightMapModal
              isEmbedded={true}
              isOpen={true}
              onClose={() => setCurrentView("home")}
              selectedRegion={selectedMapRegion}
              regionTitle={selectedMapTitle}
              searchTrigger={mapSearchTrigger}
              routeTrigger={mapRouteTrigger}
            />
          </div>
        ) : (
          /* Dashboard Grid: When HOME -> Full Central Friday Circle; When CHAT -> Left Monitor | Center Circle | Right Terminal */
          <div style={{ flex: 1, display: "grid", gridTemplateColumns: currentView === "chat" ? "88px 1.3fr 420px" : "1fr", gridTemplateRows: "1fr", gap: "10px", overflow: "hidden" }}>

            {/* Left Column: Concentric System Monitor Panel (Only in CHAT AGENT view) */}
            {currentView === "chat" && (
              <div className="jarvis-glass-card jarvis-panel-box" style={{ height: "100%", display: "flex", flexDirection: "column", padding: "10px" }}>
              <div className="jarvis-panel-title" style={{ marginBottom: "6px" }}>SYSTEM MONITOR</div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "6px", alignItems: "center", justifyItems: "center", flex: 1, overflowY: "auto" }}>
                {/* 1. CPU */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${cpuVal * 3.6}deg, rgba(0,240,255,0.12) ${cpuVal * 3.6}deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">CPU</span>
                        <span className="gauge-val">{cpuVal}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. RAM */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${(ramUsedGb / ramTotalGb) * 360}deg, rgba(0,240,255,0.12) ${(ramUsedGb / ramTotalGb) * 360}deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">RAM</span>
                        <span className="gauge-val-small">{ramUsedGb}/{ramTotalGb}G</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Disk */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#00f0ff 0deg ${(diskUsedGb / diskTotalGb) * 360}deg, rgba(0,240,255,0.12) ${(diskUsedGb / diskTotalGb) * 360}deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">Disk</span>
                        <span className="gauge-val-small">{diskUsedGb}/{diskTotalGb}G</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 4. WiFi Speed */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#38bdf8 0deg 240deg, rgba(56,189,248,0.12) 240deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">WiFi</span>
                        <span className="gauge-val-small">{wifiSpeed}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 5. Fan Speed */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#34d399 0deg 280deg, rgba(52,211,153,0.12) 280deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">Fan</span>
                        <span className="gauge-val-tiny">{fanSpeed}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 6. Memory Frequency */}
                <div className="jarvis-gauge-card" style={{ transform: "scale(0.85)" }}>
                  <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#a78bfa 0deg 300deg, rgba(167,139,250,0.12) 300deg 360deg)` }}>
                    <div className="jarvis-ring-layer-2">
                      <div className="jarvis-gauge-inner">
                        <span className="gauge-title">Mem Freq</span>
                        <span className="gauge-val-tiny">{memFreq}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 7. GPU 0 Load (RTX) */}
                {gpus.filter((g) => g.id === "gpu0").map((gpu) => (
                  <div className="jarvis-gauge-card" key="gpu0_load" style={{ transform: "scale(0.85)" }}>
                    <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#38bdf8 0deg ${gpu.load * 3.6}deg, rgba(56,189,248,0.12) ${gpu.load * 3.6}deg 360deg)` }}>
                      <div className="jarvis-ring-layer-2">
                        <div className="jarvis-gauge-inner">
                          <span className="gauge-title">GPU 0</span>
                          <span className="gauge-val">{gpu.load}%</span>
                          <span className="gpu-subtitle">{gpu.shortName}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* 8. GPU 1 Load (Radeon) */}
                {gpus.filter((g) => g.id === "gpu1").map((gpu) => (
                  <div className="jarvis-gauge-card" key="gpu1_load" style={{ transform: "scale(0.85)" }}>
                    <div className="jarvis-concentric-ring" style={{ background: `conic-gradient(#38bdf8 0deg ${gpu.load * 3.6}deg, rgba(56,189,248,0.12) ${gpu.load * 3.6}deg 360deg)` }}>
                      <div className="jarvis-ring-layer-2">
                        <div className="jarvis-gauge-inner">
                          <span className="gauge-title">GPU 1</span>
                          <span className="gauge-val">{gpu.load}%</span>
                          <span className="gpu-subtitle">{gpu.shortName}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Center Column: Friday Glowing Neural Core Circle */}
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              overflow: "hidden",
              background: "transparent",
              border: "none",
              boxShadow: "none"
            }}
          >

            {/* Ambient Background Radial Glow */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: currentView === "home"
                  ? "radial-gradient(circle at center, rgba(0, 140, 255, 0.12) 0%, rgba(1, 4, 9, 0.3) 70%)"
                  : "radial-gradient(circle at center, rgba(0, 140, 255, 0.06) 0%, rgba(1, 4, 9, 0.15) 70%)",
                pointerEvents: "none",
                zIndex: 1,
              }}
            />
            <canvas ref={centerCanvasRef} width={460} height={460} style={{ position: "absolute", zIndex: 2, pointerEvents: "none" }} />

            {(() => {
              const isBlue = isListening || assistantState === "speaking";
              return (
                <div
                  className="jarvis-sphere-container"
                  onClick={toggleListening}
                  style={{
                    zIndex: 2,
                    transform: currentView === "home" ? "scale(1.2)" : "scale(1.0)",
                    transition: "all 0.3s ease",
                    cursor: "pointer",
                    borderColor: isBlue ? "rgba(0, 240, 255, 0.85)" : "rgba(248, 113, 113, 0.85)",
                    boxShadow: isBlue
                      ? (assistantState === "speaking"
                        ? "0 0 50px rgba(0, 240, 255, 0.6), inset 0 0 25px rgba(0, 119, 255, 0.45)"
                        : "0 0 45px rgba(0, 240, 255, 0.45), inset 0 0 25px rgba(0, 119, 255, 0.35)")
                      : "0 0 50px rgba(239, 68, 68, 0.5), inset 0 0 25px rgba(239, 68, 68, 0.35)",
                    background: isBlue
                      ? "radial-gradient(circle at 50% 50%, rgba(0, 140, 255, 0.22) 0%, rgba(1, 4, 10, 0.95) 75%)"
                      : "radial-gradient(circle at 50% 50%, rgba(239, 68, 68, 0.22) 0%, rgba(1, 4, 10, 0.95) 75%)"
                  }}
                  title={assistantState === "speaking" ? "🔊 Friday Speaking - Click to Pause Mic" : isListening ? "🎙️ Mic ON (Blue) - Click to Turn OFF" : "🔇 Mic OFF (Red) - Click to Turn ON"}
                >
                  <div
                    style={{
                      position: "absolute",
                      inset: "14px",
                      borderRadius: "50%",
                      border: `1px solid ${isBlue ? "rgba(0, 240, 255, 0.45)" : "rgba(248, 113, 113, 0.6)"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: "transparent",
                      transition: "all 0.3s ease"
                    }}
                  >
                    <div style={{ textAlign: "center" }}>
                      <div
                        style={{
                          fontFamily: "'Orbitron', sans-serif",
                          fontWeight: 900,
                          letterSpacing: "2px",
                          color: isBlue ? "#00f0ff" : "#f87171",
                          fontSize: "1.45rem",
                          textShadow: isBlue ? "0 0 16px rgba(0,240,255,0.95)" : "0 0 16px rgba(239,68,68,0.95)",
                          transition: "color 0.3s ease, text-shadow 0.3s ease"
                        }}
                      >
                        {cleanAgentDisplay}
                      </div>
                      <div
                        style={{
                          fontSize: "10px",
                          color: isBlue ? "#00f0ff" : "#f87171",
                          textTransform: "uppercase",
                          letterSpacing: "1.5px",
                          marginTop: "4px",
                          fontWeight: "bold",
                          transition: "color 0.3s ease"
                        }}
                      >
                        {assistantState === "speaking" ? "🔊 SPEAKING" : isThinking ? "⚡ THINKING" : isListening ? "🎙️ LISTENING" : "🔇 MIC OFF"}
                      </div>
                      <div style={{ fontSize: "9px", color: isBlue ? "#94a3b8" : "#fca5a5", fontFamily: "monospace", marginTop: "2px" }}>v3.0.0</div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Right Column: Terminal Stream (Quick Commands & Terminal - Only in CHAT AGENT view) */}
          {currentView === "chat" && (
            <div className="jarvis-glass-card jarvis-panel-box" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
              <div className="jarvis-panel-title">
                <span>QUICK COMMANDS & TERMINAL</span>
                <button
                  onClick={() => setIsTerminalCollapsed((prev) => !prev)}
                  style={{
                    background: "rgba(0, 119, 255, 0.2)",
                    border: "1px solid rgba(0, 240, 255, 0.4)",
                    color: "var(--jarvis-cyan)",
                    width: "20px",
                    height: "20px",
                    borderRadius: "3px",
                    cursor: "pointer",
                    fontSize: "10px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                  }}
                  title={isTerminalCollapsed ? "Expand Terminal" : "Minimize Terminal"}
                >
                  {isTerminalCollapsed ? "▲" : "▼"}
                </button>
              </div>

              {!isTerminalCollapsed && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1, overflow: "hidden" }}>
                  <div style={{ flex: 1, overflowY: "auto", background: "rgba(1, 4, 10, 0.85)", borderRadius: "4px", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px", fontSize: "11px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    {messages.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          padding: "6px 8px",
                          borderRadius: "4px",
                          background: m.sender === "user" ? "rgba(0, 119, 255, 0.18)" : "rgba(0, 240, 255, 0.12)",
                          border: "1px solid rgba(0,240,255,0.1)",
                          position: "relative"
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div style={{ fontSize: "9px", color: "var(--jarvis-cyan)", fontWeight: "bold", textTransform: "uppercase" }}>
                            {m.sender}
                          </div>
                          <button
                            onClick={() => speakSpecificMessage(m.text)}
                            style={{ background: "transparent", border: "none", color: "var(--jarvis-cyan)", cursor: "pointer", fontSize: "10px" }}
                            title="Speak this message"
                          >
                            🔊 Speak
                          </button>
                        </div>
                        <div style={{ fontSize: "11px", whiteSpace: "pre-wrap", color: "#e2e8f0", marginTop: "3px" }}>
                          {m.text}
                        </div>
                      </div>
                    ))}

                    {isThinking && <ProcessingIndicator />}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Staged Files Preview */}
                  {selectedFiles.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", width: "100%", overflowX: "auto", paddingBottom: "2px" }}>
                      <span style={{ fontSize: "9px", color: "var(--jarvis-cyan)", fontWeight: "bold", whiteSpace: "nowrap" }}>
                        STAGED ({selectedFiles.length}/6):
                      </span>
                      {selectedFiles.map((file, index) => (
                        <div
                          key={index}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            background: "rgba(0, 240, 255, 0.15)",
                            border: "1px solid rgba(0, 240, 255, 0.4)",
                            borderRadius: "4px",
                            padding: "2px 6px",
                            fontSize: "10px",
                            color: "#fff",
                            whiteSpace: "nowrap"
                          }}
                        >
                          <span style={{ maxWidth: "80px", overflow: "hidden", textOverflow: "ellipsis" }} title={file.name}>
                            {file.name}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRemoveFile(index)}
                            style={{ background: "transparent", border: "none", color: "#f87171", cursor: "pointer", fontWeight: "bold", fontSize: "10px", padding: "0 2px" }}
                            title="Remove file"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Upload, Input, EXEC, and STOP BUTTON */}
                  <form onSubmit={handleSendMessage} className="jarvis-input-group" style={{ display: "flex", alignItems: "center", gap: "6px", width: "100%", marginTop: "auto" }}>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        background: "rgba(0, 240, 255, 0.15)",
                        border: "1px solid rgba(0, 240, 255, 0.4)",
                        color: "var(--jarvis-cyan)",
                        fontWeight: "bold",
                        fontSize: "12px",
                        padding: "6px 10px",
                        borderRadius: "4px",
                        cursor: "pointer"
                      }}
                      title="Upload Up to 6 Files (PDF, Code, Images, Text)"
                    >
                      📎
                    </button>
                    <input type="file" multiple ref={fileInputRef} onChange={handleFileSelect} style={{ display: "none" }} />

                    <input
                      type="text"
                      placeholder="Type command or query..."
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      className="jarvis-input"
                    />

                    <button type="submit" className="jarvis-btn-exec">
                      EXEC
                    </button>

                    {/* AUTHENTIC STOP EXECUTION BUTTON */}
                    <button
                      type="button"
                      onClick={handleStopExecution}
                      style={{
                        background: "rgba(239, 68, 68, 0.2)",
                        border: "1px solid rgba(239, 68, 68, 0.5)",
                        color: "#f87171",
                        fontWeight: "bold",
                        fontSize: "11px",
                        padding: "6px 10px",
                        borderRadius: "4px",
                        cursor: "pointer"
                      }}
                      title="Halt current execution & silence audio"
                    >
                      STOP
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}

          </div>
        )}
        </div>
      </div>

      {/* 5. 7-Box Settings Configuration Center Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        isBox1Open={isBox1Open}
        setIsBox1Open={setIsBox1Open}
        isBox2Open={isBox2Open}
        setIsBox2Open={setIsBox2Open}
        isBox3Open={isBox3Open}
        setIsBox3Open={setIsBox3Open}
        isBox4Open={isBox4Open}
        setIsBox4Open={setIsBox4Open}
        isBoxScanOpen={isBoxScanOpen}
        setIsBoxScanOpen={setIsBoxScanOpen}
        isBox6Open={isBox6Open}
        setIsBox6Open={setIsBox6Open}
        isBox7Open={isBox7Open}
        setIsBox7Open={setIsBox7Open}
        isBox8Open={isBox8Open}
        setIsBox8Open={setIsBox8Open}
        settingsForm={settingsForm}
        setSettingsForm={setSettingsForm}
        saveUserProfile={saveUserProfile}
        onTestVoice={handleTestVoice}
        masterPasswordInput={masterPasswordInput}
        setMasterPasswordInput={setMasterPasswordInput}
        isLockAuthenticated={isLockAuthenticated}
        verifyMasterPassword={verifyMasterPassword}
        lockMappings={lockMappings}
        setLockMappings={setLockMappings}
        saveLockConfig={saveLockConfig}
        newMasterPasswordInput={newMasterPasswordInput}
        setNewMasterPasswordInput={setNewMasterPasswordInput}
        saveMasterPassword={saveMasterPassword}
        savedPaths={savedPaths}
        addRoute={addRoute}
        setAddRoute={setAddRoute}
        addPathLoc={addPathLoc}
        setAddPathLoc={setAddPathLoc}
        addCustomPath={addCustomPath}
        deleteCustomPath={deleteCustomPath}
        isScanningFeatures={isScanningFeatures}
        featureScanResults={featureScanResults}
        featureSearchQuery={featureSearchQuery}
        setFeatureSearchQuery={setFeatureSearchQuery}
        runFeatureScan={runFeatureScan}
        whatsappSettings={whatsappSettings}
        customAutoReplyText={customAutoReplyText}
        setCustomAutoReplyText={setCustomAutoReplyText}
        whatsappRecipient={whatsappRecipient}
        setWhatsappRecipient={setWhatsappRecipient}
        whatsappMsgText={whatsappMsgText}
        setWhatsappMsgText={setWhatsappMsgText}
        whatsappLogs={whatsappLogs}
        isSendingWhatsApp={isSendingWhatsApp}
        isUpdatingWhatsApp={isUpdatingWhatsApp}
        fetchWhatsAppSettings={fetchWhatsAppSettings}
        updateWhatsAppSettings={updateWhatsAppSettings}
        sendTestWhatsAppMessage={sendTestWhatsAppMessage}
        powerSettings={powerSettings}
        batteryState={batteryState}
        isEcoActive={isEcoActive}
        isUpdatingPower={isUpdatingPower}
        fetchPowerSettings={fetchPowerSettings}
        updatePowerSettings={updatePowerSettings}
        deviceSettings={deviceSettings}
        isUpdatingDevice={isUpdatingDevice}
        fetchDeviceSettings={async () => {
          try {
            const resp = await fetch("http://localhost:8000/api/v1/settings/device-monitoring");
            if (resp.ok) {
              const data = await resp.json();
              if (data.status === "success" && data.settings) {
                setDeviceSettings(data.settings);
              }
            }
          } catch (e) { }
        }}
        updateDeviceSettings={async (enabled: boolean) => {
          setIsUpdatingDevice(true);
          try {
            const resp = await fetch("http://localhost:8000/api/v1/settings/device-monitoring", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ device_monitoring_enabled: enabled }),
            });
            if (resp.ok) {
              const data = await resp.json();
              if (data.status === "success" && data.settings) {
                setDeviceSettings(data.settings);
              }
            }
          } catch (e) {
          } finally {
            setIsUpdatingDevice(false);
          }
        }}
      />

      {/* 6. Interactive Blue Light Holographic Map Modal */}
      <BlueLightMapModal
        isOpen={isMapModalOpen}
        onClose={() => setIsMapModalOpen(false)}
        selectedRegion={selectedMapRegion}
        regionTitle={selectedMapTitle}
        searchTrigger={mapSearchTrigger}
        routeTrigger={mapRouteTrigger}
      />
    </div>
  );
};

export default App;