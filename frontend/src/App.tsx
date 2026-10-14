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
  PowerSettings,
  BatteryState,
  WhatsAppSettings,
  WhatsAppLog,
  UrgentAlert,
  FeatureScanResult,
  DeviceMonitoringSettings,
  DesktopOverlaySettings
} from "./types/assistant";


// Modular UI Components
import { ProcessingIndicator } from "./components/ProcessingIndicator";
import { UrgentAlertBanner } from "./components/UrgentAlertBanner";
import { SettingsModal } from "./components/SettingsModal";
import { BlueLightMapModal } from "./components/BlueLightMapModal";
import { SystemMonitorView } from "./components/SystemMonitorView";
import { OneToOneView } from "./components/OneToOneView";

interface CodeBlockProps {
  language: string;
  code: string;
  blockId: string;
}

const CodeBlockCard: React.FC<CodeBlockProps> = ({ language, code, blockId }) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Failed to copy code block:", e);
    }
  };

  const rawLang = (language || "").trim().toLowerCase();
  let displayTitle = rawLang.toUpperCase().replace(/[_\-]+/g, " ");

  if (!rawLang || rawLang === "code" || rawLang === "text") {
    displayTitle = "CODE / OUTPUT";
  } else if (rawLang === "prompt" || rawLang.includes("prompt")) {
    displayTitle = rawLang.includes("negative") ? "NEGATIVE PROMPT" : "MASTER PROMPT";
  } else if (rawLang.includes("architect") || rawLang.includes("system")) {
    displayTitle = "PROJECT ARCHITECTURE";
  } else if (rawLang.includes("struct") || rawLang.includes("tree") || rawLang.includes("folder")) {
    displayTitle = "DIRECTORY STRUCTURE";
  }

  return (
    <div id={blockId} style={{
      margin: "10px 0",
      borderRadius: "6px",
      border: "1px solid rgba(0, 240, 255, 0.35)",
      background: "rgba(2, 8, 20, 0.96)",
      overflow: "hidden",
      boxShadow: "0 4px 16px rgba(0, 0, 0, 0.7)"
    }}>
      {/* Top Header Bar */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "6px 12px",
        background: "rgba(0, 240, 255, 0.08)",
        borderBottom: "1px solid rgba(0, 240, 255, 0.2)",
        fontSize: "10.5px",
        color: "var(--jarvis-cyan)",
        fontFamily: "'Inter', sans-serif"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, letterSpacing: "0.6px" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="16 18 22 12 16 6"></polyline>
            <polyline points="8 6 2 12 8 18"></polyline>
          </svg>
          <span style={{ color: "var(--jarvis-cyan)" }}>{displayTitle}</span>
        </div>
        <button
          onClick={handleCopyCode}
          style={{
            background: copied ? "rgba(16, 185, 129, 0.2)" : "rgba(0, 240, 255, 0.08)",
            border: copied ? "1px solid rgba(16, 185, 129, 0.6)" : "1px solid rgba(0, 240, 255, 0.3)",
            color: copied ? "#10b981" : "var(--jarvis-cyan)",
            cursor: "pointer",
            fontSize: "10px",
            padding: "3px 8px",
            borderRadius: "4px",
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            fontWeight: 600,
            transition: "all 0.2s ease",
            boxShadow: copied ? "0 0 8px rgba(16, 185, 129, 0.4)" : "0 0 4px rgba(0, 240, 255, 0.15)"
          }}
          title={copied ? "Copied code!" : "Copy block to clipboard"}
        >
          {copied ? (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <span>Copied!</span>
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Body */}
      <pre style={{
        margin: 0,
        padding: "12px 14px",
        overflowX: "auto",
        fontSize: "11.5px",
        lineHeight: 1.6,
        color: "#f8fafc",
        fontFamily: "Consolas, 'Fira Code', 'Courier New', monospace",
        background: "transparent",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word"
      }}>
        <code>{code}</code>
      </pre>
    </div>
  );
};

const ImageCard: React.FC<{
  src: string;
  prompt: string;
  engine?: string;
  path?: string;
}> = ({ src, prompt, engine = "FLUX.1 Turbo", path }) => {
  const [downloading, setDownloading] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedPath, setCopiedPath] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const resolveInitialSrc = () => {
    if (src && src.trim()) return src;
    if (path && path.trim()) {
      const filename = path.split(/[/\\]/).pop();
      if (filename) return `http://localhost:8000/api/v1/images/${filename}`;
    }
    return null;
  };

  const [imgSrc, setImgSrc] = useState<string | null>(resolveInitialSrc());

  useEffect(() => {
    if (src && src.trim()) {
      setImgSrc(src);
    } else if (path && path.trim()) {
      const filename = path.split(/[/\\]/).pop();
      if (filename) setImgSrc(`http://localhost:8000/api/v1/images/${filename}`);
    } else {
      setImgSrc(null);
    }
  }, [src, path]);

  const handleDownload = async () => {
    if (!imgSrc) return;
    try {
      setDownloading(true);
      const filename = path ? path.split(/[/\\]/).pop() || `friday_image_${Date.now()}.png` : `friday_image_${Date.now()}.png`;
      const response = await fetch(imgSrc);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
      setTimeout(() => setDownloading(false), 2000);
    } catch (e) {
      console.warn("Direct blob download fallback:", e);
      if (imgSrc) {
        const link = document.createElement("a");
        link.href = imgSrc;
        link.download = `friday_image_${Date.now()}.png`;
        link.target = "_blank";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setDownloading(false);
    }
  };

  const handleCopyPrompt = () => {
    try {
      navigator.clipboard.writeText(prompt);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 2000);
    } catch (e) {
      console.error("Failed to copy prompt:", e);
    }
  };

  const handleCopyPath = () => {
    if (!path) return;
    try {
      navigator.clipboard.writeText(path);
      setCopiedPath(true);
      setTimeout(() => setCopiedPath(false), 2000);
    } catch (e) {
      console.error("Failed to copy path:", e);
    }
  };

  const displayEngine = (engine || "FLUX.1 Turbo").toUpperCase();

  return (
    <div
      style={{
        margin: "12px 0",
        borderRadius: "8px",
        border: "1px solid rgba(0, 240, 255, 0.4)",
        background: "linear-gradient(180deg, rgba(2, 10, 24, 0.98) 0%, rgba(1, 4, 12, 0.98) 100%)",
        overflow: "hidden",
        boxShadow: "0 6px 24px rgba(0, 0, 0, 0.8), 0 0 12px rgba(0, 240, 255, 0.15)",
        width: "100%",
        maxWidth: "540px"
      }}
    >
      {/* Top Header Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "7px 12px",
          background: "rgba(0, 240, 255, 0.08)",
          borderBottom: "1px solid rgba(0, 240, 255, 0.2)",
          fontSize: "10.5px",
          color: "var(--jarvis-cyan)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "7px", fontWeight: 700, letterSpacing: "0.5px" }}>
          <span>🖼️</span>
          <span>AI IMAGE GENERATION</span>
          <span
            style={{
              fontSize: "9px",
              padding: "1px 6px",
              borderRadius: "3px",
              background: "rgba(0, 240, 255, 0.15)",
              border: "1px solid rgba(0, 240, 255, 0.35)",
              color: "var(--jarvis-cyan)",
              fontWeight: 600
            }}
          >
            {displayEngine}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={handleCopyPrompt}
            style={{
              background: copiedPrompt ? "rgba(16, 185, 129, 0.2)" : "rgba(0, 240, 255, 0.08)",
              border: copiedPrompt ? "1px solid rgba(16, 185, 129, 0.6)" : "1px solid rgba(0, 240, 255, 0.3)",
              color: copiedPrompt ? "#10b981" : "var(--jarvis-cyan)",
              cursor: "pointer",
              fontSize: "10px",
              padding: "3px 8px",
              borderRadius: "4px",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontWeight: 600,
              transition: "all 0.2s ease"
            }}
            title="Copy Prompt"
          >
            {copiedPrompt ? "✓ Copied" : "📋 Prompt"}
          </button>
          <button
            onClick={handleDownload}
            style={{
              background: downloading ? "rgba(16, 185, 129, 0.2)" : "rgba(0, 240, 255, 0.15)",
              border: downloading ? "1px solid rgba(16, 185, 129, 0.6)" : "1px solid rgba(0, 240, 255, 0.45)",
              color: downloading ? "#10b981" : "var(--jarvis-cyan)",
              cursor: "pointer",
              fontSize: "10px",
              padding: "3px 9px",
              borderRadius: "4px",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontWeight: 600,
              transition: "all 0.2s ease"
            }}
            title="Download Full Resolution PNG"
          >
            {downloading ? "✓ Saved!" : "⬇ Download"}
          </button>
        </div>
      </div>

      {/* Center Image Display */}
      <div
        onClick={() => setIsPreviewOpen(true)}
        style={{
          position: "relative",
          width: "100%",
          maxHeight: "380px",
          overflow: "hidden",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          background: "radial-gradient(circle at center, rgba(0, 240, 255, 0.06) 0%, #040914 100%)",
          padding: "6px",
          cursor: "zoom-in"
        }}
        title="Click to view full preview"
      >
        {imgSrc ? (
          <img
            src={imgSrc}
            alt={prompt || "AI Generated Image"}
            onError={() => {
              if (path) {
                const filename = path.split(/[/\\]/).pop();
                if (filename && (!imgSrc || !imgSrc.includes(filename))) {
                  setImgSrc(`http://localhost:8000/api/v1/images/${filename}`);
                }
              }
            }}
            style={{
              maxWidth: "100%",
              maxHeight: "360px",
              objectFit: "contain",
              display: "block",
              borderRadius: "4px",
              boxShadow: "0 4px 14px rgba(0, 0, 0, 0.6)"
            }}
            loading="lazy"
          />
        ) : (
          <div style={{ padding: "30px", color: "var(--jarvis-cyan)", fontSize: "11px", letterSpacing: "1px", textAlign: "center" }}>
            GENERATING VISUAL ASSET...
          </div>
        )}
      </div>

      {/* Bottom Info Box - Inside the Card */}
      <div
        style={{
          padding: "9px 12px",
          background: "rgba(0, 240, 255, 0.04)",
          borderTop: "1px solid rgba(0, 240, 255, 0.18)",
          display: "flex",
          flexDirection: "column",
          gap: "6px"
        }}
      >
        {/* Prompt details */}
        <div>
          <div style={{ fontSize: "9px", fontWeight: 700, color: "var(--jarvis-cyan)", letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: "2px" }}>
            PROMPT:
          </div>
          <div style={{ fontSize: "11px", color: "#e2e8f0", lineHeight: 1.5, wordBreak: "break-word" }}>
            {prompt}
          </div>
        </div>

        {/* Saved Path Details */}
        {path && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "8px",
              background: "rgba(0, 0, 0, 0.4)",
              padding: "4px 8px",
              borderRadius: "4px",
              border: "1px solid rgba(0, 240, 255, 0.12)",
              marginTop: "2px"
            }}
          >
            <span
              style={{
                fontSize: "9.5px",
                color: "#94a3b8",
                fontFamily: "Consolas, 'Fira Code', monospace",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap"
              }}
              title={path}
            >
              📁 {path}
            </span>
            <button
              onClick={handleCopyPath}
              style={{
                background: copiedPath ? "rgba(16, 185, 129, 0.2)" : "rgba(0, 240, 255, 0.08)",
                border: copiedPath ? "1px solid rgba(16, 185, 129, 0.5)" : "1px solid rgba(0, 240, 255, 0.25)",
                color: copiedPath ? "#10b981" : "var(--jarvis-cyan)",
                cursor: "pointer",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "3px",
                fontWeight: 600,
                whiteSpace: "nowrap"
              }}
              title="Copy file path to clipboard"
            >
              {copiedPath ? "✓ Copied" : "Copy Path"}
            </button>
          </div>
        )}
      </div>

      {/* Lightbox Preview Modal */}
      {isPreviewOpen && (
        <div
          onClick={() => setIsPreviewOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            background: "rgba(0, 0, 0, 0.88)",
            backdropFilter: "blur(6px)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "20px",
            cursor: "zoom-out"
          }}
        >
          <div style={{ maxWidth: "90vw", maxHeight: "90vh", display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
            {imgSrc && (
              <img
                src={imgSrc}
                alt={prompt || "Full Preview"}
                style={{
                  maxWidth: "100%",
                  maxHeight: "82vh",
                  objectFit: "contain",
                  borderRadius: "6px",
                  border: "1px solid rgba(0, 240, 255, 0.5)",
                  boxShadow: "0 0 30px rgba(0, 240, 255, 0.3)"
                }}
              />
            )}
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload();
                }}
                style={{
                  background: "rgba(0, 240, 255, 0.2)",
                  border: "1px solid rgba(0, 240, 255, 0.6)",
                  color: "#00f0ff",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 600
                }}
              >
                {downloading ? "✓ Saved!" : "⬇ Download Full Image"}
              </button>
              <button
                onClick={() => setIsPreviewOpen(false)}
                style={{
                  background: "rgba(239, 68, 68, 0.2)",
                  border: "1px solid rgba(239, 68, 68, 0.6)",
                  color: "#f87171",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 600
                }}
              >
                ✕ Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const renderFormattedInlineText = (text: string, keyPrefix: string): React.ReactNode[] => {
  // Format bold (**text**), italics (*text*), inline code (`code`), and bullet lists cleanly
  if (!text) return [];
  const lines = text.split("\n");
  const renderedLines: React.ReactNode[] = [];

  lines.forEach((line, lIdx) => {
    // Check for inline elements using regex
    const inlineRegex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
    const parts = line.split(inlineRegex);
    const lineNodes: React.ReactNode[] = [];

    parts.forEach((part, pIdx) => {
      const partKey = `${keyPrefix}-l${lIdx}-p${pIdx}`;
      if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
        lineNodes.push(
          <strong key={partKey} style={{ color: "var(--jarvis-cyan)", fontWeight: 700 }}>
            {part.slice(2, -2)}
          </strong>
        );
      } else if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
        lineNodes.push(
          <em key={partKey} style={{ color: "#94a3b8", fontStyle: "italic" }}>
            {part.slice(1, -1)}
          </em>
        );
      } else if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
        lineNodes.push(
          <code
            key={partKey}
            style={{
              background: "rgba(0, 240, 255, 0.1)",
              border: "1px solid rgba(0, 240, 255, 0.2)",
              color: "#38bdf8",
              fontFamily: "Consolas, 'Fira Code', monospace",
              padding: "1px 4px",
              borderRadius: "3px",
              fontSize: "10.5px"
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      } else if (part) {
        lineNodes.push(<span key={partKey}>{part}</span>);
      }
    });

    renderedLines.push(
      <div key={`${keyPrefix}-line-${lIdx}`} style={{ minHeight: "1.2em", wordBreak: "break-word" }}>
        {lineNodes}
      </div>
    );
  });

  return renderedLines;
};

const renderTextWithImages = (text: string, keyPrefix: string): React.ReactNode[] => {
  const imageRegex = /!\[([\s\S]*?)\]\(([\s\S]*?)\)/g;
  const elements: React.ReactNode[] = [];
  let lastIdx = 0;
  let match: RegExpExecArray | null;
  let imgIdx = 0;

  while ((match = imageRegex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      const precedingText = text.slice(lastIdx, match.index).trim();
      if (precedingText) {
        elements.push(
          <div key={`${keyPrefix}-t-${lastIdx}`} style={{ marginBottom: "6px" }}>
            {renderFormattedInlineText(precedingText, `${keyPrefix}-t-${lastIdx}`)}
          </div>
        );
      }
    }

    const rawAlt = match[1].replace(/\r?\n/g, " ").trim();
    const src = match[2].trim();

    let prompt = rawAlt;
    let engine = "FLUX.1 Turbo";
    let path = "";

    if (rawAlt.includes("|engine=") || rawAlt.includes("|path=")) {
      const parts = rawAlt.split("|");
      prompt = (parts[0] || "AI Generated Image").trim();
      for (let i = 1; i < parts.length; i++) {
        const part = parts[i].trim();
        if (part.startsWith("engine=")) {
          engine = part.slice(7).trim();
        } else if (part.startsWith("path=")) {
          path = part.slice(5).trim();
        }
      }
    }

    elements.push(
      <ImageCard
        key={`${keyPrefix}-img-${imgIdx++}`}
        prompt={prompt}
        src={src}
        engine={engine}
        path={path}
      />
    );
    lastIdx = imageRegex.lastIndex;
  }

  if (lastIdx < text.length) {
    const trailingText = text.slice(lastIdx).trim();
    // Only render trailing text if it's not redundant bullet lines already in the image card
    if (trailingText && !trailingText.startsWith("• **Prompt:**")) {
      elements.push(
        <div key={`${keyPrefix}-tend-${lastIdx}`} style={{ marginTop: "6px" }}>
          {renderFormattedInlineText(trailingText, `${keyPrefix}-tend-${lastIdx}`)}
        </div>
      );
    }
  }

  return elements;
};

const RenderMessageContent: React.FC<{ content: string; messageId: string }> = React.memo(({ content, messageId }) => {
  if (!content) return null;

  // Robust Regex matching closed code blocks: ```lang ... ``` with optional leading spaces and 3+ backticks
  const codeBlockRegex = /(?:^|\n)[ \t]*`{3,}([^\r\n]*)\r?\n([\s\S]*?)\r?\n[ \t]*`{3,}[ \t]*(?=\n|$)/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let blockIndex = 0;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    const matchStart = match.index + (match[0].startsWith("\n") ? 1 : 0);
    if (matchStart > lastIndex) {
      const textChunk = content.slice(lastIndex, matchStart);
      if (textChunk) {
        parts.push(...renderTextWithImages(textChunk, `${messageId}-chunk-${lastIndex}`));
      }
    }

    const lang = (match[1] || "code").trim();
    const code = match[2];
    const blockKey = `${messageId}-block-${blockIndex++}`;

    parts.push(
      <CodeBlockCard
        key={blockKey}
        blockId={blockKey}
        language={lang}
        code={code}
      />
    );

    lastIndex = codeBlockRegex.lastIndex;
  }

  if (lastIndex < content.length) {
    const remainingText = content.slice(lastIndex);
    // Check if remaining text contains an unclosed code block (e.g. streaming or truncated message)
    const unclosedMatch = remainingText.match(/(?:^|\n)[ \t]*`{3,}([^\r\n]*)\r?\n([\s\S]*)$/);
    if (unclosedMatch && unclosedMatch.index !== undefined) {
      const matchStart = unclosedMatch.index + (unclosedMatch[0].startsWith("\n") ? 1 : 0);
      const textBefore = remainingText.slice(0, matchStart);
      if (textBefore) {
        parts.push(...renderTextWithImages(textBefore, `${messageId}-rem-${lastIndex}`));
      }
      const lang = (unclosedMatch[1] || "code").trim();
      const code = unclosedMatch[2];
      const blockKey = `${messageId}-block-${blockIndex++}`;
      parts.push(
        <CodeBlockCard
          key={blockKey}
          blockId={blockKey}
          language={lang}
          code={code}
        />
      );
    } else {
      parts.push(...renderTextWithImages(remainingText, `${messageId}-end-${lastIndex}`));
    }
  }

  return (
    <div style={{ fontSize: "11.5px", color: "#e2e8f0", marginTop: "4px", lineHeight: 1.6 }}>
      {parts}
    </div>
  );
});

const ChatMessageBubble: React.FC<{
  m: Message;
  isCopied: boolean;
  onCopy: (id: string, text: string) => void;
  onSpeak: (text: string) => void;
}> = React.memo(({ m, isCopied, onCopy, onSpeak }) => {
  return (
    <div
      style={{
        padding: "6px 10px",
        borderRadius: "4px",
        background: m.sender === "user" ? "rgba(0, 240, 255, 0.05)" : "rgba(0, 0, 0, 0.4)",
        borderLeft: m.sender === "user" ? "2px solid var(--jarvis-cyan)" : "2px solid rgba(0, 240, 255, 0.3)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div
          style={{
            fontSize: m.sender === "user" ? "9px" : "10px",
            fontFamily: m.sender === "user" ? "'Share Tech Mono', monospace" : "var(--font-eurostile)",
            fontStyle: m.sender === "user" ? "normal" : "italic",
            fontStretch: m.sender === "user" ? "normal" : "expanded",
            color: "var(--jarvis-cyan)",
            fontWeight: 800,
            letterSpacing: m.sender === "user" ? "0.8px" : "1.8px",
            textTransform: "uppercase",
            display: "flex",
            alignItems: "center",
            gap: "5px"
          }}
        >
          {m.sender === "user" ? "USER" : (
            <>
              <span style={{ fontSize: "10px", filter: "drop-shadow(0 0 6px var(--jarvis-cyan))" }}>▲</span>
              <span>{m.sender.toUpperCase()}</span>
            </>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={() => onCopy(m.id, m.text)}
            style={{
              background: isCopied ? "rgba(16, 185, 129, 0.15)" : "rgba(0, 240, 255, 0.06)",
              border: isCopied ? "1px solid rgba(16, 185, 129, 0.5)" : "1px solid rgba(0, 240, 255, 0.25)",
              color: isCopied ? "#10b981" : "var(--jarvis-cyan)",
              cursor: "pointer",
              fontSize: "10px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2px 5px",
              borderRadius: "3px",
              transition: "all 0.2s ease",
              boxShadow: isCopied ? "0 0 8px rgba(16, 185, 129, 0.4)" : "0 0 4px rgba(0, 240, 255, 0.15)"
            }}
            title={isCopied ? "Copied to clipboard!" : "Copy message"}
          >
            {isCopied ? (
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            ) : (
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ filter: "drop-shadow(0 0 2px rgba(0, 240, 255, 0.5))" }}>
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            )}
          </button>
          <button
            onClick={() => onSpeak(m.text)}
            style={{ background: "transparent", border: "none", color: "var(--jarvis-cyan)", cursor: "pointer", fontSize: "10px", padding: "0 2px" }}
            title="Speak this message"
          >
            🔊 Speak
          </button>
        </div>
      </div>
      <RenderMessageContent content={m.text} messageId={m.id} />
    </div>
  );
});

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
  const [isChatMaximized, setIsChatMaximized] = useState<boolean>(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("english");
  const [isGlobalMuted, setIsGlobalMuted] = useState<boolean>(false);

  // Settings & Modal States
  const [currentView, setCurrentView] = useState<"home" | "chat" | "map" | "system" | "one-to-one">("home");
  const [oneToOneMessages, setOneToOneMessages] = useState<Message[]>([]);
  const [latestUserTranscript, setLatestUserTranscript] = useState<string>("");
  const [latestFridayResponse, setLatestFridayResponse] = useState<string>("");
  const currentViewRef = useRef(currentView);

  useEffect(() => {
    currentViewRef.current = currentView;
  }, [currentView]);
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

  // Desktop Overlay States
  const [isBox9Open, setIsBox9Open] = useState<boolean>(false);
  const [overlaySettings, setOverlaySettings] = useState<DesktopOverlaySettings>({
    enabled: false,
    opacity: 1.0,
    scale: 0.85,
    reset_position: false
  });
  const [isUpdatingOverlay, setIsUpdatingOverlay] = useState<boolean>(false);

  const fetchOverlaySettings = async () => {
    try {
      const resp = await fetch("http://localhost:8000/api/v1/settings/desktop-overlay");
      if (resp.ok) {
        const data = await resp.json();
        if (data.status === "success" && data.settings) {
          setOverlaySettings(data.settings);
        }
      }
    } catch (e) { }
  };

  const updateOverlaySettings = async (opts: Partial<DesktopOverlaySettings>) => {
    setIsUpdatingOverlay(true);
    try {
      const resp = await fetch("http://localhost:8000/api/v1/settings/desktop-overlay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opts)
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.status === "success" && data.settings) {
          setOverlaySettings(data.settings);
        }
      }
    } catch (e) { } finally {
      setIsUpdatingOverlay(false);
    }
  };

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
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

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
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeWsRef = useRef<WebSocket | null>(null);
  const activeTtsAbortRef = useRef<AbortController | null>(null);
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const speechPulseIntervalRef = useRef<any>(null);
  const speechSeqRef = useRef<number>(0);

  const isListeningDesiredRef = useRef<boolean>(true);
  const isSpeakingRef = useRef<boolean>(false);
  const profileRef = useRef<UserProfile>(profile);
  const isSendingRef = useRef<boolean>(false);
  const lastMessageDedupeRef = useRef<{ sender: string; text: string; time: number }>({ sender: "", text: "", time: 0 });

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

  // Non-blocking ChatGPT-style Textarea Auto-Expansion & Dynamic Sizing
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInputText(val);
    const target = e.target;
    requestAnimationFrame(() => {
      if (!target) return;
      target.style.height = "auto";
      const scrollH = target.scrollHeight;
      target.style.height = `${Math.min(Math.max(scrollH, 36), 140)}px`;
    });
  };

  // ChatGPT-style Keyboard Shortcuts: Shift+Enter for newline, Enter to send, Up Arrow to recall
  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter") {
      if (e.shiftKey) {
        // Shift + Enter: Allow natural multiline newline insertion
        return;
      } else {
        // Enter without Shift: Dispatch message immediately
        e.preventDefault();
        handleSendMessage();
      }
    } else if (e.key === "ArrowUp") {
      // ChatGPT Prompt Recall: populate last user prompt if input is empty
      if (!inputText.trim() && messages.length > 0) {
        const userMsgs = messages.filter((m) => m.sender === "user").map((m) => m.text);
        if (userMsgs.length > 0) {
          e.preventDefault();
          setInputText(userMsgs[userMsgs.length - 1]);
        }
      }
    } else if (e.key === "Escape") {
      if (inputText) {
        e.preventDefault();
        setInputText("");
        if (textareaRef.current) textareaRef.current.style.height = "36px";
      }
    }
  };

  // ChatGPT-style Clipboard Attachment Paste Handler
  const handleTextareaPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (e.clipboardData.files && e.clipboardData.files.length > 0) {
      const pastedFiles = Array.from(e.clipboardData.files);
      const combined = [...selectedFiles, ...pastedFiles].slice(0, 6);
      setSelectedFiles(combined);
    }
  };

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
        if (data && (data.name || data.profile?.name)) {
          const agent = data.agent_profile?.agent_name || data.agent_name || data.wake_word || "Friday";
          const wake = data.agent_profile?.wake_word || data.wake_word || agent.toLowerCase();
          const userName = data.profile?.name || data.name || "Harishan";
          const userAge = data.profile?.age || data.age || "";
          const userEmail = data.profile?.email || data.email || "";
          const userCity = data.profile?.city || data.city || "";
          const loaded: UserProfile = {
            name: userName,
            agent_name: agent,
            wake_word: wake,
            age: userAge,
            email: userEmail,
            city: userCity,
            voice_gender: (data.voice_gender || "female") as "female" | "male",
            language: data.language || "english",
            languages: Array.isArray(data.languages) ? data.languages : ["english", "tamil", "tanglish"],
            profile: {
              name: userName,
              age: userAge,
              email: userEmail,
              city: userCity
            },
            agent_profile: {
              agent_name: agent,
              wake_word: wake
            }
          };
          setProfile(loaded);
          setSettingsForm(loaded);
          setSelectedLanguage(data.language || "english");
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
    fetchOverlaySettings();
    fetchOneToOneMessages();
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
        activeWsRef.current = activeWs;
        activeWs.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === "state" && payload.data) {
              setAssistantState(payload.data);
              setIsThinking(payload.data === "thinking");
              if (payload.is_speaking !== undefined) isSpeakingRef.current = Boolean(payload.is_speaking);
              if (payload.is_listening !== undefined) {
                const lis = Boolean(payload.is_listening);
                setIsListening(lis);
                isListeningDesiredRef.current = lis;
                if (!lis) safeStopRecognition();
                else if (payload.data !== "thinking" && payload.data !== "speaking") safeStartRecognition();
              }
            } else if (payload.type === "mic_toggled") {
              const active = Boolean(payload.is_listening);
              setIsListening(active);
              isListeningDesiredRef.current = active;
              setAssistantState(payload.state || (active ? "listening" : "idle"));
              if (active) {
                safeStartRecognition();
              } else {
                safeStopRecognition();
              }
            }
          } catch (err) { }
        };
      } catch (e) { }
    };

    connectTelemetry();

    return () => {
      isMounted = false;
      if (activeWs) activeWs.close();
      activeWsRef.current = null;
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
      theme: "yellow" | "red" | "blue"
    ) => {
      ctx.save();

      const numStrands = 28;
      const pointsPerRing = 130;
      const isThinkingActive = theme === "yellow";
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

        const alpha = Math.max(0.12, 1 - Math.abs(offsetFraction) * 1.8) * (isSpeaking ? 0.85 : isThinkingActive ? 0.92 : 0.35);
        const primaryColor = theme === "yellow"
          ? `rgba(250, 204, 21, ${alpha})`
          : theme === "blue"
            ? `rgba(0, 240, 255, ${alpha})`
            : `rgba(248, 113, 113, ${alpha})`;
        const secondaryColor = theme === "yellow"
          ? `rgba(234, 179, 8, ${alpha * 0.75})`
          : theme === "blue"
            ? `rgba(0, 140, 255, ${alpha * 0.85})`
            : `rgba(239, 68, 68, ${alpha * 0.85})`;
        ctx.strokeStyle = s % 2 === 0 ? primaryColor : secondaryColor;
        ctx.lineWidth = s % 4 === 0 ? 1.4 : 0.8;

        if ((isSpeaking || isThinkingActive) && s % 5 === 0) {
          ctx.shadowColor = theme === "yellow" ? "#facc15" : theme === "blue" ? "#00f0ff" : "#ef4444";
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
      const isThinkingActive = isThinkingRef.current || assistantStateRef.current === "thinking";
      const isMicOn = isListeningDesiredRef.current || isListeningRef.current || assistantStateRef.current === "listening";

      let theme: "yellow" | "red" | "blue" = "red";
      if (isThinkingActive) {
        theme = "yellow";
      } else if (isSpeaking || isMicOn) {
        theme = "blue";
      } else {
        theme = "red";
      }

      const arcCol1 = theme === "yellow" ? "rgba(250, 204, 21, 0.95)" : theme === "blue" ? "rgba(0, 240, 255, 0.88)" : "rgba(248, 113, 113, 0.88)";
      const arcCol2 = theme === "yellow" ? "rgba(234, 179, 8, 0.65)" : theme === "blue" ? "rgba(0, 140, 255, 0.45)" : "rgba(239, 68, 68, 0.45)";
      const arcCol3 = theme === "yellow" ? "rgba(250, 204, 21, 0.85)" : theme === "blue" ? "rgba(0, 240, 255, 0.65)" : "rgba(248, 113, 113, 0.65)";
      const arcCol4 = theme === "yellow" ? "rgba(250, 204, 21, 0.95)" : theme === "blue" ? "rgba(0, 240, 255, 0.95)" : "rgba(239, 68, 68, 0.95)";

      drawSegmentedArc(cx, cy, 125, 4, 0.45, arcCol1, theme === "yellow" ? 2.6 : 2.5, angle * 0.6);
      drawSegmentedArc(cx, cy, 112, 24, 0.08, arcCol2, 1.8, -angle * 0.8);
      drawSegmentedArc(cx, cy, 96, 40, 0.05, arcCol3, theme === "yellow" ? 2.6 : 2.5, angle * 0.5);
      drawSegmentedArc(cx, cy, 76, 8, 0.25, arcCol4, 1.8, -angle * 1.3);

      const pulse = isSpeaking ? 1.6 : theme === "yellow" ? 1.35 : 1.0;
      const coreR = Math.max(10, 18 + Math.sin(angle * 6) * (2.5 * pulse));

      const radGrad = ctx.createRadialGradient(cx, cy, 1.5, cx, cy, coreR);
      radGrad.addColorStop(0, "#ffffff");
      radGrad.addColorStop(0.35, theme === "yellow" ? "#facc15" : theme === "blue" ? (isSpeaking ? "#38bdf8" : "#00f0ff") : "#ef4444");
      radGrad.addColorStop(0.85, theme === "yellow" ? "rgba(234, 179, 8, 0.4)" : theme === "blue" ? "rgba(0, 119, 255, 0.35)" : "rgba(239, 68, 68, 0.35)");
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fillStyle = radGrad;
      ctx.fill();

      drawCircularWaveMesh(cx, cy, isSpeaking, theme);

      angle += isSpeaking ? 0.045 : theme === "yellow" ? 0.028 : 0.012;
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [currentView, isTerminalCollapsed, isChatMaximized]);

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
     * Retrieves the list of active 24-hour conversational sessions from backend storage
     * and maintains the user's active session without creating unwanted duplicate chats.
     */
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations");
      const data = await res.json();
      if (data && data.status === "success" && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
        const desiredId = targetToSelect || activeConversationId;
        if (desiredId && data.conversations.some((c: any) => c.conversation_id === desiredId)) {
          loadConversation(desiredId);
        } else if (data.conversations.length > 0) {
          loadConversation(data.conversations[0].conversation_id);
        } else if (!desiredId) {
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
          const dedupedMsgs: Message[] = [];
          msgs.forEach((m: any, idx: number) => {
            const role = m.role === "user" ? "user" : m.role === "assistant" ? "friday" : "system";
            const text = m.content || "";
            const prev = dedupedMsgs[dedupedMsgs.length - 1];
            if (prev && prev.sender === role && prev.text === text) {
              return; // Skip duplicate adjacent message
            }
            dedupedMsgs.push({
              id: m.message_id || `msg-${idx}-${Math.random().toString(36).substring(2, 7)}`,
              sender: role,
              text,
              timestamp: new Date((m.created_at || Date.now() / 1000) * 1000).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
            });
          });
          setMessages(dedupedMsgs);
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

  const fetchOneToOneMessages = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations/one_to_one");
      const data = await res.json();
      if (data && data.status === "success" && data.conversation) {
        const msgs = data.conversation.messages || [];
        const formatted: Message[] = msgs.map((m: any, idx: number) => ({
          id: m.message_id || `oto-${idx}-${Math.random().toString(36).substring(2, 7)}`,
          sender: m.role === "user" ? "user" : m.role === "assistant" ? "friday" : "system",
          text: m.content || "",
          timestamp: new Date((m.created_at || Date.now() / 1000) * 1000).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        }));
        setOneToOneMessages(formatted);
      } else {
        setOneToOneMessages([]);
      }
    } catch (e) {
      setOneToOneMessages([]);
    }
  };

  const clearOneToOneHistory = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/conversations/one_to_one/messages", {
        method: "DELETE",
      });
      setOneToOneMessages([]);
      setLatestUserTranscript("");
      setLatestFridayResponse("");
    } catch (e) { }
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

  const selectOptimalVoice = (text: string, overrideGender?: "female" | "male") => {
    /**
     * What does this function do:
     * Analyzes text to dynamically select optimal TTS voice engine, locale, pitch, and speech rate,
     * strictly honoring the user's selected gender (Female vs Male) so the voice identity NEVER drifts.
     */
    const clean = text.trim();
    const isTamil = /[\u0B80-\u0BFF]/.test(clean);
    const isTanglish = /\b(vanakkam|nandri|epdi|eppadi|irukinga|irukeenga|irukken|irukku|solunga|sollunga|pannunga|panren|panniten|romba|seri|theriyuma|kudunga|enna|enga|yaar|ungalukku|enakku|tamil|tanglish|tamilnadu|illai|aama|illa|machan|thala|bro|vaanga|ponga|sollu|theriyum|varaverpu|anbu|nanba|nanbargale|amma|appa|anna|thambi|thangachi|akka)\b/i.test(clean);

    const gender = (overrideGender || profileRef.current.voice_gender || "female").toLowerCase();
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

    const pitchAdjustment = isFemale ? 1.12 : 0.88;

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
        rate: 1.0,
        pitch: pitchAdjustment
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
        rate: 1.0,
        pitch: pitchAdjustment
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
      rate: 1.0,
      pitch: pitchAdjustment
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
    const currentLang = (profileRef.current.language || "english").toLowerCase();
    recognition.lang = currentLang === "tamil" ? "ta-IN" : "en-IN";

    let restartTimer: any = null;

    recognition.onstart = () => {
      if (!isSpeakingRef.current && !isThinkingRef.current && !isSendingRef.current) {
        setIsListening(true);
      }
    };

    recognition.onresult = (event: any) => {
      if (isSpeakingRef.current || isThinkingRef.current || isSendingRef.current) return;

      const lastIndex = event.results.length - 1;
      const lastResult = event.results[lastIndex];
      if (!lastResult) return;

      // If recognition returns interim hypotheses, ignore non-final interim updates to prevent duplicate triggers
      if (event.results.length > 1 && !lastResult.isFinal) return;

      const transcript = (lastResult[0]?.transcript || "").trim();
      if (!transcript) return;

      // In One-to-One Mode: DIRECT PERSON-TO-PERSON CONVERSATION (Zero Wake Word Delay)
      if (currentViewRef.current === "one-to-one") {
        setLatestUserTranscript(transcript);
        if (isSpeakingRef.current || isThinkingRef.current || isSendingRef.current) return;
        setInputText("");
        handleSendMessage(undefined, transcript);
        return;
      }

      const currentWakeWord = (profileRef.current.wake_word || profileRef.current.agent_name || "Friday").trim().toLowerCase();
      const currentAgentName = (profileRef.current.agent_name || "Friday").trim().toLowerCase();
      const wakeWordsSet = Array.from(new Set([currentWakeWord, currentAgentName, "friday"])).filter(Boolean);
      const wakeRegexGroup = wakeWordsSet.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|");
      const wakePattern = new RegExp(`\\b(?:hey\\s+|hi\\s+|hello\\s+|vanakkam\\s+|வணக்கம்\\s+|ok\\s+)?(?:${wakeRegexGroup})\\b`, "i");

      // Check if the wake word was spoken
      const hasWakeWord = wakePattern.test(transcript);
      if (!hasWakeWord) {
        console.log(`[SpeechRecognition] Ignored speech without wake word: "${transcript}"`);
        return;
      }

      // Extract the command by removing the wake word greeting prefix
      let cleanCommand = transcript
        .replace(new RegExp(`^.*?\\b(?:hey\\s+|hi\\s+|hello\\s+|vanakkam\\s+|வணக்கம்\\s+|ok\\s+)?(?:${wakeRegexGroup})[,:\\s]*`, "i"), "")
        .trim();

      // If user only said the wake word (e.g., "Friday", "Hey Friday", "Jarvis"), pass the wake word so the agent greets back
      if (!cleanCommand) {
        cleanCommand = currentWakeWord;
      }

      if (isSpeakingRef.current || isThinkingRef.current || isSendingRef.current) return;

      setInputText("");
      handleSendMessage(undefined, cleanCommand);
    };

    recognition.onerror = () => {
      if (isListeningDesiredRef.current && !isSpeakingRef.current && !isThinkingRef.current && !isSendingRef.current) {
        if (restartTimer) clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          safeStartRecognition();
        }, 150);
      }
    };

    recognition.onend = () => {
      if (isListeningDesiredRef.current && !isSpeakingRef.current && !isThinkingRef.current && !isSendingRef.current) {
        if (restartTimer) clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          safeStartRecognition();
        }, 150);
      } else if (!isListeningDesiredRef.current) {
        setIsListening(false);
      }
    };

    recognitionRef.current = recognition;
    safeStartRecognition();

    return () => {
      if (restartTimer) clearTimeout(restartTimer);
      safeStopRecognition();
    };
  }, [isThinking, profile.language]);

  const syncVoiceStateToBackend = (
    newState: "listening" | "idle" | "thinking" | "speaking" | "error",
    newListening?: boolean,
    newThinking?: boolean,
    newSpeaking?: boolean
  ) => {
    const lis = newListening !== undefined ? newListening : isListeningDesiredRef.current;
    const thk = newThinking !== undefined ? newThinking : (newState === "thinking");
    const spk = newSpeaking !== undefined ? newSpeaking : (newState === "speaking");

    if (activeWsRef.current && activeWsRef.current.readyState === WebSocket.OPEN) {
      try {
        activeWsRef.current.send(JSON.stringify({
          action: "set_voice_state",
          state: newState,
          is_listening: lis,
          is_thinking: thk,
          is_speaking: spk
        }));
      } catch (e) { }
    }
    fetch("http://localhost:8000/api/v1/voice/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        state: newState,
        is_listening: lis,
        is_thinking: thk,
        is_speaking: spk
      })
    }).catch(() => { });
  };

  const toggleListening = () => {
    /**
     * What does this function do:
     * Toggles continuous microphone listening ON / OFF.
     */
    if (!recognitionRef.current) {
      alert("Speech recognition is supported in Chrome or Edge.");
      return;
    }

    const nextState = !isListening;
    isListeningDesiredRef.current = nextState;
    setIsListening(nextState);
    setAssistantState(nextState ? "listening" : "idle");

    if (nextState) {
      safeStartRecognition();
    } else {
      safeStopRecognition();
    }

    syncVoiceStateToBackend(nextState ? "listening" : "idle", nextState, false, false);
  };

  const handleTestVoice = (lang: "english" | "tamil" | "tanglish", gender: "female" | "male") => {
    /**
     * What does this function do:
     * Plays an instant voice sample in the selected language and gender (Female / Male) for operator evaluation.
     * Uses backend neural Edge-TTS with instant browser SpeechSynthesis fallback on error.
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

    const fallbackBrowserTestSpeech = () => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
      try {
        window.speechSynthesis.cancel();
        const config = selectOptimalVoice(testMsg, gender);
        const utterance = new SpeechSynthesisUtterance(testMsg);
        if (config.voice) utterance.voice = config.voice;
        utterance.lang = config.lang;
        utterance.rate = config.rate;
        utterance.pitch = config.pitch;
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn("[App] Browser test speech notice:", err);
      }
    };

    const ttsUrl = `http://localhost:8000/api/tts?text=${encodeURIComponent(testMsg)}&gender=${gender}&language=${lang}`;
    fetch(ttsUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`TTS fetch failed with status ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (!blob || blob.size < 100) throw new Error("Empty audio blob");
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        audio.preload = "auto";
        activeAudioRef.current = audio;
        audio.onended = () => URL.revokeObjectURL(audioUrl);
        audio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          fallbackBrowserTestSpeech();
        };
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch(() => {
            fallbackBrowserTestSpeech();
          });
        }
      })
      .catch((err) => {
        console.warn("[App] Backend TTS preview fallback:", err);
        fallbackBrowserTestSpeech();
      });
  };

  const handleCopyMessage = async (msgId: string, text?: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(msgId);
      setTimeout(() => {
        setCopiedMessageId((prev) => (prev === msgId ? null : prev));
      }, 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  const speakSpecificMessage = (text?: string) => {
    /**
     * What does this function do:
     * High-fidelity speech synthesizer supporting Tamil, Tanglish, and English with Male/Female voice selection.
     * Uses backend neural TTS (/api/tts) with low-latency memory buffer, with transparent fallback to browser SpeechSynthesis.
     * Strictly synchronizes voice requests using sequence counters and abort controllers to prevent overlapping voices.
     */
    if (!text) return;

    // 1. Invalidate any in-flight speech/TTS request
    const currentSeq = ++speechSeqRef.current;

    // 2. Abort any active TTS fetch immediately
    if (activeTtsAbortRef.current) {
      try {
        activeTtsAbortRef.current.abort();
      } catch (e) { }
      activeTtsAbortRef.current = null;
    }

    // 3. Clear keep-alive pulse interval
    if (speechPulseIntervalRef.current) {
      clearInterval(speechPulseIntervalRef.current);
      speechPulseIntervalRef.current = null;
    }
    activeUtteranceRef.current = null;

    // 4. Stop and clean up any playing Audio element
    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
        activeAudioRef.current.removeAttribute("src");
        activeAudioRef.current.load();
      } catch (e) { }
      activeAudioRef.current = null;
    }

    // 5. Cancel any browser speech synthesis immediately
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) { }
    }

    const cleaned = cleanTextForVoice(text);
    if (!cleaned) return;

    safeStopRecognition();

    let hasEnded = false;
    const resumeListening = () => {
      if (hasEnded || currentSeq !== speechSeqRef.current) return;
      hasEnded = true;
      if (speechPulseIntervalRef.current) {
        clearInterval(speechPulseIntervalRef.current);
        speechPulseIntervalRef.current = null;
      }
      activeUtteranceRef.current = null;
      activeAudioRef.current = null;
      isSpeakingRef.current = false;
      const nextState = isListeningDesiredRef.current ? "listening" : "idle";
      setAssistantState(nextState);
      syncVoiceStateToBackend(nextState, isListeningDesiredRef.current, false, false);
      if (isListeningDesiredRef.current) {
        setTimeout(safeStartRecognition, 300);
      }
    };

    const fallbackToSpeechSynthesis = () => {
      if (hasEnded || currentSeq !== speechSeqRef.current) return;

      if (!("speechSynthesis" in window)) {
        resumeListening();
        return;
      }

      try {
        window.speechSynthesis.cancel();
      } catch (e) { }

      const voiceConfig = selectOptimalVoice(cleaned);
      const utterance = new SpeechSynthesisUtterance(cleaned);
      activeUtteranceRef.current = utterance;
      utterance.lang = voiceConfig.lang;
      utterance.rate = voiceConfig.rate;
      utterance.pitch = voiceConfig.pitch;
      if (voiceConfig.voice) {
        utterance.voice = voiceConfig.voice;
      }

      utterance.onstart = () => {
        if (currentSeq !== speechSeqRef.current) {
          try { window.speechSynthesis.cancel(); } catch (e) { }
          return;
        }
        safeStopRecognition();
        isSpeakingRef.current = true;
        setAssistantState("speaking");

        // Chrome keep-alive pulse: prevents browser engine from pausing long speech after 15 seconds
        if (speechPulseIntervalRef.current) clearInterval(speechPulseIntervalRef.current);
        speechPulseIntervalRef.current = setInterval(() => {
          if (window.speechSynthesis && window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        }, 10000);

        syncVoiceStateToBackend("speaking", undefined, false, true);
      };

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

    // Maintain complete natural speech without aggressive mid-sentence cutoffs
    let speechInput = cleaned;
    if (speechInput.length > 3500) {
      const boundary = speechInput.slice(0, 3400).lastIndexOf(".");
      if (boundary > 500) {
        speechInput = speechInput.slice(0, boundary + 1);
      }
    }

    // 1. Primary: Studio-Grade Neural Edge TTS with strictly synchronized visual animations
    try {
      const gender = (profileRef.current.voice_gender || "female").toLowerCase();
      const isTamilScript = /[\u0B80-\u0BFF]/.test(speechInput);
      const userLang = (profileRef.current.language || "english").toLowerCase();
      const lang = isTamilScript ? "tamil" : (userLang === "tanglish" ? "tanglish" : (userLang === "tamil" ? "tamil" : "english"));
      const ttsUrl = `http://localhost:8000/api/tts?text=${encodeURIComponent(speechInput)}&gender=${gender}&language=${lang}`;

      const ttsAbort = new AbortController();
      activeTtsAbortRef.current = ttsAbort;
      let isFallbackTriggered = false;

      const triggerFastFallback = () => {
        if (isFallbackTriggered || hasEnded || currentSeq !== speechSeqRef.current) return;
        isFallbackTriggered = true;
        try { ttsAbort.abort(); } catch (e) { }
        fallbackToSpeechSynthesis();
      };

      // Fast 1.2s timeout: If neural network TTS takes longer than 1.2s, start instant local speech in <30ms
      const timeoutId = setTimeout(triggerFastFallback, 1200);

      fetch(ttsUrl, { signal: ttsAbort.signal })
        .then((res) => {
          clearTimeout(timeoutId);
          if (currentSeq !== speechSeqRef.current) return null;
          if (!res.ok || res.status === 204) {
            triggerFastFallback();
            return null;
          }
          return res.blob();
        })
        .then((blob) => {
          if (!blob || isFallbackTriggered || hasEnded || currentSeq !== speechSeqRef.current) return;
          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          audio.preload = "auto";
          activeAudioRef.current = audio;

          // Crucial: Only trigger visual "speaking" (blue circle & waves) the exact instant audio begins playing
          audio.onplay = () => {
            if (currentSeq !== speechSeqRef.current) {
              audio.pause();
              audio.removeAttribute("src");
              audio.load();
              try { URL.revokeObjectURL(audioUrl); } catch (e) { }
              return;
            }
            safeStopRecognition();
            isSpeakingRef.current = true;
            setAssistantState("speaking");
            syncVoiceStateToBackend("speaking", undefined, false, true);
          };

          audio.onended = () => {
            try { URL.revokeObjectURL(audioUrl); } catch (e) { }
            resumeListening();
          };

          audio.onerror = () => {
            try { URL.revokeObjectURL(audioUrl); } catch (e) { }
            if (currentSeq === speechSeqRef.current) {
              triggerFastFallback();
            }
          };

          audio.play().catch(() => {
            if (currentSeq === speechSeqRef.current) {
              triggerFastFallback();
            }
          });
        })
        .catch(() => {
          clearTimeout(timeoutId);
          if (currentSeq !== speechSeqRef.current) return;
          triggerFastFallback();
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
     * HALT BUTTON: Instantly aborts ongoing network requests, cancels all speech synthesis / audio playback,
     * resets thinking indicators, returns to listening mode, and synchronizes state with overlay HUD.
     */
    ++speechSeqRef.current;
    if (activeTtsAbortRef.current) {
      try { activeTtsAbortRef.current.abort(); } catch (e) { }
      activeTtsAbortRef.current = null;
    }
    if (speechPulseIntervalRef.current) {
      clearInterval(speechPulseIntervalRef.current);
      speechPulseIntervalRef.current = null;
    }
    activeUtteranceRef.current = null;

    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
        activeAudioRef.current.removeAttribute("src");
        activeAudioRef.current.load();
      } catch (e) { }
      activeAudioRef.current = null;
    }

    // Forcefully stop any other audio elements playing across the DOM
    try {
      document.querySelectorAll("audio").forEach((el) => {
        try {
          el.pause();
          el.currentTime = 0;
          el.removeAttribute("src");
          el.load();
        } catch (err) { }
      });
    } catch (e) { }

    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.pause();
        setTimeout(() => {
          try { window.speechSynthesis.cancel(); } catch (err) { }
        }, 50);
      } catch (e) { }
    }

    if (abortControllerRef.current) {
      try { abortControllerRef.current.abort(); } catch (e) { }
      abortControllerRef.current = null;
    }

    const nextState = isListeningDesiredRef.current ? "listening" : "idle";
    isSpeakingRef.current = false;
    setAssistantState(nextState);
    setIsThinking(false);
    addMessage("system", "EXECUTION HALTED BY OPERATOR.");

    // Synchronize stop state with backend and desktop overlay HUD immediately
    fetch("http://localhost:8000/api/v1/voice/stop", {
      method: "POST"
    }).catch(() => { });

    fetch("http://localhost:8000/api/v1/voice/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        state: nextState,
        is_speaking: false,
        is_thinking: false,
        is_listening: isListeningDesiredRef.current
      })
    }).catch(() => { });

    if (activeWsRef.current && activeWsRef.current.readyState === WebSocket.OPEN) {
      try {
        activeWsRef.current.send(JSON.stringify({
          action: "stop",
          is_listening: isListeningDesiredRef.current,
          is_speaking: false,
          is_thinking: false
        }));
      } catch (e) { }
    }

    if (isListeningDesiredRef.current) {
      setTimeout(safeStartRecognition, 300);
    }
  };

  // ---------------------------------------------------------------------------
  // 7. MESSAGE DISPATCH & DOCUMENT UPLOAD
  // ---------------------------------------------------------------------------

  const addMessage = async (sender: "user" | "friday" | "system", text: string) => {
    /**
     * What does this function do:
     * Appends a message to local state and persists it to the active memory session backend,
     * with debounced deduplication to prevent duplicate message bubbles.
     */
    const sanitizedText = sender === "friday" ? sanitizeDisplayMessage(text) : text;
    if (!sanitizedText && sender !== "system") return;

    const now = Date.now();
    if (
      lastMessageDedupeRef.current.sender === sender &&
      lastMessageDedupeRef.current.text === (sanitizedText || "Ready.") &&
      now - lastMessageDedupeRef.current.time < 1200
    ) {
      console.warn("[App] Debounced duplicate message addition:", sender, sanitizedText);
      return;
    }
    lastMessageDedupeRef.current = { sender, text: sanitizedText || "Ready.", time: now };

    const newMsgObj: Message = {
      id: Math.random().toString(36).substring(2, 9),
      sender,
      text: sanitizedText || "Ready.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    if (currentViewRef.current === "one-to-one") {
      setOneToOneMessages((prev) => [...prev, newMsgObj]);
      if (sender !== "system") {
        try {
          await fetch(`http://localhost:8000/api/v1/conversations/one_to_one/messages`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: sender === "user" ? "user" : "assistant", content: sanitizedText }),
          });
        } catch (e) { }
      }
      return;
    }

    setMessages((prev) => [...prev, newMsgObj]);

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
     * uploads (PDF, code, CSV, images) to /api/analyze-files with re-entrancy concurrency protection.
     */
    if (e) e.preventDefault();
    if (isSendingRef.current || isThinkingRef.current) return;

    const clean = (overrideText !== undefined ? overrideText : inputText).trim();
    if (!clean && selectedFiles.length === 0) return;

    isSendingRef.current = true;

    // Immediately stop and invalidate any speaking audio or speech synthesis
    ++speechSeqRef.current;
    if (activeTtsAbortRef.current) {
      try { activeTtsAbortRef.current.abort(); } catch (err) { }
      activeTtsAbortRef.current = null;
    }
    if (activeAudioRef.current) {
      try {
        activeAudioRef.current.pause();
        activeAudioRef.current.currentTime = 0;
        activeAudioRef.current.removeAttribute("src");
        activeAudioRef.current.load();
      } catch (err) { }
      activeAudioRef.current = null;
    }
    if ("speechSynthesis" in window) {
      try { window.speechSynthesis.cancel(); } catch (err) { }
    }
    isSpeakingRef.current = false;

    const filesToUpload = [...selectedFiles];
    const messagePayload = clean || `[Uploaded ${filesToUpload.length} file(s)]`;

    setInputText("");
    setSelectedFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (textareaRef.current) textareaRef.current.style.height = "24px";

    await addMessage("user", messagePayload);
    setAssistantState("thinking");
    setIsThinking(true);
    syncVoiceStateToBackend("thinking", undefined, true, false);

    abortControllerRef.current = new AbortController();

    const isTamilScript = /[\u0B80-\u0BFF]/.test(clean);
    const activeLang = isTamilScript ? "tamil" : (profileRef.current.language || selectedLanguage || "english");

    try {
      let res;
      if (filesToUpload.length > 0) {
        const formData = new FormData();
        filesToUpload.forEach((f) => formData.append("files", f));
        formData.append("prompt", messagePayload);
        formData.append("language", activeLang);
        const targetSession = currentViewRef.current === "one-to-one" ? "one_to_one" : (activeConversationId || "default");
        formData.append("session_id", targetSession);
        res = await fetch("http://localhost:8000/api/analyze-files", {
          method: "POST",
          body: formData,
          signal: abortControllerRef.current.signal,
        });
      } else {
        const targetSession = currentViewRef.current === "one-to-one" ? "one_to_one" : (activeConversationId || "default");
        res = await fetch("http://localhost:8000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: messagePayload,
            language: activeLang,
            session_id: targetSession,
          }),
          signal: abortControllerRef.current.signal,
        });
      }

      let rawReply = "Command executed.";
      try {
        const data = await res.json();
        rawReply = data?.response || data?.message || "Command executed.";
      } catch (jsonErr) {
        console.warn("[App] Response JSON parse notice:", jsonErr);
      }

      // Dispatch Internal Action Tags
      try {
        if (rawReply.includes("[[ACTION:")) {
          if (rawReply.includes("[[ACTION:OPEN_FRIDAY_MAP]]")) {
            setCurrentView("map");
          }
          if (rawReply.includes("[[ACTION:OPEN_SYSTEM_MONITOR]]") || rawReply.includes("[[ACTION:OPEN_SYSTEM_VIEW]]")) {
            setCurrentView("system");
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
          const langMatch = rawReply.match(/\[\[ACTION:SET_LANGUAGE:(english|tamil|tanglish)\]\]/i);
          if (langMatch) {
            const newLang = langMatch[1].toLowerCase() as "english" | "tamil" | "tanglish";
            profileRef.current.language = newLang;
            setProfile((prev) => ({ ...prev, language: newLang }));
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
      } catch (actionErr) {
        console.warn("[App] Action dispatcher notice:", actionErr);
      }

      const replyText = sanitizeDisplayMessage(rawReply);
      setIsThinking(false);
      if (currentViewRef.current === "one-to-one") {
        setLatestFridayResponse(replyText);
      }
      await addMessage("friday", replyText);
      if (!isGlobalMuted) {
        setAssistantState("speaking");
        isSpeakingRef.current = true;
        safeStopRecognition();
        syncVoiceStateToBackend("speaking", undefined, false, true);
        speakText(replyText, false);
      } else {
        const nextState = isListeningDesiredRef.current ? "listening" : "idle";
        setAssistantState(nextState);
        syncVoiceStateToBackend(nextState, isListeningDesiredRef.current, false, false);
      }
    } catch (err: any) {
      if (
        err?.name === "AbortError" ||
        err?.message?.toLowerCase().includes("aborted") ||
        err?.message?.toLowerCase().includes("canceled")
      ) {
        return; // Halted or superseded cleanly
      }
      console.error("[App] Dispatch error:", err);
      setIsThinking(false);
      const nextState = isListeningDesiredRef.current ? "listening" : "idle";
      setAssistantState(nextState);
      syncVoiceStateToBackend("error", false, false, false);
      addMessage("system", "Target connection failure.");
    } finally {
      abortControllerRef.current = null;
      isSendingRef.current = false;
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
      const res = await fetch("http://localhost:8000/api/add-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_name: addRoute.trim(), path: addPathLoc.trim() }),
      });
      const data = await res.json();
      setAddRoute("");
      setAddPathLoc("");
      if (data && data.paths) {
        setSavedPaths(data.paths);
      } else {
        fetchPaths();
      }
    } catch (e) {
      alert("Failed to add custom path.");
    }
  };

  const updateCustomPath = async (oldRouteName: string, newRouteName: string, newPath: string) => {
    if (!newRouteName.trim() || !newPath.trim()) return;
    try {
      const res = await fetch("http://localhost:8000/api/add-path", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_route_name: oldRouteName.trim(),
          new_route_name: newRouteName.trim(),
          path: newPath.trim()
        }),
      });
      const data = await res.json();
      if (data && data.paths) {
        setSavedPaths(data.paths);
      } else {
        fetchPaths();
      }
    } catch (e) {
      alert("Failed to update custom path.");
    }
  };

  const deleteCustomPath = async (routeName: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/add-path/${encodeURIComponent(routeName)}`, {
        method: "DELETE"
      });
      const data = await res.json();
      if (data && data.paths) {
        setSavedPaths(data.paths);
      } else {
        fetchPaths();
      }
    } catch (e) {
      alert("Failed to delete custom path.");
    }
  };

  const testCustomPath = async (path: string) => {
    if (!path.trim()) return;
    try {
      const res = await fetch("http://localhost:8000/api/test-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_name: "test", path: path.trim() }),
      });
      const data = await res.json();
      if (data && data.status === "error") {
        alert(data.message || "Failed to launch path.");
      }
    } catch (e) {
      alert("Error testing path execution.");
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
      const agent = settingsForm.agent_name || settingsForm.wake_word || "Friday";
      const wake = (settingsForm.wake_word || agent).trim().toLowerCase();
      const userName = settingsForm.name || "Harishan";
      const payload: UserProfile = {
        ...settingsForm,
        name: userName,
        agent_name: agent,
        wake_word: wake,
        profile: {
          name: userName,
          age: settingsForm.age || "",
          email: settingsForm.email || "",
          city: settingsForm.city || ""
        },
        agent_profile: {
          agent_name: agent,
          wake_word: wake
        }
      };

      await fetch("http://localhost:8000/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setProfile(payload);
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
        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <div className="jarvis-logo-area" style={{ paddingBottom: 0, borderBottom: "none", marginRight: "3px" }}>
            <div className="jarvis-logo-icon" style={{ width: "22px", height: "22px", fontSize: "9px" }}>▲</div>
            <div className="jarvis-logo-text" style={{ fontSize: "0.75rem" }}>{cleanAgentDisplay}</div>
          </div>

          <button
            onClick={() => {
              setCurrentView("home");
              setIsMapModalOpen(false);
            }}
            className="agent-brand-font"
            style={{
              fontFamily: "var(--font-eurostile)",
              fontStyle: "italic",
              background: currentView === "home" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.2))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "home" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.25)",
              color: currentView === "home" ? "#00f0ff" : "#94a3b8",
              borderRadius: "4px",
              padding: "2.5px 7px",
              height: "22px",
              fontSize: "7.5px",
              fontWeight: 800,
              letterSpacing: "0.4px",
              cursor: "pointer",
              boxShadow: currentView === "home" ? "0 0 8px rgba(0, 240, 255, 0.35), inset 0 0 4px rgba(0, 240, 255, 0.2)" : "none",
              transition: "all 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
            }}
          >
            ⌂ HOME
          </button>

          <button
            onClick={() => {
              setCurrentView("chat");
              setIsMapModalOpen(false);
            }}
            className="agent-brand-font"
            style={{
              fontFamily: "var(--font-eurostile)",
              fontStyle: "italic",
              background: currentView === "chat" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.35), rgba(0, 119, 255, 0.2))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "chat" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.25)",
              color: currentView === "chat" ? "#00f0ff" : "#94a3b8",
              borderRadius: "4px",
              padding: "2.5px 7px",
              height: "22px",
              fontSize: "7.5px",
              fontWeight: 800,
              letterSpacing: "0.4px",
              cursor: "pointer",
              boxShadow: currentView === "chat" ? "0 0 8px rgba(0, 240, 255, 0.35), inset 0 0 4px rgba(0, 240, 255, 0.2)" : "none",
              transition: "all 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
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
            className="agent-brand-font"
            style={{
              fontFamily: "var(--font-eurostile)",
              fontStyle: "italic",
              background: currentView === "map" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.3))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "map" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.35)",
              color: currentView === "map" ? "#00f0ff" : "#38bdf8",
              borderRadius: "4px",
              padding: "2.5px 7px",
              height: "22px",
              fontSize: "7.5px",
              fontWeight: 800,
              letterSpacing: "0.4px",
              cursor: "pointer",
              boxShadow: currentView === "map" ? "0 0 8px rgba(0, 240, 255, 0.45), inset 0 0 4px rgba(0, 240, 255, 0.2)" : "0 0 3px rgba(0, 240, 255, 0.15)",
              transition: "all 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
            }}
            title="Open Real Holographic Map (Street / City / Country)"
          >
            🌐 MAP
          </button>

          <button
            onClick={() => {
              setCurrentView("system");
              setIsMapModalOpen(false);
            }}
            className="agent-brand-font"
            style={{
              fontFamily: "var(--font-eurostile)",
              fontStyle: "italic",
              background: currentView === "system" ? "linear-gradient(135deg, rgba(0, 240, 255, 0.45), rgba(0, 119, 255, 0.3))" : "rgba(1, 4, 10, 0.7)",
              border: currentView === "system" ? "1px solid var(--jarvis-cyan)" : "1px solid rgba(0, 240, 255, 0.35)",
              color: currentView === "system" ? "#00f0ff" : "#38bdf8",
              borderRadius: "4px",
              padding: "2.5px 7px",
              height: "22px",
              fontSize: "7.5px",
              fontWeight: 800,
              letterSpacing: "0.4px",
              cursor: "pointer",
              boxShadow: currentView === "system" ? "0 0 8px rgba(0, 240, 255, 0.45), inset 0 0 4px rgba(0, 240, 255, 0.2)" : "0 0 3px rgba(0, 240, 255, 0.15)",
              transition: "all 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
            }}
            title="Open Live Full-Screen System Telemetry & Hardware Monitor"
          >
            ⚡ SYSTEM MONITOR
          </button>

          <button
            onClick={() => {
              setCurrentView("one-to-one");
              setIsMapModalOpen(false);
              fetchOneToOneMessages();
            }}
            className="agent-brand-font"
            style={{
              fontFamily: "var(--font-eurostile)",
              fontStyle: "italic",
              background: currentView === "one-to-one"
                ? "linear-gradient(135deg, rgba(236, 72, 153, 0.45), rgba(168, 85, 247, 0.35))"
                : "rgba(1, 4, 10, 0.7)",
              border: currentView === "one-to-one" ? "1px solid #ec4899" : "1px solid rgba(236, 72, 153, 0.35)",
              color: currentView === "one-to-one" ? "#f472b6" : "#e879f9",
              borderRadius: "4px",
              padding: "2.5px 7px",
              height: "22px",
              fontSize: "7.5px",
              fontWeight: 800,
              letterSpacing: "0.4px",
              cursor: "pointer",
              boxShadow: currentView === "one-to-one"
                ? "0 0 8px rgba(236, 72, 153, 0.45), inset 0 0 4px rgba(236, 72, 153, 0.2)"
                : "0 0 3px rgba(236, 72, 153, 0.15)",
              transition: "all 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
            }}
            title="Switch to One to One Direct Person-to-Person Conversation Mode (No Wake Word Required)"
          >
            🎙️ ONE TO ONE
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
          {currentView === "one-to-one" ? (
            /* Full Embedded One to One Direct Person-to-Person Conversation View */
            <div style={{ flex: 1, height: "100%", overflow: "hidden", display: "flex", flexDirection: "column", marginTop: "4px" }}>
              <OneToOneView
                onClose={() => setCurrentView("home")}
                profile={profile}
                assistantState={assistantState}
                isThinking={isThinking}
                isListening={isListening}
                isGlobalMuted={isGlobalMuted}
                onSendMessage={(txt) => handleSendMessage(undefined, txt)}
                onStopExecution={handleStopExecution}
                onToggleMic={() => {
                  if (isListening) {
                    safeStopRecognition();
                    isListeningDesiredRef.current = false;
                  } else {
                    isListeningDesiredRef.current = true;
                    safeStartRecognition();
                  }
                }}
                messages={oneToOneMessages}
                onClearHistory={clearOneToOneHistory}
                latestUserTranscript={latestUserTranscript}
                latestFridayResponse={latestFridayResponse}
              />
            </div>
          ) : currentView === "map" ? (
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
          ) : currentView === "system" ? (
            /* Full Embedded Live System Telemetry & Hardware Monitor View */
            <div style={{ flex: 1, height: "100%", overflow: "hidden", display: "flex", flexDirection: "column", marginTop: "4px" }}>
              <SystemMonitorView onClose={() => setCurrentView("home")} />
            </div>
          ) : (
            /* Dashboard Grid: When HOME or Terminal Minimized -> Full Central Friday Circle; When CHAT -> (If Maximized: 1fr; Else: 1.2fr 460px) */
            <div
              style={{
                flex: 1,
                display: "grid",
                gridTemplateColumns: currentView === "chat"
                  ? (isChatMaximized ? "1fr" : (isTerminalCollapsed ? "1fr auto" : "1.2fr 460px"))
                  : "1fr",
                gridTemplateRows: "1fr",
                gap: "12px",
                overflow: "hidden"
              }}
            >

              {/* Center Column: Friday Glowing Neural Core Circle (Hidden when Chat is Maximized in Chat View) */}
              {!(currentView === "chat" && isChatMaximized) && (
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

                  {(() => {
                    const isThinkingActive = isThinking || assistantState === "thinking";
                    const isSpeakingActive = assistantState === "speaking";
                    const isMicOn = isListeningDesiredRef.current || isListening || assistantState === "listening";
                    const isFullFridayDisplay = currentView === "home" || (currentView === "chat" && isTerminalCollapsed);

                    let theme: "yellow" | "red" | "blue" = "red";
                    if (isThinkingActive) {
                      theme = "yellow";
                    } else if (isSpeakingActive || isMicOn) {
                      theme = "blue";
                    } else {
                      theme = "red";
                    }

                    const ambientGlow = theme === "yellow"
                      ? "radial-gradient(circle at center, rgba(234, 179, 8, 0.22) 0%, rgba(1, 4, 9, 0.4) 70%)"
                      : theme === "blue"
                        ? (isFullFridayDisplay
                          ? "radial-gradient(circle at center, rgba(0, 140, 255, 0.15) 0%, rgba(1, 4, 9, 0.35) 70%)"
                          : "radial-gradient(circle at center, rgba(0, 140, 255, 0.08) 0%, rgba(1, 4, 9, 0.18) 70%)")
                        : (isFullFridayDisplay
                          ? "radial-gradient(circle at center, rgba(239, 68, 68, 0.15) 0%, rgba(1, 4, 9, 0.35) 70%)"
                          : "radial-gradient(circle at center, rgba(239, 68, 68, 0.08) 0%, rgba(1, 4, 9, 0.18) 70%)");

                    const sphereBorderColor = theme === "yellow"
                      ? "rgba(250, 204, 21, 0.95)"
                      : theme === "blue"
                        ? "rgba(0, 240, 255, 0.85)"
                        : "rgba(248, 113, 113, 0.85)";

                    const sphereBoxShadow = theme === "yellow"
                      ? "0 0 50px rgba(250, 204, 21, 0.6), inset 0 0 25px rgba(234, 179, 8, 0.45)"
                      : theme === "blue"
                        ? (isSpeakingActive
                          ? "0 0 50px rgba(0, 240, 255, 0.6), inset 0 0 25px rgba(0, 119, 255, 0.45)"
                          : "0 0 45px rgba(0, 240, 255, 0.45), inset 0 0 25px rgba(0, 119, 255, 0.35)")
                        : "0 0 50px rgba(239, 68, 68, 0.5), inset 0 0 25px rgba(239, 68, 68, 0.35)";

                    const sphereBackground = theme === "yellow"
                      ? "radial-gradient(circle at 50% 50%, rgba(234, 179, 8, 0.28) 0%, rgba(14, 11, 2, 0.96) 75%)"
                      : theme === "blue"
                        ? "radial-gradient(circle at 50% 50%, rgba(0, 140, 255, 0.22) 0%, rgba(1, 4, 10, 0.95) 75%)"
                        : "radial-gradient(circle at 50% 50%, rgba(239, 68, 68, 0.22) 0%, rgba(1, 4, 10, 0.95) 75%)";

                    const innerBorderColor = theme === "yellow"
                      ? "rgba(250, 204, 21, 0.55)"
                      : theme === "blue"
                        ? "rgba(0, 240, 255, 0.45)"
                        : "rgba(248, 113, 113, 0.6)";

                    const textColor = theme === "yellow"
                      ? "#facc15"
                      : theme === "blue"
                        ? "#00f0ff"
                        : "#f87171";

                    const textShadowColor = theme === "yellow"
                      ? "0 0 16px rgba(250, 204, 21, 0.95)"
                      : theme === "blue"
                        ? "0 0 16px rgba(0, 240, 255, 0.95)"
                        : "0 0 16px rgba(239, 68, 68, 0.95)";

                    const versionColor = theme === "yellow"
                      ? "#fef08a"
                      : theme === "blue"
                        ? "#94a3b8"
                        : "#fca5a5";

                    return (
                      <>
                        {/* Ambient Background Radial Glow */}
                        <div
                          style={{
                            position: "absolute",
                            inset: 0,
                            background: ambientGlow,
                            pointerEvents: "none",
                            zIndex: 1,
                            transition: "background 0.3s ease"
                          }}
                        />
                        <canvas ref={centerCanvasRef} width={460} height={460} style={{ position: "absolute", zIndex: 2, pointerEvents: "none" }} />

                        <div
                          className={`jarvis-sphere-container theme-${theme}`}
                          onClick={toggleListening}
                          style={{
                            zIndex: 2,
                            transform: isFullFridayDisplay ? "scale(1.22)" : "scale(1.05)",
                            transition: "all 0.3s ease",
                            cursor: "pointer",
                            borderColor: sphereBorderColor,
                            boxShadow: sphereBoxShadow,
                            background: sphereBackground
                          }}
                          title={
                            isThinkingActive
                              ? "⚡ Friday Thinking (Gold/Yellow)"
                              : isSpeakingActive
                                ? "🔊 Friday Speaking - Click to Pause Mic"
                                : isMicOn
                                  ? "🎙️ Mic ON (Blue) - Click to Turn OFF"
                                  : "🔇 Mic OFF (Red) - Click to Turn ON"
                          }
                        >
                          <div
                            style={{
                              position: "absolute",
                              inset: "14px",
                              borderRadius: "50%",
                              border: `1px solid ${innerBorderColor}`,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              background: "transparent",
                              transition: "all 0.3s ease"
                            }}
                          >
                            <div style={{ textAlign: "center" }}>
                              <div
                                className="agent-brand-font"
                                style={{
                                  fontFamily: "var(--font-eurostile)",
                                  fontWeight: 900,
                                  fontStyle: "italic",
                                  fontStretch: "expanded",
                                  letterSpacing: "3px",
                                  color: textColor,
                                  fontSize: "1.45rem",
                                  textShadow: textShadowColor,
                                  WebkitTextStroke: "1.5px currentColor",
                                  transition: "color 0.3s ease, text-shadow 0.3s ease",
                                  textTransform: "uppercase"
                                }}
                              >
                                {cleanAgentDisplay}
                              </div>
                              <div
                                className="agent-brand-font"
                                style={{
                                  fontFamily: "var(--font-eurostile)",
                                  fontStyle: "italic",
                                  fontStretch: "expanded",
                                  fontSize: "10px",
                                  color: textColor,
                                  textTransform: "uppercase",
                                  letterSpacing: "2px",
                                  marginTop: "4px",
                                  fontWeight: 800,
                                  transition: "color 0.3s ease"
                                }}
                              >
                                {isThinkingActive
                                  ? "⚡ THINKING"
                                  : isSpeakingActive
                                    ? "🔊 SPEAKING"
                                    : isMicOn
                                      ? "🎙️ LISTENING"
                                      : "🔇 MIC OFF"}
                              </div>
                              <div style={{ fontSize: "9px", color: versionColor, fontFamily: "monospace", marginTop: "2px" }}>v3.0.0</div>
                            </div>
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Right/Full Column: Terminal Stream (Quick Commands & Terminal - Only in CHAT AGENT view) */}
              {currentView === "chat" && (
                <div
                  className="jarvis-glass-card jarvis-panel-box"
                  style={{
                    height: isTerminalCollapsed ? "auto" : "100%",
                    alignSelf: isTerminalCollapsed ? "flex-start" : "stretch",
                    minWidth: isTerminalCollapsed ? "280px" : "auto",
                    transition: "all 0.3s ease",
                    display: "flex",
                    flexDirection: "column"
                  }}
                >
                  <div className="jarvis-panel-title">
                    <span>QUICK COMMANDS & TERMINAL</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <button
                        onClick={() => setIsChatMaximized((prev) => !prev)}
                        style={{
                          background: isChatMaximized ? "rgba(0, 240, 255, 0.35)" : "rgba(0, 119, 255, 0.2)",
                          border: "1px solid rgba(0, 240, 255, 0.45)",
                          color: "var(--jarvis-cyan)",
                          width: "22px",
                          height: "22px",
                          borderRadius: "3px",
                          cursor: "pointer",
                          fontSize: "12px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s ease"
                        }}
                        title={isChatMaximized ? "Restore Friday Neural Core View (Split View)" : "Maximize Chat Box to Full Width (Near Conversations)"}
                      >
                        {isChatMaximized ? "🗗" : "⛶"}
                      </button>
                      <button
                        onClick={() => setIsTerminalCollapsed((prev) => !prev)}
                        style={{
                          background: "rgba(0, 119, 255, 0.2)",
                          border: "1px solid rgba(0, 240, 255, 0.4)",
                          color: "var(--jarvis-cyan)",
                          width: "22px",
                          height: "22px",
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
                  </div>

                  {!isTerminalCollapsed && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1, overflow: "hidden" }}>
                      <div style={{ flex: 1, overflowY: "auto", background: "rgba(1, 4, 10, 0.85)", borderRadius: "4px", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px", fontSize: "11px", display: "flex", flexDirection: "column", gap: "6px" }}>
                        {messages.map((m) => (
                          <ChatMessageBubble
                            key={m.id}
                            m={m}
                            isCopied={copiedMessageId === m.id}
                            onCopy={handleCopyMessage}
                            onSpeak={speakSpecificMessage}
                          />
                        ))}

                        {isThinking && <ProcessingIndicator />}
                        <div ref={chatEndRef} />
                      </div>

                      {/* ChatGPT-style Unified Input Card (Textarea Top, Attach/Mic/Exec/Stop Below) */}
                      <form onSubmit={handleSendMessage} className="chatgpt-input-card">
                        {/* Top Multiline Textarea */}
                        <textarea
                          ref={textareaRef}
                          rows={1}
                          placeholder="Message Friday..."
                          value={inputText}
                          onChange={handleInputChange}
                          onKeyDown={handleTextareaKeyDown}
                          onPaste={handleTextareaPaste}
                          className="chatgpt-textarea"
                        />

                        {/* Staged Files Preview */}
                        {selectedFiles.length > 0 && (
                          <div className="chatgpt-staged-files">
                            <span style={{ fontSize: "9px", color: "var(--jarvis-cyan)", fontWeight: "bold", whiteSpace: "nowrap" }}>
                              STAGED ({selectedFiles.length}/6):
                            </span>
                            {selectedFiles.map((file, index) => (
                              <div key={index} className="chatgpt-file-pill">
                                <span style={{ maxWidth: "90px", overflow: "hidden", textOverflow: "ellipsis" }} title={file.name}>
                                  {file.name}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveFile(index)}
                                  title="Remove file"
                                >
                                  ✕
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Bottom Toolbar: Attachment on left, Mic, Exec, Stop on right */}
                        <div className="chatgpt-bottom-toolbar">
                          <div className="chatgpt-toolbar-left">
                            <button
                              type="button"
                              onClick={() => fileInputRef.current?.click()}
                              className="chatgpt-icon-btn"
                              title="Upload files (PDF, Code, Images, Text)"
                            >
                              <span style={{ fontSize: "16px", lineHeight: 1 }}>+</span>
                            </button>
                            <input type="file" multiple ref={fileInputRef} onChange={handleFileSelect} style={{ display: "none" }} />
                          </div>

                          <div className="chatgpt-toolbar-right">
                            {/* Microphone Toggle Button */}
                            <button
                              type="button"
                              onClick={toggleListening}
                              className={`chatgpt-icon-btn ${isListening ? "active" : "muted"}`}
                              title={isListening ? "🎙️ Mic Active (Listening) - Click to Mute" : "🔇 Mic Muted - Click to Activate"}
                            >
                              <span style={{ fontSize: "13px" }}>{isListening ? "🎙️" : "🔇"}</span>
                            </button>

                            {/* Execute / Send Button */}
                            <button
                              type="submit"
                              className="chatgpt-send-btn"
                              disabled={!inputText.trim() && selectedFiles.length === 0}
                              title="Execute (Enter)"
                            >
                              <span>EXEC</span>
                              <span style={{ fontSize: "13px", fontWeight: "bold" }}>↑</span>
                            </button>

                            {/* AUTHENTIC STOP EXECUTION BUTTON */}
                            <button
                              type="button"
                              onClick={handleStopExecution}
                              className="chatgpt-stop-btn"
                              title="Halt current execution & silence audio"
                            >
                              STOP
                            </button>
                          </div>
                        </div>
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
        updateCustomPath={updateCustomPath}
        deleteCustomPath={deleteCustomPath}
        testCustomPath={testCustomPath}
        fetchPaths={fetchPaths}
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
        isBox9Open={isBox9Open}
        setIsBox9Open={setIsBox9Open}
        overlaySettings={overlaySettings}
        isUpdatingOverlay={isUpdatingOverlay}
        fetchOverlaySettings={fetchOverlaySettings}
        updateOverlaySettings={updateOverlaySettings}
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