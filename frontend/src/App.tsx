import React, { useState, useEffect, useRef } from "react";
import "./App.css";

interface Message {
  id: string;
  sender: "user" | "friday" | "system";
  text: string;
  timestamp: string;
  muted?: boolean;
}

interface ConversationItem {
  conversation_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

interface UserProfile {
  name: string;
  agent_name: string;
  age: string;
  email: string;
  city: string;
}

interface GpuInfo {
  id: string;
  label: string;
  shortName: string;
  load: number;
  temp: number;
}

function ProcessingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", margin: "8px 0" }}>
      <div
        className="friday-glow-border"
        style={{
          position: "relative",
          padding: "1.5px",
          borderRadius: "18px",
          borderTopLeftRadius: "3px",
          background: "linear-gradient(270deg, #00f0ff, #0077ff, #1e1e24, #00f0ff)",
          backgroundSize: "400% 400%",
        }}
      >
        <div
          style={{
            backgroundColor: "#121215",
            padding: "8px 16px",
            borderRadius: "18px",
            borderTopLeftRadius: "3px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <div style={{ width: "6px", height: "6px", backgroundColor: "#00f0ff", borderRadius: "50%", animation: "bounce 1.4s infinite ease-in-out both", animationDelay: "-0.32s" }}></div>
            <div style={{ width: "6px", height: "6px", backgroundColor: "#0077ff", borderRadius: "50%", animation: "bounce 1.4s infinite ease-in-out both", animationDelay: "-0.16s" }}></div>
            <div style={{ width: "6px", height: "6px", backgroundColor: "#ffffff", borderRadius: "50%", animation: "bounce 1.4s infinite ease-in-out both" }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

export const App: React.FC = () => {
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
  const [selectedLanguage] = useState<"english">("english");
  const [isGlobalMuted, setIsGlobalMuted] = useState<boolean>(false);

  // Real-Time PC Hardware Metrics States
  const [cpuVal, setCpuVal] = useState<number>(48);
  const [ramUsedGb, setRamUsedGb] = useState<number>(12.2);
  const [ramTotalGb] = useState<number>(15.3);
  const [diskUsedGb, setDiskUsedGb] = useState<number>(353.4);
  const [diskTotalGb, setDiskTotalGb] = useState<number>(446.5);
  const [wifiSpeed, setWifiSpeed] = useState<string>("0.0M");
  const [fanSpeed, setFanSpeed] = useState<string>("2800 RPM");
  const [memFreq, setMemFreq] = useState<string>("4800 MT/s");

  const [gpus, setGpus] = useState<GpuInfo[]>([
    { id: "gpu0", label: "GPU 0", shortName: "RTX 3050", load: 0, temp: 50 },
    { id: "gpu1", label: "GPU 1", shortName: "Radeon", load: 4, temp: 45 }
  ]);

  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isBox1Open, setIsBox1Open] = useState<boolean>(false);
  const [isBox2Open, setIsBox2Open] = useState<boolean>(false);
  const [isBox3Open, setIsBox3Open] = useState<boolean>(false);
  const [isBox4Open, setIsBox4Open] = useState<boolean>(false);
  const [isBoxScanOpen, setIsBoxScanOpen] = useState<boolean>(false);
  const [isBox6Open, setIsBox6Open] = useState<boolean>(false);

  const [whatsappSettings, setWhatsappSettings] = useState<{
    enabled: boolean;
    auto_reply: boolean;
    monitoring_active: boolean;
    custom_auto_reply_message?: string;
    replied_count: number;
    last_activity?: string;
  }>({
    enabled: false,
    auto_reply: true,
    monitoring_active: false,
    custom_auto_reply_message: "",
    replied_count: 0,
  });
  const [customAutoReplyText, setCustomAutoReplyText] = useState<string>("");
  const [whatsappLogs, setWhatsappLogs] = useState<any[]>([]);
  const [whatsappRecipient, setWhatsappRecipient] = useState<string>("");
  const [whatsappMsgText, setWhatsappMsgText] = useState<string>("");
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState<boolean>(false);
  const [isUpdatingWhatsApp, setIsUpdatingWhatsApp] = useState<boolean>(false);

  const [isScanningFeatures, setIsScanningFeatures] = useState<boolean>(false);
  const [featureScanResults, setFeatureScanResults] = useState<any[]>([]);
  const [featureSearchQuery, setFeatureSearchQuery] = useState<string>("");

  const [isSubViewOpen, setIsSubViewOpen] = useState<boolean>(false);
  const [savedPaths, setSavedPaths] = useState<{ route_name: string; path: string }[]>([]);
  const [addRoute, setAddRoute] = useState("");
  const [addPathLoc, setAddPathLoc] = useState("");

  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [tempRouteName, setTempRouteName] = useState("");
  const [tempPathLoc, setTempPathLoc] = useState("");

  const [masterPasswordInput, setMasterPasswordInput] = useState<string>("");
  const [isLockAuthenticated, setIsLockAuthenticated] = useState<boolean>(false);

  const [profile, setProfile] = useState<UserProfile>({
    name: "Harishan",
    agent_name: "Friday",
    age: "",
    email: "",
    city: "",
  });
  const [settingsForm, setSettingsForm] = useState<UserProfile>({
    name: "Harishan",
    agent_name: "Friday",
    age: "",
    email: "",
    city: "",
  });

  const centerCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const freqCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
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
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    profileRef.current = profile;
  }, [profile]);

  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem("friday_active_conv_id", activeConversationId);
    }
  }, [activeConversationId]);

  useEffect(() => {
    if (isGlobalMuted && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
      setAssistantState("idle");
    }
  }, [isGlobalMuted]);

  useEffect(() => {
    fetch("http://localhost:8000/api/profile")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.name) {
          const loaded = {
            name: data.name,
            agent_name: data.agent_name || data.wake_word || "Friday",
            age: data.age || "",
            email: data.email || "",
            city: data.city || "",
          };
          setProfile(loaded);
          setSettingsForm(loaded);
        }
      })
      .catch(() => { });

    fetchConversations();
    fetchWhatsAppSettings();
  }, []);

  const fetchWhatsAppSettings = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings/whatsapp");
      if (res.ok) {
        const data = await res.json();
        const settings = data.settings || data;
        setWhatsappSettings(settings);
        if (settings.custom_auto_reply_message !== undefined) {
          setCustomAutoReplyText(settings.custom_auto_reply_message || "");
        }
      }
      const logsRes = await fetch("http://localhost:8000/api/v1/whatsapp/logs?limit=10");
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        if (logsData && logsData.logs) {
          setWhatsappLogs(logsData.logs);
        }
      }
    } catch (e) {
      console.error("Failed to fetch WhatsApp settings", e);
    }
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
          custom_auto_reply_message: custom_msg !== undefined ? custom_msg : customAutoReplyText
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const settings = data.settings || data;
        setWhatsappSettings(settings);
      }
    } catch (e) {
      alert("Failed to update WhatsApp settings");
    } finally {
      setIsUpdatingWhatsApp(false);
    }
  };

  const sendTestWhatsAppMessage = async () => {
    if (!whatsappRecipient.trim() || !whatsappMsgText.trim()) {
      alert("Please provide both recipient contact name and message text.");
      return;
    }
    setIsSendingWhatsApp(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/whatsapp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact: whatsappRecipient.trim(), recipient: whatsappRecipient.trim(), message: whatsappMsgText.trim() }),
      });
      const data = await res.json();
      if (data.status === "success" || data.success) {
        alert(`✅ WhatsApp message dispatched to "${whatsappRecipient}"!`);
        setWhatsappMsgText("");
        fetchWhatsAppSettings();
      } else {
        alert(`❌ WhatsApp Send failed: ${data.message || data.error || "Unknown error"}`);
      }
    } catch (e) {
      alert("Failed to send WhatsApp message");
    } finally {
      setIsSendingWhatsApp(false);
    }
  };

  // Real-Time PC Telemetry WebSockets Connection
  useEffect(() => {
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

  const fetchConversations = async (targetToSelect?: string) => {
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
    } catch (e) {
      console.warn("Failed to fetch conversations:", e);
    }
  };

  const createNewConversation = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New chat" })
      });
      const data = await res.json();
      if (data && data.status === "success" && data.conversation) {
        const newConv = data.conversation;
        setConversations(prev => [
          {
            conversation_id: newConv.conversation_id,
            title: newConv.title,
            created_at: newConv.created_at,
            updated_at: newConv.updated_at,
            message_count: 0
          },
          ...prev
        ]);
        setActiveConversationId(newConv.conversation_id);
        setMessages([
          {
            id: Math.random().toString(36).substring(2, 9),
            sender: "system",
            text: "NEW SESSION ENGAGED // MEMORY CONNECTED",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          }
        ]);
      }
    } catch {
      const fallbackId = Math.random().toString(36).substring(2, 9);
      setActiveConversationId(fallbackId);
      setConversations(prev => [
        {
          conversation_id: fallbackId,
          title: "New chat",
          created_at: Date.now(),
          updated_at: Date.now(),
          message_count: 0
        },
        ...prev
      ]);
      setMessages([
        {
          id: Math.random().toString(36).substring(2, 9),
          sender: "system",
          text: "NEW SESSION ENGAGED // MEMORY CONNECTED",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        }
      ]);
    }
  };

  const loadConversation = async (convId: string) => {
    setActiveConversationId(convId);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/conversations/${convId}`);
      const data = await res.json();
      if (data && data.status === "success" && data.conversation) {
        const msgs = data.conversation.messages || [];
        if (msgs.length > 0) {
          setMessages(msgs.map((m: any) => ({
            id: m.message_id || Math.random().toString(36).substring(2, 9),
            sender: m.role === "user" ? "user" : m.role === "assistant" ? "friday" : "system",
            text: m.content,
            timestamp: new Date(m.created_at * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          })));
        } else {
          setMessages([
            {
              id: "1",
              sender: "system",
              text: `LOADED SESSION ${convId} // MEMORY SYNCED`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
            }
          ]);
        }
      }
    } catch {
      console.warn("Failed to load conversation messages");
    }
  };

  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await fetch(`http://localhost:8000/api/v1/conversations/${convId}`, { method: "DELETE" });
      const remaining = conversations.filter(c => c.conversation_id !== convId);
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
    if (!newTitle.trim()) return;
    try {
      await fetch(`http://localhost:8000/api/v1/conversations/${convId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim() })
      });
      setConversations(prev => prev.map(c => c.conversation_id === convId ? { ...c, title: newTitle.trim() } : c));
    } catch {
      console.warn("Failed to rename conversation.");
    }
  };

  const fetchPaths = () => {
    fetch("http://localhost:8000/api/add-path")
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.paths)) {
          setSavedPaths(data.paths);
        } else if (Array.isArray(data)) {
          setSavedPaths(data);
        } else {
          setSavedPaths([]);
        }
      })
      .catch(() => {
        setSavedPaths([]);
      });
  };

  useEffect(() => {
    if (isBox3Open) {
      fetchPaths();
    }
  }, [isBox3Open]);

  const sanitizeDisplayMessage = (text: string): string => {
    if (!text || typeof text !== "string") return "Processing complete.";
    let clean = text;
    if (clean.toLowerCase().includes("</think>")) {
      const parts = clean.split(/<\/think>/i);
      clean = parts[parts.length - 1];
    }
    clean = clean.replace(/<think>[\s\S]*?<\/think>/gi, "");
    return clean.trim() || text.trim() || "Ready.";
  };

  const cleanTextForVoice = (rawText?: string): string => {
    if (!rawText || typeof rawText !== "string") return "";
    let text = sanitizeDisplayMessage(rawText);

    // 1. Replace code blocks with a brief natural voice phrase
    text = text.replace(/```[\s\S]*?```/g, " Here is the requested snippet, boss. ");

    // 2. Remove inline code backticks `code` -> code
    text = text.replace(/`([^`]+)`/g, "$1");

    // 3. Remove markdown links [title](url) -> title
    text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

    // 4. Remove bold & italics markdown (**text**, *text*, __text__, _text_)
    text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
    text = text.replace(/\*([^*]+)\*/g, "$1");
    text = text.replace(/__([^_]+)__/g, "$1");
    text = text.replace(/_([^_]+)_/g, "$1");
    text = text.replace(/\*/g, "");

    // 5. Remove headers (### Header -> Header)
    text = text.replace(/^#+\s+/gm, "");

    // 6. Remove table formatting, pipes, double pipes, and dividers
    text = text.replace(/\|/g, " ");
    text = text.replace(/[-=]{3,}/g, " ");

    // 7. Remove double slashes //, bullet dashes, tildes, approximate symbols
    text = text.replace(/\/\//g, " ");
    text = text.replace(/\\\\/g, " ");
    text = text.replace(/^[ \t]*[-•*][ \t]+/gm, " ");
    text = text.replace(/[~≈]/g, " about ");

    // 8. Remove stray symbols that TTS reads aloud awkwardly
    text = text.replace(/[#&<>^$]/g, " ");

    // 9. Normalize whitespace
    return text.replace(/\s+/g, " ").trim();
  };

  const safeStartRecognition = () => {
    if (!recognitionRef.current || !isListeningDesiredRef.current || isSpeakingRef.current || isThinking) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) { }
  };

  const safeStopRecognition = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {
      try { recognitionRef.current.abort(); } catch (err) { }
    }
    setIsListening(false);
  };

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

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
        .replace(new RegExp(`^(?:hey|hi|hello)?\\s*${currentWakeWord}[,:\\s]*`, "i"), "")
        .replace(wakeRegex, "")
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

  const speakSpecificMessage = (text?: string) => {
    if (!text || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    isSpeakingRef.current = true;
    setAssistantState("speaking");
    safeStopRecognition();

    const utterance = new SpeechSynthesisUtterance(cleanTextForVoice(text));
    utterance.rate = 1.05;
    utterance.pitch = 0.95;
    utterance.lang = "en-US";

    const resumeListening = () => {
      isSpeakingRef.current = false;
      setAssistantState("idle");
      if (isListeningDesiredRef.current) setTimeout(safeStartRecognition, 300);
    };

    utterance.onend = resumeListening;
    utterance.onerror = resumeListening;
    window.speechSynthesis.speak(utterance);
  };

  const speakText = (text?: string, forceMuted: boolean = false) => {
    if (forceMuted || isGlobalMuted || !text || !("speechSynthesis" in window)) return;
    speakSpecificMessage(text);
  };

  const handleStopExecution = () => {
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

  const addMessage = async (sender: "user" | "friday" | "system", text: string) => {
    const sanitizedText = sender === "friday" ? sanitizeDisplayMessage(text) : text;
    setMessages((prev) => [...prev, {
      id: Math.random().toString(36).substring(2, 9),
      sender,
      text: sanitizedText || "Ready.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }]);

    if (activeConversationId && sender !== "system") {
      try {
        await fetch(`http://localhost:8000/api/v1/conversations/${activeConversationId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: sender === "user" ? "user" : "assistant", content: sanitizedText })
        });

        if (sender === "user") {
          const currentConv = conversations.find(c => c.conversation_id === activeConversationId);
          if (currentConv && (currentConv.title === "New chat" || currentConv.title.startsWith("Session "))) {
            const newTitle = sanitizedText.slice(0, 30);
            renameConversation(activeConversationId, newTitle);
            setConversations(prev => prev.map(c => c.conversation_id === activeConversationId ? { ...c, title: newTitle } : c));
          }
        }
      } catch (e) { }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputText(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSendMessage();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const fileArr = Array.from(files).slice(0, 6);
      setSelectedFiles(fileArr);
      addMessage("system", `ATTACHED FILE(S): ${fileArr.map(f => f.name).join(", ")}`);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      const fileArr = Array.from(files).slice(0, 6);
      setSelectedFiles(fileArr);
      addMessage("system", `PASTED ${fileArr.length} FILE(S)`);
    }
  };

  const handleRemoveFile = (indexToRemove: number) => {
    const updatedFiles = selectedFiles.filter((_, idx) => idx !== indexToRemove);
    setSelectedFiles(updatedFiles);
    if (updatedFiles.length === 0 && fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSendMessage = async (e?: React.FormEvent, overrideText?: string) => {
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

    try {
      let res;
      if (filesToUpload.length > 0) {
        const formData = new FormData();
        filesToUpload.forEach((f) => formData.append("files", f));
        formData.append("prompt", messagePayload);
        formData.append("language", selectedLanguage);
        formData.append("session_id", activeConversationId || "default");

        res = await fetch("http://localhost:8000/api/analyze-files", {
          method: "POST",
          body: formData,
        });
      } else {
        res = await fetch("http://localhost:8000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: messagePayload, language: selectedLanguage, session_id: activeConversationId || "default" }),
        });
      }

      const data = await res.json();
      const replyText = sanitizeDisplayMessage(data?.response || data?.message || "Command executed.");
      setIsThinking(false);
      setAssistantState("idle");
      await addMessage("friday", replyText);
      if (!isGlobalMuted) speakText(replyText, false);
    } catch {
      setIsThinking(false);
      setAssistantState("idle");
      addMessage("system", "Target connection failure.");
    }
  };

  // Frequency wave animation
  useEffect(() => {
    const canvas = freqCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let step = 0;

    const renderFreq = () => {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;
      const mid = h / 2;

      const isLive = assistantState === "speaking" || isThinking || isListening;

      if (isLive) {
        for (let waveIdx = 0; waveIdx < 2; waveIdx++) {
          ctx.beginPath();
          const points = 35;
          for (let i = 0; i <= points; i++) {
            const x = (w / points) * i;
            const freqMultiplier = waveIdx === 0 ? 0.38 : 0.28;
            const phase = waveIdx === 0 ? step : -step * 0.8;
            const amp = assistantState === "speaking" ? 8 : isThinking ? 5 : 3;

            const y = mid + Math.sin(i * freqMultiplier + phase) * Math.cos(i * 0.15 + phase * 0.5) * amp;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.strokeStyle = waveIdx === 0 ? "#00f0ff" : "#0077ff";
          ctx.lineWidth = waveIdx === 0 ? 1.5 : 1.0;
          ctx.shadowBlur = 6;
          ctx.shadowColor = "#00f0ff";
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
        step += 0.1;
      } else {
        ctx.beginPath();
        ctx.moveTo(0, mid);
        ctx.lineTo(w, mid);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
        ctx.lineWidth = 1.0;
        ctx.stroke();
      }

      animId = requestAnimationFrame(renderFreq);
    };

    renderFreq();
    return () => cancelAnimationFrame(animId);
  }, [assistantState, isThinking, isListening]);

  // Classic Neural Core HUD Ring Renderer
  useEffect(() => {
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
      isThinkingActive: boolean
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
        ctx.strokeStyle = s % 2 === 0 ? `rgba(0, 240, 255, ${alpha})` : `rgba(0, 140, 255, ${alpha * 0.85})`;
        ctx.lineWidth = s % 4 === 0 ? 1.4 : 0.8;

        if (isSpeaking && s % 5 === 0) {
          ctx.shadowColor = "#00f0ff";
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

      drawSegmentedArc(cx, cy, 125, 4, 0.45, "rgba(0, 240, 255, 0.88)", 2.5, angle * 0.6);
      drawSegmentedArc(cx, cy, 112, 24, 0.08, "rgba(0, 140, 255, 0.45)", 1.8, -angle * 0.8);
      drawSegmentedArc(cx, cy, 96, 40, 0.05, "rgba(0, 240, 255, 0.65)", 2.5, angle * 0.5);
      drawSegmentedArc(cx, cy, 76, 8, 0.25, "rgba(0, 240, 255, 0.95)", 1.8, -angle * 1.3);

      const pulse = isSpeaking ? 1.6 : isThinkingRef.current ? 1.25 : 1.0;
      const coreR = Math.max(10, 18 + Math.sin(angle * 6) * (2.5 * pulse));

      const radGrad = ctx.createRadialGradient(cx, cy, 1.5, cx, cy, coreR);
      radGrad.addColorStop(0, "#ffffff");
      radGrad.addColorStop(0.35, "#00f0ff");
      radGrad.addColorStop(0.7, "rgba(0, 120, 255, 0.85)");
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fillStyle = radGrad;
      ctx.shadowColor = "#00f0ff";
      ctx.shadowBlur = isSpeaking ? 28 : 14;
      ctx.fill();
      ctx.shadowBlur = 0;

      drawCircularWaveMesh(cx, cy, isSpeaking, isThinkingRef.current);

      angle += isSpeaking ? 0.025 : 0.01;
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  const cleanAgentDisplay = (profile.agent_name || "FRIDAY").toUpperCase();

  const filteredConversations = conversations.filter(c =>
    (c.title || "").toLowerCase().includes(chatSearchQuery.toLowerCase())
  );

  return (
    <div className="jarvis-root-layout">
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        multiple
        onChange={handleFileSelect}
      />

      {/* 1. Left Sidebar: FRIDAY CHATS */}
      <aside className="jarvis-glass-card jarvis-sidebar" style={{ display: "flex", flexDirection: "column", padding: "12px", gap: "10px", width: "260px" }}>

        {/* Header Title & Minimize Option */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(0, 240, 255, 0.3)", paddingBottom: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "#00f0ff", fontSize: "12px" }}>✦</span>
            <span style={{ fontFamily: "'Orbitron', sans-serif", fontWeight: 900, fontSize: "11px", color: "#00f0ff", letterSpacing: "1px" }}>FRIDAY CHATS</span>
          </div>
          <button
            onClick={() => {
              if (conversations.length > 0) loadConversation(conversations[0].conversation_id);
            }}
            style={{ background: "rgba(0, 240, 255, 0.1)", border: "1px solid rgba(0, 240, 255, 0.3)", color: "var(--jarvis-cyan)", fontSize: "9px", padding: "2px 6px", borderRadius: "3px", cursor: "pointer" }}
          >
            ▼ Minimize
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={createNewConversation}
          style={{ width: "100%", padding: "8px", background: "rgba(0, 240, 255, 0.12)", border: "1px solid rgba(0, 240, 255, 0.4)", borderRadius: "6px", color: "#00f0ff", fontFamily: "'Orbitron', sans-serif", fontSize: "11px", fontWeight: "bold", cursor: "pointer", textAlign: "center" }}
        >
          + New chat
        </button>

        {/* Search Chats Input */}
        <input
          type="text"
          placeholder="Search chats..."
          value={chatSearchQuery}
          onChange={(e) => setChatSearchQuery(e.target.value)}
          style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.3)", borderRadius: "4px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none", width: "100%", boxSizing: "border-box" }}
        />

        {/* Recent Section Title */}
        <div style={{ fontSize: "9px", fontWeight: "bold", color: "rgba(0, 240, 255, 0.75)", textTransform: "uppercase", letterSpacing: "1px", marginTop: "4px" }}>
          RECENT
        </div>

        {/* Chats List */}
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
          {filteredConversations.length === 0 ? (
            <div style={{ fontSize: "10px", color: "#94a3b8", padding: "6px" }}>No chats found.</div>
          ) : (
            filteredConversations.map((c) => {
              const isEditing = editingConvId === c.conversation_id;
              const isActive = activeConversationId === c.conversation_id;
              return (
                <div
                  key={c.conversation_id}
                  onClick={() => loadConversation(c.conversation_id)}
                  style={{
                    padding: "8px 10px",
                    borderRadius: "6px",
                    background: isActive ? "rgba(0, 240, 255, 0.25)" : "rgba(0, 119, 255, 0.08)",
                    border: `1px solid ${isActive ? "rgba(0, 240, 255, 0.6)" : "rgba(0, 240, 255, 0.2)"}`,
                    cursor: "pointer",
                    fontSize: "11px",
                    color: "#e2e8f0",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "6px"
                  }}
                >
                  {isEditing ? (
                    <input
                      type="text"
                      value={editingTitleText}
                      autoFocus
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
                      onClick={(e) => e.stopPropagation()}
                      style={{ background: "#000", border: "1px solid #00f0ff", color: "#fff", flex: 1, fontSize: "11px", padding: "2px 4px", borderRadius: "3px" }}
                    />
                  ) : (
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                      {c.title || "Chat " + c.conversation_id.substring(0, 6)}
                    </span>
                  )}

                  <div style={{ display: "flex", gap: "6px", alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
                    {!isEditing && (
                      <button
                        type="button"
                        onClick={() => {
                          setEditingConvId(c.conversation_id);
                          setEditingTitleText(c.title);
                        }}
                        style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "11px" }}
                        title="Edit title"
                      >
                        ✏️
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => deleteConversation(c.conversation_id, e)}
                      style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "11px" }}
                      title="Delete chat"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="jarvis-workspace">
        {/* 2. Top Header */}
        <header className="jarvis-glass-card jarvis-top-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "11px", fontWeight: 600, color: "#10b981", padding: "3px 10px", borderRadius: "4px", background: "rgba(16, 185, 129, 0.15)", border: "1px solid rgba(16, 185, 129, 0.3)", display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} /> SYSTEM STATUS: OPTIMAL
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: "12px" }}>
            <span style={{ fontFamily: "monospace", color: "#00f0ff" }}>
              {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} — {new Date().toLocaleTimeString()}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.3)", borderRadius: "4px", padding: "4px 8px", fontSize: "11px", color: "#fff", outline: "none", width: "150px" }}
              />

              <button
                onClick={() => {
                  const nextMuted = !isGlobalMuted;
                  setIsGlobalMuted(nextMuted);
                  if (nextMuted && "speechSynthesis" in window) {
                    window.speechSynthesis.cancel();
                    isSpeakingRef.current = false;
                    setAssistantState("idle");
                  }
                }}
                style={{
                  padding: "6px 10px",
                  borderRadius: "4px",
                  background: isGlobalMuted ? "rgba(239, 68, 68, 0.25)" : "rgba(0, 240, 255, 0.15)",
                  border: `1px solid ${isGlobalMuted ? "#f87171" : "rgba(0, 240, 255, 0.4)"}`,
                  color: isGlobalMuted ? "#f87171" : "var(--jarvis-cyan)",
                  cursor: "pointer",
                  fontWeight: "bold",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px"
                }}
                title={isGlobalMuted ? "Speaker Muted (Click to Unmute)" : "Speaker Active (Click to Mute)"}
              >
                {isGlobalMuted ? "🔇 Mute" : "🔊 Audio"}
              </button>

              <button
                onClick={() => setIsSettingsOpen(true)}
                style={{ padding: "6px 10px", borderRadius: "4px", background: "rgba(0, 240, 255, 0.15)", border: "1px solid rgba(0, 240, 255, 0.4)", color: "var(--jarvis-cyan)", cursor: "pointer", fontWeight: "bold" }}
                title="Agent Settings"
              >
                ⚙️
              </button>
            </div>
          </div>
        </header>

        {/* 3. Dashboard Grid Panels */}
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "220px 1.6fr 360px", gridTemplateRows: "1fr", gap: "10px", overflow: "hidden" }}>

          {/* Left Column: Comprehensive System Monitor Panel */}
          <div className="jarvis-glass-card jarvis-panel-box" style={{ height: "100%", display: "flex", flexDirection: "column", padding: "10px" }}>
            <div className="jarvis-panel-title" style={{ marginBottom: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>SYSTEM MONITOR</span>
              <span style={{ fontSize: "8px", color: "#34d399", letterSpacing: "1px" }}>LIVE ●</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 6px", alignItems: "center", justifyItems: "center", flex: 1, overflowY: "auto", paddingBottom: "6px" }}>

              {/* 1. CPU */}
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

              {/* 2. RAM */}
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

              {/* 3. Disk */}
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

              {/* 4. WiFi Speed */}
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

              {/* 5. Fan Speed */}
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

              {/* 6. Memory Frequency */}
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

          {/* Center Column: Classic Neural Core HUD with Map Background strictly behind the circle */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", height: "100%", overflow: "hidden" }}>
            <div className="jarvis-glass-card jarvis-panel-box jarvis-central-core" style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center", padding: "10px", flex: 1.6 }}>
              {/* Map Background Layer restricted strictly to the center neural core area */}
              <div
                style={{
                  position: "absolute",
                  inset: "10px",
                  borderRadius: "12px",
                  backgroundImage: `radial-gradient(circle, rgba(0, 40, 90, 0.35) 0%, rgba(0, 0, 0, 0.9) 80%), url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='400' viewBox='0 0 800 400'%3E%3Cpath fill='%230055ff' fill-opacity='0.25' d='M140 110 c25 -15 50 15 35 30 c-15 15 -45 5 -35 -30 z M310 170 c35 -25 70 25 45 45 c-25 25 -60 -5 -45 -45 z M540 130 c45 -25 80 25 55 55 c-25 35 -75 10 -55 -55 z'/%3E%3C/svg%3E")`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                  pointerEvents: "none",
                  zIndex: 0
                }}
              />
              <canvas ref={centerCanvasRef} width={450} height={450} style={{ position: "absolute", zIndex: 1, pointerEvents: "none" }} />
              <div className="jarvis-sphere-container" style={{ zIndex: 2 }}>
                <div style={{ position: "absolute", inset: "14px", borderRadius: "50%", border: "1px solid rgba(0, 240, 255, 0.3)", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontFamily: "'Orbitron', sans-serif", fontWeight: 900, letterSpacing: "2px", color: "#00f0ff", fontSize: "1.4rem", textShadow: "0 0 14px rgba(0,240,255,0.9)" }}>
                      {cleanAgentDisplay}
                    </div>
                    <div style={{ fontSize: "10px", color: "rgba(0,240,255,0.8)", textTransform: "uppercase", letterSpacing: "1.5px", marginTop: "4px" }}>NEURAL CORE</div>
                    <div style={{ fontSize: "9px", color: "#94a3b8", fontFamily: "monospace", marginTop: "2px" }}>v3.0.0</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Terminal Stream Only */}
          <div className="jarvis-glass-card jarvis-panel-box" style={{ height: "100%" }}>
            <div className="jarvis-panel-title">
              <span>QUICK COMMANDS & TERMINAL</span>
              <button
                onClick={() => setIsTerminalCollapsed((prev) => !prev)}
                style={{ background: "rgba(0, 119, 255, 0.2)", border: "1px solid rgba(0, 240, 255, 0.4)", color: "var(--jarvis-cyan)", width: "20px", height: "20px", borderRadius: "3px", cursor: "pointer", fontSize: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}
                title={isTerminalCollapsed ? "Expand Terminal" : "Minimize Terminal"}
              >
                {isTerminalCollapsed ? "▲" : "▼"}
              </button>
            </div>

            {!isTerminalCollapsed && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1, overflow: "hidden" }}>
                <div style={{ flex: 1, overflowY: "auto", background: "rgba(1, 4, 10, 0.85)", borderRadius: "4px", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px", fontSize: "11px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {messages.map((m) => (
                    <div key={m.id} style={{ padding: "6px 8px", borderRadius: "4px", background: m.sender === 'user' ? 'rgba(0, 119, 255, 0.18)' : 'rgba(0, 240, 255, 0.12)', border: '1px solid rgba(0,240,255,0.1)', position: "relative" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ fontSize: "9px", color: "var(--jarvis-cyan)", fontWeight: "bold", textTransform: "uppercase" }}>{m.sender}</div>
                        <button
                          onClick={() => speakSpecificMessage(m.text)}
                          style={{ background: "transparent", border: "none", color: "var(--jarvis-cyan)", cursor: "pointer", fontSize: "10px" }}
                          title="Speak this message"
                        >
                          🔊 Speak
                        </button>
                      </div>
                      <div style={{ fontSize: "11px", whiteSpace: "pre-wrap", color: "#e2e8f0", marginTop: "3px" }}>{m.text}</div>
                    </div>
                  ))}

                  {isThinking && <ProcessingIndicator />}
                  <div ref={chatEndRef} />
                </div>
              </div>
            )}
          </div>

        </div>

        {/* 4. Bottom Voice Control & Command Bar */}
        <footer className="jarvis-glass-card jarvis-bottom-bar" style={{ display: "flex", flexDirection: "column", height: selectedFiles.length > 0 ? "95px" : "60px", padding: "8px 18px", transition: "height 0.2s" }}>

          {selectedFiles.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", width: "100%", overflowX: "auto", paddingBottom: "4px" }}>
              <span style={{ fontSize: "9px", color: "var(--jarvis-cyan)", fontWeight: "bold", whiteSpace: "nowrap" }}>STAGED ({selectedFiles.length}/6):</span>
              {selectedFiles.map((file, index) => (
                <div key={index} style={{ display: "flex", alignItems: "center", gap: "4px", background: "rgba(0, 240, 255, 0.15)", border: "1px solid rgba(0, 240, 255, 0.4)", borderRadius: "4px", padding: "2px 6px", fontSize: "10px", color: "#fff", whiteSpace: "nowrap" }}>
                  <span style={{ maxWidth: "100px", overflow: "hidden", textOverflow: "ellipsis" }} title={file.name}>{file.name}</span>
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

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: isListening ? "#10b981" : "#64748b", boxShadow: isListening ? "0 0 8px #10b981" : "none", display: "inline-block" }} />
              <span style={{ fontSize: "11px", fontWeight: "bold", color: "var(--jarvis-cyan)", letterSpacing: "1px" }}>TALK TO {cleanAgentDisplay}</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px", height: "20px" }}>
              {[40, 70, 30, 90, 50, 80, 20, 100, 60, 40].map((h, i) => (
                <div key={i} style={{ width: "3px", background: "#00f0ff", borderRadius: "2px", height: `${h}%` }} />
              ))}
            </div>

            <form onSubmit={handleSendMessage} className="jarvis-input-group">
              <button
                type="button"
                onClick={toggleListening}
                style={{
                  padding: "6px 10px",
                  borderRadius: "4px",
                  background: isListening ? "rgba(16, 185, 129, 0.25)" : "rgba(0, 240, 255, 0.15)",
                  border: `1px solid ${isListening ? "#10b981" : "rgba(0, 240, 255, 0.4)"}`,
                  color: isListening ? "#34d399" : "var(--jarvis-cyan)",
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: "11px",
                  whiteSpace: "nowrap"
                }}
                title={isListening ? "Voice Active" : "Click to Speak"}
              >
                {isListening ? "🎙️ Active" : "🎙️ Speak"}
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                style={{ background: "rgba(0, 240, 255, 0.15)", border: "1px solid rgba(0, 240, 255, 0.4)", color: "var(--jarvis-cyan)", fontWeight: "bold", fontSize: "12px", padding: "6px 10px", borderRadius: "4px", cursor: "pointer" }}
                title="Upload Up to 6 Files"
              >
                📎
              </button>

              <input
                type="text"
                placeholder="Type command or query..."
                value={inputText}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                className="jarvis-input"
              />
              <button type="submit" className="jarvis-btn-exec">
                EXEC
              </button>
              <button
                type="button"
                onClick={handleStopExecution}
                style={{ background: "rgba(239, 68, 68, 0.2)", border: "1px solid rgba(239, 68, 68, 0.5)", color: "#f87171", fontWeight: "bold", fontSize: "11px", padding: "6px 10px", borderRadius: "4px", cursor: "pointer" }}
              >
                STOP
              </button>
            </form>
          </div>
        </footer>
      </div>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", padding: "16px" }}>
          <div className="jarvis-glass-card" style={{ width: "600px", maxHeight: "90vh", overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px", border: "1px solid rgba(0,240,255,0.5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(0,240,255,0.3)", paddingBottom: "8px" }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "13px", fontWeight: "bold", color: "#00f0ff" }}>AGENT SETTINGS // CONFIGURATION</span>
              <button onClick={() => setIsSettingsOpen(false)} style={{ background: "transparent", border: "none", color: "#00f0ff", fontSize: "14px", cursor: "pointer", fontWeight: "bold" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
              <div className="jarvis-glass-card" style={{ padding: "10px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => setIsBox1Open(!isBox1Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>1. PROFILE {isBox1Open ? "▼" : "▶"}</div>
                </div>
                {isBox1Open && (
                  <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <input type="text" placeholder="Name" value={settingsForm.name} onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                    <input type="text" placeholder="Age" value={settingsForm.age} onChange={(e) => setSettingsForm({ ...settingsForm, age: e.target.value })} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                    <input type="email" placeholder="Email" value={settingsForm.email} onChange={(e) => setSettingsForm({ ...settingsForm, email: e.target.value })} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                    <input type="text" placeholder="City" value={settingsForm.city} onChange={(e) => setSettingsForm({ ...settingsForm, city: e.target.value })} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                    <button onClick={async () => {
                      try {
                        await fetch("http://localhost:8000/api/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settingsForm) });
                        setProfile(settingsForm);
                        alert("Profile updated!");
                      } catch { alert("Failed."); }
                    }} style={{ alignSelf: "flex-end", padding: "4px 8px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer" }}>SAVE</button>
                  </div>
                )}
              </div>

              <div className="jarvis-glass-card" style={{ padding: "10px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => setIsBox2Open(!isBox2Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>2. AGENT PROFILE {isBox2Open ? "▼" : "▶"}</div>
                </div>
                {isBox2Open && (
                  <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <input type="text" value={settingsForm.agent_name} onChange={(e) => setSettingsForm({ ...settingsForm, agent_name: e.target.value })} placeholder="Agent Name (e.g. FRIDAY)" style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                    <button onClick={async () => {
                      try {
                        await fetch("http://localhost:8000/api/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settingsForm) });
                        setProfile(settingsForm);
                        alert("Agent updated!");
                      } catch { alert("Failed."); }
                    }} style={{ alignSelf: "flex-end", padding: "4px 8px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer" }}>SAVE</button>
                  </div>
                )}
              </div>

              <div className="jarvis-glass-card" style={{ padding: "10px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => setIsBox3Open(!isBox3Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>3. ADD & VIEW PATHS {isBox3Open ? "▼" : "▶"}</div>
                </div>
                {isBox3Open && (
                  <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", paddingBottom: "8px", borderBottom: "1px solid rgba(0,240,255,0.2)" }}>
                      <span style={{ fontSize: "10px", color: "var(--jarvis-cyan)", fontWeight: "bold" }}>Add New Route</span>
                      <input type="text" placeholder="Route Name" value={addRoute} onChange={(e) => setAddRoute(e.target.value)} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                      <input type="text" placeholder="Path Location" value={addPathLoc} onChange={(e) => setAddPathLoc(e.target.value)} style={{ background: "#01040a", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                      <button onClick={async () => {
                        try {
                          await fetch("http://localhost:8000/api/add-path", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ route_name: addRoute.trim(), path: addPathLoc.trim() }) });
                          alert("Path added!");
                          setAddRoute(""); setAddPathLoc(""); fetchPaths();
                        } catch { alert("Failed."); }
                      }} style={{ alignSelf: "flex-end", padding: "4px 8px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer" }}>ADD PATH</button>
                    </div>

                    <div>
                      <div onClick={() => { const next = !isSubViewOpen; setIsSubViewOpen(next); if (next) fetchPaths(); }} style={{ cursor: "pointer", fontSize: "10px", color: "#00f0ff", fontWeight: "bold", padding: "4px 0" }}>
                        VIEW SAVED PATHS {isSubViewOpen ? "▼" : "▶"}
                      </div>
                      {isSubViewOpen && (
                        <div style={{ marginTop: "6px", maxHeight: "120px", overflowY: "auto" }}>
                          {savedPaths.length === 0 ? (
                            <div style={{ fontSize: "10px", color: "#8ab4f8" }}>No routes saved.</div>
                          ) : (
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10px", color: "#e2e8f0" }}>
                              <tbody>
                                {savedPaths.map((item, idx) => {
                                  const isRowEditing = editingIndex === idx;
                                  return (
                                    <tr key={idx} style={{ borderBottom: "1px solid rgba(0,240,255,0.1)" }}>
                                      <td style={{ padding: "4px" }}>
                                        {isRowEditing ? (
                                          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                            <input type="text" value={tempRouteName} onChange={(e) => setTempRouteName(e.target.value)} style={{ background: "#010409", border: "1px solid #00f0ff", color: "#fff", padding: "2px" }} />
                                            <input type="text" value={tempPathLoc} onChange={(e) => setTempPathLoc(e.target.value)} style={{ background: "#010409", border: "1px solid #00f0ff", color: "#fff", padding: "2px" }} />
                                          </div>
                                        ) : (
                                          <div><strong>{item.route_name}:</strong> <span style={{ color: "#8ab4f8" }}>{item.path}</span></div>
                                        )}
                                      </td>
                                      <td style={{ padding: "4px", textAlign: "right" }}>
                                        {isRowEditing ? (
                                          <button onClick={async () => {
                                            try {
                                              await fetch("http://localhost:8000/api/add-path", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ route_name: tempRouteName.trim(), path: tempPathLoc.trim() }) });
                                              setEditingIndex(null); fetchPaths();
                                            } catch { alert("Error"); }
                                          }} style={{ background: "#00f0ff", color: "#010409", border: "none", padding: "2px 6px", fontWeight: "bold" }}>SAVE</button>
                                        ) : (
                                          <button onClick={() => { setEditingIndex(idx); setTempRouteName(item.route_name); setTempPathLoc(item.path); }} style={{ background: "transparent", border: "none", color: "#00f0ff", cursor: "pointer" }}>✏️</button>
                                        )}
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="jarvis-glass-card" style={{ padding: "10px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => setIsBox4Open(!isBox4Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>4. LOCK SCREEN SECURITY {isBox4Open ? "▼" : "▶"}</div>
                </div>
                {isBox4Open && (
                  <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    {!isLockAuthenticated ? (
                      <>
                        <input type="password" placeholder="Master Password" value={masterPasswordInput} onChange={(e) => setMasterPasswordInput(e.target.value)} style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", padding: "6px", color: "#fff", borderRadius: "4px" }} />
                        <button onClick={async () => {
                          try {
                            const res = await fetch("http://localhost:8000/api/security/verify-master", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: masterPasswordInput }) });
                            const data = await res.json();
                            if (data.status === "success") { setIsLockAuthenticated(true); alert("Unlocked!"); }
                            else { alert("Incorrect password."); }
                          } catch { alert("Error."); }
                        }} style={{ alignSelf: "flex-end", padding: "4px 8px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer" }}>UNLOCK</button>
                      </>
                    ) : (
                      <div style={{ color: "#38bdf8", fontSize: "11px" }}>Security Mappings Unlocked and Active.</div>
                    )}
                  </div>
                )}
              </div>

              <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => setIsBoxScanOpen(!isBoxScanOpen)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>5. SCAN AGENT FEATURES (100% HEALTH CHECK)</span>
                    {featureScanResults.length > 0 && (
                      <span style={{ fontSize: "9px", background: "rgba(52, 211, 153, 0.2)", border: "1px solid #34d399", color: "#34d399", padding: "1px 6px", borderRadius: "10px" }}>
                        {featureScanResults.filter(r => r.status === 'working').length}/{featureScanResults.length} OPERATIONAL
                      </span>
                    )}
                  </div>
                  <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBoxScanOpen ? "▼" : "▶"}</span>
                </div>

                {isBoxScanOpen && (
                  <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <button
                        onClick={async () => {
                          setIsScanningFeatures(true);
                          try {
                            const res = await fetch("http://localhost:8000/api/v1/settings/scan-agent-features", { method: "POST" });
                            const data = await res.json();
                            if (data && data.results) setFeatureScanResults(data.results);
                          } catch {
                            alert("Diagnostic scan failed.");
                          } finally {
                            setIsScanningFeatures(false);
                          }
                        }}
                        disabled={isScanningFeatures}
                        style={{
                          flex: 1,
                          padding: "8px 12px",
                          background: isScanningFeatures ? "rgba(0, 240, 255, 0.2)" : "#00f0ff",
                          color: isScanningFeatures ? "#00f0ff" : "#010409",
                          fontWeight: "bold",
                          fontFamily: "'Orbitron', sans-serif",
                          fontSize: "10px",
                          letterSpacing: "1px",
                          borderRadius: "4px",
                          border: isScanningFeatures ? "1px dashed #00f0ff" : "none",
                          cursor: isScanningFeatures ? "wait" : "pointer",
                          transition: "all 0.2s"
                        }}
                      >
                        {isScanningFeatures ? "⚡ EXECUTING COMPLETE SYSTEM DIAGNOSTICS..." : "▶ RUN 100% FULL AGENT FEATURE SCAN"}
                      </button>
                    </div>

                    {featureScanResults.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {/* Overall Health Score Bar */}
                        <div style={{ background: "rgba(1, 4, 10, 0.95)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "10px", borderRadius: "6px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px", fontSize: "10px" }}>
                            <span style={{ color: "#8ab4f8", fontWeight: "bold" }}>DIAGNOSTIC STATUS:</span>
                            <span style={{ color: "#34d399", fontWeight: "bold", fontFamily: "'Orbitron', sans-serif" }}>
                              {Math.round((featureScanResults.filter(r => r.status === 'working').length / featureScanResults.length) * 100)}% OPERATIONAL ({featureScanResults.filter(r => r.status === 'working').length}/{featureScanResults.length} PROBES PASSED)
                            </span>
                          </div>
                          <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                            <div
                              style={{
                                width: `${(featureScanResults.filter(r => r.status === 'working').length / featureScanResults.length) * 100}%`,
                                height: "100%",
                                background: "linear-gradient(90deg, #00f0ff 0%, #34d399 100%)",
                                boxShadow: "0 0 10px #34d399"
                              }}
                            />
                          </div>
                        </div>

                        {/* Search / Filter */}
                        <input
                          type="text"
                          placeholder="Filter diagnostics (e.g. CPU, LLM, Filesystem, Memory, Audio)..."
                          value={featureSearchQuery}
                          onChange={(e) => setFeatureSearchQuery(e.target.value)}
                          style={{
                            background: "#010409",
                            border: "1px solid rgba(0, 240, 255, 0.3)",
                            borderRadius: "4px",
                            padding: "6px 8px",
                            fontSize: "10px",
                            color: "#fff",
                            outline: "none"
                          }}
                        />

                        {/* Results Grid List */}
                        <div style={{ maxHeight: "220px", overflowY: "auto", fontSize: "10px", background: "#010409", padding: "8px", borderRadius: "6px", border: "1px solid rgba(0,240,255,0.15)", display: "flex", flexDirection: "column", gap: "6px" }}>
                          {featureScanResults
                            .filter(r => !featureSearchQuery || r.feature.toLowerCase().includes(featureSearchQuery.toLowerCase()) || (r.details && r.details.toLowerCase().includes(featureSearchQuery.toLowerCase())))
                            .map((r, i) => (
                              <div
                                key={i}
                                style={{
                                  display: "flex",
                                  flexDirection: "column",
                                  gap: "2px",
                                  padding: "6px 8px",
                                  borderRadius: "4px",
                                  background: r.status === 'working' ? "rgba(52, 211, 153, 0.05)" : "rgba(239, 68, 68, 0.1)",
                                  border: `1px solid ${r.status === 'working' ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.4)"}`
                                }}
                              >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <span style={{ fontWeight: "bold", color: "#e2e8f0" }}>{r.feature}</span>
                                  <span
                                    style={{
                                      fontSize: "8.5px",
                                      fontWeight: "bold",
                                      padding: "1px 6px",
                                      borderRadius: "3px",
                                      background: r.status === 'working' ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.25)",
                                      color: r.status === 'working' ? "#34d399" : "#f87171",
                                      border: `1px solid ${r.status === 'working' ? "#34d399" : "#f87171"}`
                                    }}
                                  >
                                    {r.status === 'working' ? "100% OK" : "FAILED"}
                                  </span>
                                </div>
                                {r.details && (
                                  <div style={{ color: "#94a3b8", fontSize: "9px" }}>{r.details}</div>
                                )}
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Box 6: WhatsApp Auto-Monitor & Agent Plugin */}
              <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
                <div onClick={() => { setIsBox6Open(!isBox6Open); fetchWhatsAppSettings(); }} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>6. WHATSAPP AUTO-MONITOR & AGENT PLUGIN</span>
                    <span style={{
                      fontSize: "9px",
                      padding: "1px 6px",
                      borderRadius: "10px",
                      background: whatsappSettings.monitoring_active ? "rgba(52, 211, 153, 0.2)" : "rgba(148, 163, 184, 0.2)",
                      border: `1px solid ${whatsappSettings.monitoring_active ? "#34d399" : "#64748b"}`,
                      color: whatsappSettings.monitoring_active ? "#34d399" : "#94a3b8"
                    }}>
                      {whatsappSettings.monitoring_active ? "🟢 MONITORING ACTIVE" : "⚪ STANDBY"}
                    </span>
                  </div>
                  <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox6Open ? "▼" : "▶"}</span>
                </div>

                {isBox6Open && (
                  <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    {/* Controls Row */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                      {/* Master Monitoring Switch */}
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px 10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div>
                          <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>Background Monitor</div>
                          <div style={{ fontSize: "8.5px", color: "#94a3b8" }}>Windows Toast Listener</div>
                        </div>
                        <button
                          onClick={() => updateWhatsAppSettings(!whatsappSettings.enabled, whatsappSettings.auto_reply)}
                          disabled={isUpdatingWhatsApp}
                          style={{
                            padding: "4px 10px",
                            borderRadius: "4px",
                            fontWeight: "bold",
                            fontSize: "10px",
                            fontFamily: "'Orbitron', sans-serif",
                            cursor: isUpdatingWhatsApp ? "wait" : "pointer",
                            background: whatsappSettings.enabled ? "linear-gradient(135deg, #10b981, #059669)" : "#334155",
                            color: "#fff",
                            border: `1px solid ${whatsappSettings.enabled ? "#34d399" : "#475569"}`,
                            boxShadow: whatsappSettings.enabled ? "0 0 8px rgba(52, 211, 153, 0.4)" : "none"
                          }}
                        >
                          {whatsappSettings.enabled ? "ON" : "OFF"}
                        </button>
                      </div>

                      {/* AI Auto-Reply Switch */}
                      <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px 10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div>
                          <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>AI Auto-Reply</div>
                          <div style={{ fontSize: "8.5px", color: "#94a3b8" }}>Autonomous Response</div>
                        </div>
                        <button
                          onClick={() => updateWhatsAppSettings(whatsappSettings.enabled, !whatsappSettings.auto_reply)}
                          disabled={isUpdatingWhatsApp}
                          style={{
                            padding: "4px 10px",
                            borderRadius: "4px",
                            fontWeight: "bold",
                            fontSize: "10px",
                            fontFamily: "'Orbitron', sans-serif",
                            cursor: isUpdatingWhatsApp ? "wait" : "pointer",
                            background: whatsappSettings.auto_reply ? "linear-gradient(135deg, #00f0ff, #0284c7)" : "#334155",
                            color: whatsappSettings.auto_reply ? "#010409" : "#fff",
                            border: `1px solid ${whatsappSettings.auto_reply ? "#00f0ff" : "#475569"}`,
                            boxShadow: whatsappSettings.auto_reply ? "0 0 8px rgba(0, 240, 255, 0.4)" : "none"
                          }}
                        >
                          {whatsappSettings.auto_reply ? "ON" : "OFF"}
                        </button>
                      </div>
                    </div>

                    {/* Telemetry & Stats */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", background: "rgba(1, 4, 10, 0.95)", border: "1px solid rgba(0, 240, 255, 0.2)", padding: "8px", borderRadius: "6px" }}>
                      <div>
                        <div style={{ fontSize: "8.5px", color: "#8ab4f8", textTransform: "uppercase" }}>Auto-Replies Dispatched</div>
                        <div style={{ fontSize: "14px", fontWeight: "bold", color: "#34d399", fontFamily: "'Orbitron', sans-serif" }}>{whatsappSettings.replied_count || 0}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "8.5px", color: "#8ab4f8", textTransform: "uppercase" }}>Last Monitored Event</div>
                        <div style={{ fontSize: "10px", color: "#e2e8f0", marginTop: "3px" }}>
                          {whatsappSettings.last_activity ? new Date(whatsappSettings.last_activity).toLocaleTimeString() : "No events yet"}
                        </div>
                      </div>
                    </div>

                    {/* Custom Auto-Reply Message Rule */}
                    <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "10px", borderRadius: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ fontSize: "10px", fontWeight: "bold", color: "#00f0ff", fontFamily: "'Orbitron', sans-serif" }}>CUSTOM AUTO-REPLY MESSAGE</div>
                        {whatsappSettings.custom_auto_reply_message && (
                          <span style={{ fontSize: "8.5px", color: "#34d399", background: "rgba(52, 211, 153, 0.15)", padding: "1px 6px", borderRadius: "8px" }}>CUSTOM SET</span>
                        )}
                      </div>
                      <div style={{ fontSize: "8.5px", color: "#94a3b8" }}>When messages arrive, Friday will reply with this exact text:</div>
                      <input
                        type="text"
                        placeholder="e.g. I will call you later on."
                        value={customAutoReplyText}
                        onChange={(e) => setCustomAutoReplyText(e.target.value)}
                        style={{
                          background: "#010409",
                          border: "1px solid rgba(0, 240, 255, 0.3)",
                          borderRadius: "4px",
                          padding: "6px 8px",
                          fontSize: "10px",
                          color: "#fff",
                          outline: "none"
                        }}
                      />
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          onClick={() => updateWhatsAppSettings(whatsappSettings.enabled, whatsappSettings.auto_reply, customAutoReplyText.trim())}
                          disabled={isUpdatingWhatsApp}
                          style={{
                            flex: 1,
                            padding: "4px 8px",
                            background: "linear-gradient(135deg, #00f0ff, #0284c7)",
                            color: "#010409",
                            fontWeight: "bold",
                            fontFamily: "'Orbitron', sans-serif",
                            fontSize: "9px",
                            borderRadius: "4px",
                            border: "none",
                            cursor: isUpdatingWhatsApp ? "wait" : "pointer"
                          }}
                        >
                          💾 SAVE CUSTOM AUTO-REPLY
                        </button>
                        {customAutoReplyText && (
                          <button
                            onClick={() => {
                              setCustomAutoReplyText("");
                              updateWhatsAppSettings(whatsappSettings.enabled, whatsappSettings.auto_reply, "");
                            }}
                            disabled={isUpdatingWhatsApp}
                            style={{
                              padding: "4px 8px",
                              background: "rgba(239, 68, 68, 0.2)",
                              color: "#f87171",
                              fontWeight: "bold",
                              fontSize: "9px",
                              borderRadius: "4px",
                              border: "1px solid rgba(239, 68, 68, 0.4)",
                              cursor: "pointer"
                            }}
                          >
                            RESET
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Quick Dispatch / Test Send */}
                    <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "10px", borderRadius: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ fontSize: "10px", fontWeight: "bold", color: "#00f0ff", fontFamily: "'Orbitron', sans-serif" }}>TEST QUICK AGENT DISPATCH</div>
                      <input
                        type="text"
                        placeholder="Recipient Name (e.g. John, Mom, Work)..."
                        value={whatsappRecipient}
                        onChange={(e) => setWhatsappRecipient(e.target.value)}
                        style={{
                          background: "#010409",
                          border: "1px solid rgba(0, 240, 255, 0.3)",
                          borderRadius: "4px",
                          padding: "6px 8px",
                          fontSize: "10px",
                          color: "#fff",
                          outline: "none"
                        }}
                      />
                      <input
                        type="text"
                        placeholder="Message content..."
                        value={whatsappMsgText}
                        onChange={(e) => setWhatsappMsgText(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") sendTestWhatsAppMessage(); }}
                        style={{
                          background: "#010409",
                          border: "1px solid rgba(0, 240, 255, 0.3)",
                          borderRadius: "4px",
                          padding: "6px 8px",
                          fontSize: "10px",
                          color: "#fff",
                          outline: "none"
                        }}
                      />
                      <button
                        onClick={sendTestWhatsAppMessage}
                        disabled={isSendingWhatsApp}
                        style={{
                          padding: "6px 12px",
                          background: isSendingWhatsApp ? "rgba(0, 240, 255, 0.2)" : "#00f0ff",
                          color: isSendingWhatsApp ? "#00f0ff" : "#010409",
                          fontWeight: "bold",
                          fontFamily: "'Orbitron', sans-serif",
                          fontSize: "10px",
                          letterSpacing: "0.5px",
                          borderRadius: "4px",
                          border: "none",
                          cursor: isSendingWhatsApp ? "wait" : "pointer",
                          transition: "all 0.2s"
                        }}
                      >
                        {isSendingWhatsApp ? "⚡ DISPATCHING TO WHATSAPP DESKTOP..." : "▶ SEND WHATSAPP MESSAGE"}
                      </button>
                    </div>

                    {/* Activity Logs */}
                    {whatsappLogs.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        <div style={{ fontSize: "9px", color: "#8ab4f8", fontWeight: "bold", textTransform: "uppercase" }}>Recent WhatsApp Activity Stream:</div>
                        <div style={{ maxHeight: "120px", overflowY: "auto", fontSize: "9px", background: "#010409", padding: "6px", borderRadius: "4px", border: "1px solid rgba(0,240,255,0.15)", display: "flex", flexDirection: "column", gap: "4px" }}>
                          {whatsappLogs.slice(0, 5).map((log, idx) => (
                            <div key={idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "3px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", color: "#38bdf8" }}>
                                <span>{log.sender ? `📩 From: ${log.sender}` : `📤 To: ${log.recipient}`}</span>
                                <span style={{ color: "#64748b" }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                              </div>
                              <div style={{ color: "#e2e8f0" }}>{log.message || log.text}</div>
                              {log.reply && (
                                <div style={{ color: "#34d399", paddingLeft: "8px", fontStyle: "italic" }}>🤖 Auto-Reply: {log.reply}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

            </div>

            <button
              type="button"
              onClick={() => setIsSettingsOpen(false)}
              style={{ marginTop: "8px", padding: "6px", background: "#1e293b", color: "#e2e8f0", borderRadius: "4px", fontWeight: "bold", border: "none", cursor: "pointer" }}
            >
              CLOSE SETTINGS
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;