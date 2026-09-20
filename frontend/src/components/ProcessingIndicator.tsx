import React from "react";

/**
 * What does this component do:
 * Renders an animated JARVIS neural core processing pulse with glowing cyan and blue gradient
 * effects while Friday is actively thinking, recalling memory, or executing agent tools.
 */
export const ProcessingIndicator: React.FC = () => {
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
};
