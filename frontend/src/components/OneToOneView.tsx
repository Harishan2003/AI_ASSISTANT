import React, { useEffect, useRef, useState } from "react";
import type { UserProfile } from "../types/assistant";

interface OneToOneMessage {
  id: string;
  sender: "user" | "friday" | "system";
  text: string;
  timestamp: string;
}

interface OneToOneViewProps {
  onClose: () => void;
  profile: UserProfile;
  assistantState: "idle" | "listening" | "speaking" | "thinking";
  isThinking: boolean;
  isListening: boolean;
  isGlobalMuted: boolean;
  onSendMessage: (text: string) => void;
  onStopExecution: () => void;
  onToggleMic: () => void;
  messages: OneToOneMessage[];
  onClearHistory: () => void;
  latestUserTranscript?: string;
  latestFridayResponse?: string;
}

export const OneToOneView: React.FC<OneToOneViewProps> = ({
  onClose,
  profile,
  assistantState,
  isThinking,
  isListening,
  isGlobalMuted,
  onSendMessage,
  onStopExecution,
  onToggleMic,
  messages,
  onClearHistory,
  latestUserTranscript,
  latestFridayResponse,
}) => {
  const [inputText, setInputText] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const agentName = profile.agent_profile?.agent_name || profile.agent_name || "Friday";
  const userName = profile.profile?.name || profile.name || "Harishan";

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isThinking]);

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  const isSpeaking = assistantState === "speaking";
  const isThinkingActive = isThinking || assistantState === "thinking";
  const isMicActive = isListening || assistantState === "listening";

  let statusText = "Ready to talk";
  let statusColor = "#38bdf8";
  let glowColor = "rgba(0, 240, 255, 0.4)";
  let sphereGradient = "radial-gradient(circle at 50% 50%, rgba(0, 140, 255, 0.25) 0%, rgba(1, 4, 10, 0.95) 75%)";
  let sphereBorder = "rgba(0, 240, 255, 0.85)";

  if (isThinkingActive) {
    statusText = `${agentName} is thinking...`;
    statusColor = "#facc15";
    glowColor = "rgba(250, 204, 21, 0.55)";
    sphereGradient = "radial-gradient(circle at 50% 50%, rgba(234, 179, 8, 0.3) 0%, rgba(14, 11, 2, 0.96) 75%)";
    sphereBorder = "rgba(250, 204, 21, 0.95)";
  } else if (isSpeaking) {
    statusText = `${agentName} is speaking...`;
    statusColor = "#ec4899";
    glowColor = "rgba(236, 72, 153, 0.55)";
    sphereGradient = "radial-gradient(circle at 50% 50%, rgba(236, 72, 153, 0.3) 0%, rgba(18, 4, 14, 0.95) 75%)";
    sphereBorder = "rgba(244, 114, 182, 0.95)";
  } else if (isMicActive) {
    statusText = "Listening to you... (Speak freely without wake word)";
    statusColor = "#34d399";
    glowColor = "rgba(52, 211, 153, 0.55)";
    sphereGradient = "radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.28) 0%, rgba(2, 16, 10, 0.95) 75%)";
    sphereBorder = "rgba(52, 211, 153, 0.95)";
  }

  return (
    <div
      style={{
        flex: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "radial-gradient(ellipse at center, rgba(15, 23, 42, 0.8) 0%, #030712 100%)",
        borderRadius: "10px",
        border: "1px solid rgba(236, 72, 153, 0.3)",
        boxShadow: "0 0 30px rgba(236, 72, 153, 0.15), inset 0 0 20px rgba(0, 0, 0, 0.6)",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* 1. Header Bar */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 18px",
          background: "rgba(3, 7, 18, 0.85)",
          borderBottom: "1px solid rgba(236, 72, 153, 0.25)",
          backdropFilter: "blur(12px)",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              background: statusColor,
              boxShadow: `0 0 10px ${statusColor}`,
              animation: isSpeaking || isMicActive ? "pulse 1.5s infinite" : "none",
            }}
          />
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontSize: "13px",
                  fontWeight: "bold",
                  letterSpacing: "1.5px",
                  background: "linear-gradient(90deg, #f472b6, #38bdf8)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                ONE TO ONE // PERSON-TO-PERSON CONVERSATION
              </span>
              <span
                style={{
                  fontSize: "9px",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: "rgba(52, 211, 153, 0.15)",
                  border: "1px solid #34d399",
                  color: "#34d399",
                  fontWeight: "bold",
                  letterSpacing: "0.5px",
                }}
              >
                NO WAKE WORD NEEDED
              </span>
              {isGlobalMuted && (
                <span
                  style={{
                    fontSize: "9px",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1px solid #f87171",
                    color: "#f87171",
                    fontWeight: "bold",
                  }}
                >
                  MUTED
                </span>
              )}
            </div>
            <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "1px" }}>
              Continuous conversational stream with {agentName} • Full memory of chat &amp; personal tasks active
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={onClearHistory}
            style={{
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.35)",
              color: "#f87171",
              borderRadius: "6px",
              padding: "5px 10px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            title="Clear One-to-One conversation memory"
          >
            🗑️ CLEAR STREAM
          </button>

          <button
            onClick={onClose}
            style={{
              background: "rgba(236, 72, 153, 0.15)",
              border: "1px solid rgba(236, 72, 153, 0.4)",
              color: "#f472b6",
              borderRadius: "6px",
              padding: "5px 12px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            ✕ EXIT MODE
          </button>
        </div>
      </header>

      {/* 2. Main Content Body: Grid Layout */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "1.1fr 0.9fr",
          gap: "16px",
          padding: "16px",
          overflow: "hidden",
        }}
      >
        {/* Left Column: Interactive Face-to-Face Persona Core */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(1, 4, 9, 0.6)",
            borderRadius: "10px",
            border: "1px solid rgba(236, 72, 153, 0.2)",
            padding: "20px",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Top Status Capsule */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(3, 7, 18, 0.75)",
              padding: "6px 16px",
              borderRadius: "20px",
              border: `1px solid ${statusColor}`,
              boxShadow: `0 0 14px ${glowColor}`,
            }}
          >
            <span style={{ fontSize: "14px" }}>
              {isThinkingActive ? "🧠" : isSpeaking ? "🔊" : isMicActive ? "🎙️" : "💬"}
            </span>
            <span style={{ fontSize: "11px", fontWeight: "bold", color: statusColor, letterSpacing: "0.5px" }}>
              {statusText}
            </span>
          </div>

          {/* Central Holographic Sphere & Wave Visualizer */}
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "280px",
              height: "280px",
              margin: "auto",
            }}
          >
            {/* Outer Glowing Ripple Rings */}
            {(isSpeaking || isMicActive || isThinkingActive) && (
              <>
                <div
                  style={{
                    position: "absolute",
                    width: "260px",
                    height: "260px",
                    borderRadius: "50%",
                    border: `2px dashed ${statusColor}`,
                    opacity: 0.4,
                    animation: "spinSlow 12s linear infinite",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    width: "240px",
                    height: "240px",
                    borderRadius: "50%",
                    border: `1px solid ${statusColor}`,
                    opacity: 0.3,
                    animation: "pulseGlow 2s ease-in-out infinite",
                  }}
                />
              </>
            )}

            {/* Neural Persona Sphere */}
            <div
              style={{
                width: "180px",
                height: "180px",
                borderRadius: "50%",
                background: sphereGradient,
                border: `3px solid ${sphereBorder}`,
                boxShadow: `0 0 45px ${glowColor}, inset 0 0 25px ${glowColor}`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                cursor: "pointer",
                transition: "all 0.3s ease",
              }}
              onClick={onToggleMic}
              title="Click to toggle microphone"
            >
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: "bold",
                  letterSpacing: "2px",
                  color: "#ffffff",
                  textShadow: `0 0 10px ${statusColor}`,
                }}
              >
                {agentName.toUpperCase()}
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "#94a3b8",
                  letterSpacing: "1px",
                  marginTop: "4px",
                }}
              >
                {isSpeaking ? "SPEAKING" : isMicActive ? "LISTENING" : isThinkingActive ? "THINKING" : "TAP MIC"}
              </div>

              {/* Mini Waveform Bars inside Core */}
              <div style={{ display: "flex", gap: "3px", alignItems: "center", height: "20px", marginTop: "8px" }}>
                {[12, 22, 16, 28, 18, 24, 14].map((h, idx) => (
                  <div
                    key={idx}
                    style={{
                      width: "3px",
                      height: isSpeaking || isMicActive ? `${h}px` : "4px",
                      background: statusColor,
                      borderRadius: "2px",
                      transition: "height 0.15s ease",
                      animation: isSpeaking || isMicActive ? `wavePulse 0.8s ease-in-out infinite ${idx * 0.1}s` : "none",
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Real-Time Live Subtitle Card */}
          <div
            style={{
              width: "100%",
              background: "rgba(3, 7, 18, 0.85)",
              border: "1px solid rgba(236, 72, 153, 0.2)",
              borderRadius: "8px",
              padding: "12px 14px",
              backdropFilter: "blur(8px)",
              minHeight: "75px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ fontSize: "10px", fontWeight: "bold", color: "#ec4899", letterSpacing: "1px" }}>
                LIVE SPEECH TRANSCRIPTION
              </span>
              <span style={{ fontSize: "9px", color: "#64748b" }}>
                {isSpeaking ? "🔊 Audio Active" : isMicActive ? "🎙️ Mic Active" : "Standby"}
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "#f1f5f9", lineHeight: "1.4", fontStyle: "italic" }}>
              {isSpeaking
                ? latestFridayResponse || "Responding directly to your query..."
                : isMicActive
                ? latestUserTranscript
                  ? `"${latestUserTranscript}"`
                  : "Say anything to Friday... (No wake word required)"
                : "Microphone paused. Click 'Enable Mic' to talk."}
            </div>
          </div>

          {/* Quick Voice Bar Controls */}
          <div style={{ display: "flex", gap: "10px", width: "100%", marginTop: "12px" }}>
            <button
              onClick={onToggleMic}
              style={{
                flex: 1,
                background: isListening ? "linear-gradient(135deg, #10b981, #059669)" : "rgba(30, 41, 59, 0.8)",
                border: `1px solid ${isListening ? "#34d399" : "#475569"}`,
                color: "#ffffff",
                borderRadius: "6px",
                padding: "8px 12px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                boxShadow: isListening ? "0 0 12px rgba(52, 211, 153, 0.4)" : "none",
              }}
            >
              <span>{isListening ? "🎙️ MIC ACTIVE" : "🔇 MIC OFF"}</span>
            </button>

            {isSpeaking && (
              <button
                onClick={onStopExecution}
                style={{
                  background: "linear-gradient(135deg, #ef4444, #b91c1c)",
                  border: "1px solid #f87171",
                  color: "#ffffff",
                  borderRadius: "6px",
                  padding: "8px 14px",
                  fontSize: "11px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  boxShadow: "0 0 12px rgba(239, 68, 68, 0.5)",
                }}
                title="Interrupt and stop speech"
              >
                🛑 INTERRUPT
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Dedicated One-to-One Conversation Stream */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "rgba(1, 4, 9, 0.75)",
            borderRadius: "10px",
            border: "1px solid rgba(236, 72, 153, 0.25)",
            overflow: "hidden",
          }}
        >
          {/* Stream Header */}
          <div
            style={{
              padding: "8px 14px",
              background: "rgba(3, 7, 18, 0.9)",
              borderBottom: "1px solid rgba(236, 72, 153, 0.2)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: "11px", fontWeight: "bold", color: "#f472b6", letterSpacing: "1px" }}>
              CONVERSATION STREAM
            </span>
            <span style={{ fontSize: "10px", color: "#94a3b8" }}>
              {messages.length} messages
            </span>
          </div>

          {/* Messages Scroll Area */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
            }}
          >
            {messages.length === 0 ? (
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#64748b",
                  fontSize: "12px",
                  textAlign: "center",
                  padding: "20px",
                }}
              >
                <div style={{ fontSize: "28px", marginBottom: "8px" }}>🎙️</div>
                <div style={{ fontWeight: "bold", color: "#e2e8f0", marginBottom: "4px" }}>
                  One to One Mode Ready
                </div>
                <div>
                  Start speaking normally or type below. {agentName} is listening directly without any wake words.
                </div>
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.sender === "user";
                const isSystem = m.sender === "system";

                if (isSystem) {
                  return (
                    <div
                      key={m.id}
                      style={{
                        alignSelf: "center",
                        fontSize: "9px",
                        fontWeight: "bold",
                        letterSpacing: "1px",
                        color: "#94a3b8",
                        background: "rgba(15, 23, 42, 0.6)",
                        padding: "3px 8px",
                        borderRadius: "10px",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                      }}
                    >
                      {m.text}
                    </div>
                  );
                }

                return (
                  <div
                    key={m.id}
                    style={{
                      alignSelf: isUser ? "flex-end" : "flex-start",
                      maxWidth: "85%",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: isUser ? "flex-end" : "flex-start",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "9px",
                        color: isUser ? "#38bdf8" : "#ec4899",
                        fontWeight: "bold",
                        marginBottom: "2px",
                        padding: "0 4px",
                      }}
                    >
                      {isUser ? userName : agentName} • {m.timestamp}
                    </div>
                    <div
                      style={{
                        background: isUser
                          ? "linear-gradient(135deg, rgba(14, 165, 233, 0.25), rgba(2, 132, 199, 0.15))"
                          : "linear-gradient(135deg, rgba(236, 72, 153, 0.25), rgba(168, 85, 247, 0.15))",
                        border: `1px solid ${isUser ? "rgba(56, 189, 248, 0.4)" : "rgba(236, 72, 153, 0.4)"}`,
                        color: "#f8fafc",
                        padding: "8px 12px",
                        borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                        fontSize: "12px",
                        lineHeight: "1.4",
                        wordBreak: "break-word",
                      }}
                    >
                      {m.text}
                    </div>
                  </div>
                );
              })
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Hybrid Text Input Bar */}
          <form
            onSubmit={handleSend}
            style={{
              padding: "10px",
              background: "rgba(3, 7, 18, 0.95)",
              borderTop: "1px solid rgba(236, 72, 153, 0.2)",
              display: "flex",
              gap: "8px",
            }}
          >
            <input
              type="text"
              placeholder={`Type or speak to ${agentName}...`}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              style={{
                flex: 1,
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(236, 72, 153, 0.3)",
                borderRadius: "6px",
                padding: "8px 12px",
                color: "#ffffff",
                fontSize: "12px",
                outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={!inputText.trim()}
              style={{
                background: inputText.trim()
                  ? "linear-gradient(135deg, #ec4899, #a855f7)"
                  : "rgba(30, 41, 59, 0.5)",
                border: "none",
                color: "#ffffff",
                borderRadius: "6px",
                padding: "8px 16px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: inputText.trim() ? "pointer" : "default",
              }}
            >
              SEND
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
