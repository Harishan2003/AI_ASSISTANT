import React from "react";
import type { UrgentAlert } from "../types/assistant";

interface UrgentAlertBannerProps {
  alert: UrgentAlert | null;
  onCallSender: (sender: string) => void;
  onDismiss: () => void;
}

/**
 * What does this component do:
 * Renders a glowing red emergency alert notification banner across the top of the interface
 * when Friday detects an urgent WhatsApp message requiring Harishan's immediate voice/action.
 * Provides quick '📞 Call Now' and 'Dismiss' buttons.
 */
export const UrgentAlertBanner: React.FC<UrgentAlertBannerProps> = ({
  alert,
  onCallSender,
  onDismiss,
}) => {
  if (!alert) return null;

  return (
    <div
      style={{
        background: "linear-gradient(90deg, rgba(239, 68, 68, 0.95), rgba(185, 28, 28, 0.95))",
        border: "1px solid #f87171",
        borderRadius: "6px",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: "0 0 20px rgba(239, 68, 68, 0.6)",
        marginBottom: "4px"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#fff" }}>
        <span style={{ fontSize: "18px" }}>🚨</span>
        <div>
          <div style={{ fontWeight: "bold", fontSize: "12px", textTransform: "uppercase", letterSpacing: "1px", color: "#fff" }}>
            URGENT WHATSAPP FROM {alert.sender}
          </div>
          <div style={{ fontSize: "11px", opacity: 0.95, color: "#fef2f2" }}>"{alert.message}"</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: "8px" }}>
        <button
          onClick={() => onCallSender(alert.sender)}
          style={{
            background: "#fff",
            color: "#b91c1c",
            border: "none",
            borderRadius: "4px",
            padding: "4px 10px",
            fontSize: "11px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          📞 Call Now
        </button>
        <button
          onClick={onDismiss}
          style={{
            background: "rgba(0, 0, 0, 0.3)",
            color: "#fff",
            border: "1px solid rgba(255, 255, 255, 0.4)",
            borderRadius: "4px",
            padding: "4px 10px",
            fontSize: "11px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
};
