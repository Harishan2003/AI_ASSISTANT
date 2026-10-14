"""
Friday AI Assistant - Authentic Central Neural Core Desktop Overlay HUD
========================================================================
A GPU-accelerated, transparent, frameless, always-on-top desktop widget for Windows.
Powered by Microsoft Edge WebView2 (pywebview) and pure HTML5 Canvas.
"""

import sys
import os
import json
import threading
import time
import ctypes
from pathlib import Path
import webview


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


OVERLAY_HWND = 0
OVERLAY_FORM = None
GLOBAL_WINDOW = None

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint
]
user32.SetWindowPos.restype = ctypes.c_bool
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_bool
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = ctypes.c_bool
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_longlong
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.IsWindow.restype = ctypes.c_bool


def get_overlay_hwnd():
    """Retrieve 64-bit HWND reliably via Form instance Handle or cached handle."""
    global OVERLAY_HWND, OVERLAY_FORM, GLOBAL_WINDOW
    try:
        if OVERLAY_FORM and hasattr(OVERLAY_FORM, "Handle"):
            h = int(OVERLAY_FORM.Handle.ToInt64())
            if h and user32.IsWindow(h):
                OVERLAY_HWND = h
                return h
    except Exception:
        pass
    if OVERLAY_HWND and user32.IsWindow(OVERLAY_HWND):
        return OVERLAY_HWND
    if GLOBAL_WINDOW and hasattr(GLOBAL_WINDOW, "native") and GLOBAL_WINDOW.native:
        try:
            h = int(GLOBAL_WINDOW.native.Handle.ToInt64())
            if h and user32.IsWindow(h):
                OVERLAY_HWND = h
                OVERLAY_FORM = GLOBAL_WINDOW.native
                return h
        except Exception:
            pass
    try:
        import webview.platforms.winforms as wf  # type: ignore
        for uid, form in list(wf.BrowserView.instances.items()):
            h = int(form.Handle.ToInt64())
            if h and user32.IsWindow(h):
                OVERLAY_HWND = h
                OVERLAY_FORM = form
                return h
    except Exception:
        pass
    return OVERLAY_HWND


TRANSPARENCY_APPLIED = False


def _apply_windows_transparency():
    """Apply DWM Glass, Form color-key transparency, and toolwindow styles on the UI thread."""
    global OVERLAY_HWND, OVERLAY_FORM, TRANSPARENCY_APPLIED
    if TRANSPARENCY_APPLIED:
        return
    for _ in range(40):
        applied = False
        try:
            import clr  # type: ignore
            clr.AddReference("System")
            clr.AddReference("System.Drawing")
            clr.AddReference("System.Windows.Forms")
            import System  # type: ignore
            import System.Drawing as drawing  # type: ignore
            import webview.platforms.winforms as wf  # type: ignore

            for uid, form in list(wf.BrowserView.instances.items()):
                hwnd = int(form.Handle.ToInt64())
                if not hwnd or not user32.IsWindow(hwnd):
                    continue
                OVERLAY_HWND = hwnd
                OVERLAY_FORM = form

                def ui_action():
                    global OVERLAY_HWND
                    try:
                        # Set Form background to pure Black without AllowTransparency (prevents handle recreation & E_ABORT)
                        form.BackColor = drawing.Color.Black
                        form.ShowInTaskbar = False
                        form.TopMost = True
                        h_fresh = int(form.Handle.ToInt64())
                        if h_fresh:
                            OVERLAY_HWND = h_fresh
                        margins = MARGINS(-1, -1, -1, -1)
                        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(h_fresh, ctypes.byref(margins))
                        GWL_EXSTYLE = -20
                        WS_EX_LAYERED = 0x00080000
                        WS_EX_TOOLWINDOW = 0x00000080
                        WS_EX_TOPMOST = 0x00000008
                        ex_style = ctypes.windll.user32.GetWindowLongW(h_fresh, GWL_EXSTYLE)
                        ctypes.windll.user32.SetWindowLongW(
                            h_fresh, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
                        )
                        # Set pure black (0x00000000) as the colorkey transparency key
                        ctypes.windll.user32.SetLayeredWindowAttributes(h_fresh, 0x00000000, 0, 1)
                    except Exception:
                        pass

                form.BeginInvoke(System.Action(ui_action))
                applied = True
                TRANSPARENCY_APPLIED = True
                break
        except Exception:
            pass

        if applied:
            break
        time.sleep(0.15)


OVERLAY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Friday Neural Core Overlay</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Michroma&family=Orbitron:ital,wght@0,500;0,700;0,800;0,900;1,500;1,700;1,800;1,900&family=Oxanium:ital,wght@0,600;0,700;0,800;1,700;1,800&family=Inter:ital,wght@0,400;0,600;0,700;1,400;1,600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    @font-face {
      font-family: 'Eurostile Extended';
      font-style: italic, oblique;
      font-weight: 700 900;
      src: local('Eurostile Extended Bold Italic'),
           local('Eurostile Extended-BoldItalic'),
           local('EurostileExtended-BoldItalic'),
           local('Eurostile Extended Bold'),
           local('Eurostile-BoldItalic'),
           local('Eurostile Bold Italic'),
           local('Microgramma Extended Bold Italic'),
           local('MicrogrammaBold-Italic');
      font-display: swap;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
      border: none !important;
      outline: none !important;
    }
    html, body {
      background: transparent !important;
      background-color: transparent !important;
      width: 100vw;
      height: 100vh;
      overflow: hidden !important;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: none !important;
    }
    #hud-container {
      position: relative;
      width: 280px;
      height: 280px;
      display: flex;
      align-items: center;
      justify-content: center;
      transform-origin: center center;
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease;
      cursor: grab;
      background: transparent !important;
      background-color: transparent !important;
      box-shadow: none !important;
    }
    #hud-container:active {
      cursor: grabbing;
    }
    #hud-canvas {
      width: 280px;
      height: 280px;
      display: block;
      background: transparent !important;
      background-color: transparent !important;
      box-shadow: none !important;
      border-radius: 50%;
      cursor: grab;
    }
    #hud-canvas:active {
      cursor: grabbing;
    }
    /* Context Menu */
    #ctx-menu {
      display: none;
      position: fixed;
      z-index: 99;
      background: rgba(1, 4, 10, 0.95);
      border: 1px solid rgba(0, 240, 255, 0.4) !important;
      border-radius: 8px;
      box-shadow: 0 0 20px rgba(0, 240, 255, 0.25) !important;
      padding: 6px 0;
      min-width: 140px;
      backdrop-filter: blur(8px);
    }
    .ctx-item {
      padding: 6px 14px;
      font-size: 11px;
      font-family: 'Inter', sans-serif;
      color: #94a3b8;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.2s, color 0.2s;
    }
    .ctx-item:hover {
      background: rgba(0, 240, 255, 0.15);
      color: #00f0ff;
    }
  </style>
</head>
<body>
  <div id="hud-container">
    <canvas id="hud-canvas" width="560" height="560"></canvas>
  </div>

  <div id="ctx-menu">
    <div class="ctx-item" id="menu-mic">🎙️ Toggle Mic</div>
    <div class="ctx-item" id="menu-reset">✥ Reset Position</div>
    <div class="ctx-item" id="menu-close" style="color: #f87171;">✕ Close Overlay</div>
  </div>

  <script>
    let state = "listening"; // "listening" | "speaking" | "thinking" | "idle" | "error"
    let isListening = true;
    let isSpeaking = false;
    let isThinking = false;
    let isError = false;
    let opacity = 1.0;
    let scale = 0.85;

    const container = document.getElementById("hud-container");
    const canvas = document.getElementById("hud-canvas");
    const ctx = canvas.getContext("2d");
    const ctxMenu = document.getElementById("ctx-menu");

    // Scale canvas context for 2x crisp rendering
    ctx.scale(2, 2);
    const W = 280;
    const H = 280;
    const cx = 140;
    const cy = 140;

    let angle = 0;
    let meshStep = 0;
    let spinAngle = 0;

    function drawSegmentedArc(radius, segments, gap, color, lineWidth, rot) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";

      const segAngle = (Math.PI * 2) / segments;
      for (let i = 0; i < segments; i++) {
        ctx.beginPath();
        ctx.arc(0, 0, radius, i * segAngle, (i + 1) * segAngle - gap);
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawCircularWaveMesh(isSpeakingActive, theme) {
      ctx.save();
      const numStrands = 28;
      const pointsPerRing = 130;
      const isThinkingActive = (theme === "yellow");
      const baseAmp = isSpeakingActive ? 16 : isThinkingActive ? 9 : 4.0;
      const speed = isSpeakingActive ? 0.055 : isThinkingActive ? 0.025 : 0.012;

      meshStep += speed;

      for (let s = 0; s < numStrands; s++) {
        const offsetFraction = (s / numStrands) - 0.5;
        const radiusOffset = offsetFraction * (isSpeakingActive ? 32 : 18);
        const baseR = 120 + radiusOffset;
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

        const alpha = Math.max(0.12, 1 - Math.abs(offsetFraction) * 1.8) * (isSpeakingActive ? 0.85 : isThinkingActive ? 0.92 : 0.35);
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

        if ((isSpeakingActive || isThinkingActive) && s % 5 === 0) {
          ctx.shadowColor = theme === "yellow" ? "#facc15" : theme === "blue" ? "#00f0ff" : "#ef4444";
          ctx.shadowBlur = 12;
        } else {
          ctx.shadowBlur = 0;
        }

        ctx.stroke();
      }
      ctx.restore();
    }

    function render() {
      ctx.clearRect(0, 0, W, H);

      const isSpeakingActive = isSpeaking || state === "speaking";
      const isThinkingActive = isThinking || state === "thinking";
      const isMicOn = isListening || state === "listening";
      const isErrorActive = isError || state === "error";

      let theme = "red";
      if (isErrorActive) {
        theme = "red";
      } else if (isThinkingActive) {
        theme = "yellow";
      } else if (isSpeakingActive || isMicOn) {
        theme = "blue";
      } else {
        theme = "red";
      }

      // Hit-test backing disc so entire circular core reliably catches clicks and drags.
      // Must be a solid, deep non-black tone so Windows LWA_COLORKEY (0x00000000)
      // does not treat it as transparent / click-through!
      ctx.beginPath();
      ctx.arc(cx, cy, 138, 0, Math.PI * 2);
      ctx.fillStyle = isErrorActive
        ? "#140202"
        : isThinkingActive
          ? "#140f02"
          : (isSpeakingActive || isMicOn)
            ? "#020712"
            : "#140202";
      ctx.fill();

      // 1. Concentric Segmented Rotating Neon Arcs
      const arcCol1 = theme === "yellow"
        ? "rgba(250, 204, 21, 0.95)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.88)"
          : "rgba(248, 113, 113, 0.88)";
      const arcCol2 = theme === "yellow"
        ? "rgba(234, 179, 8, 0.65)"
        : theme === "blue"
          ? "rgba(0, 140, 255, 0.45)"
          : "rgba(239, 68, 68, 0.45)";
      const arcCol3 = theme === "yellow"
        ? "rgba(250, 204, 21, 0.85)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.65)"
          : "rgba(248, 113, 113, 0.65)";
      const arcCol4 = theme === "yellow"
        ? "rgba(250, 204, 21, 0.95)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.95)"
          : "rgba(239, 68, 68, 0.95)";

      drawSegmentedArc(125, 4, 0.45, arcCol1, theme === "yellow" ? 2.6 : 2.5, angle * 0.6);
      drawSegmentedArc(112, 24, 0.08, arcCol2, 1.8, -angle * 0.8);
      drawSegmentedArc(96, 40, 0.05, arcCol3, theme === "yellow" ? 2.6 : 2.5, angle * 0.5);
      drawSegmentedArc(76, 8, 0.25, arcCol4, 1.8, -angle * 1.3);

      // 2. Rotational Wave Mesh
      drawCircularWaveMesh(isSpeakingActive, theme);

      // 3. Inner Friday Sphere Shell (Radius = 106px / Diameter = 212px)
      const rInner = 100;
      const sphereGrad = ctx.createRadialGradient(cx, cy, 8, cx, cy, rInner);
      if (theme === "yellow") {
        sphereGrad.addColorStop(0, "rgba(234, 179, 8, 0.28)");
        sphereGrad.addColorStop(0.75, "rgba(14, 11, 2, 0.96)");
      } else if (theme === "blue") {
        sphereGrad.addColorStop(0, "rgba(0, 140, 255, 0.22)");
        sphereGrad.addColorStop(0.75, "rgba(1, 4, 10, 0.95)");
      } else {
        sphereGrad.addColorStop(0, "rgba(239, 68, 68, 0.22)");
        sphereGrad.addColorStop(0.75, "rgba(18, 3, 3, 0.96)");
      }

      ctx.beginPath();
      ctx.arc(cx, cy, rInner, 0, Math.PI * 2);
      ctx.fillStyle = sphereGrad;
      ctx.fill();

      // Sphere Neon Border with Glow
      ctx.strokeStyle = theme === "yellow"
        ? "rgba(250, 204, 21, 0.95)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.85)"
          : "rgba(248, 113, 113, 0.85)";
      ctx.lineWidth = 2.0;
      ctx.shadowColor = theme === "yellow" ? "#facc15" : theme === "blue" ? "#00f0ff" : "#ef4444";
      ctx.shadowBlur = 14;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Rotating Dashed Accent Ring
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(spinAngle);
      ctx.beginPath();
      ctx.arc(0, 0, rInner + 4, 0, Math.PI * 2);
      ctx.strokeStyle = theme === "yellow"
        ? "rgba(250, 204, 21, 0.65)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.45)"
          : "rgba(248, 113, 113, 0.55)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([6, 6]);
      ctx.stroke();
      ctx.restore();

      // Inner Fine Border Ring
      ctx.beginPath();
      ctx.arc(cx, cy, rInner - 8, 0, Math.PI * 2);
      ctx.strokeStyle = theme === "yellow"
        ? "rgba(250, 204, 21, 0.55)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.45)"
          : "rgba(248, 113, 113, 0.6)";
      ctx.lineWidth = 1.0;
      ctx.stroke();

      // 4. Central Glowing Reactor Core
      const pulse = isSpeakingActive ? 1.6 : theme === "yellow" ? 1.35 : 1.0;
      const coreR = Math.max(10, 18 + Math.sin(angle * 6) * (2.5 * pulse));

      const radGrad = ctx.createRadialGradient(cx, cy, 1.5, cx, cy, coreR);
      radGrad.addColorStop(0, "#ffffff");
      radGrad.addColorStop(
        0.35,
        theme === "yellow" ? "#facc15" : theme === "blue" ? (isSpeakingActive ? "#38bdf8" : "#00f0ff") : "#ef4444"
      );
      radGrad.addColorStop(
        0.85,
        theme === "yellow" ? "rgba(234, 179, 8, 0.4)" : theme === "blue" ? "rgba(0, 119, 255, 0.35)" : "rgba(239, 68, 68, 0.35)"
      );
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fillStyle = radGrad;
      ctx.fill();

      // 5. Orbitron Typography & Status Text
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const textColor = theme === "yellow" ? "#facc15" : theme === "blue" ? "#00f0ff" : "#f87171";
      const textShadowColor = theme === "yellow"
        ? "rgba(250, 204, 21, 0.95)"
        : theme === "blue"
          ? "rgba(0, 240, 255, 0.95)"
          : "rgba(239, 68, 68, 0.95)";
      const versionColor = theme === "yellow" ? "#fef08a" : theme === "blue" ? "#94a3b8" : "#fca5a5";

      // "FRIDAY" - Eurostile Extended Bold Italic with bold stroke & glow
      ctx.save();
      if ("letterSpacing" in ctx) {
        ctx.letterSpacing = "3px";
      }
      ctx.font = "italic 900 23px 'Eurostile Extended', 'Eurostile', 'Microgramma Extended', 'Microgramma', 'Michroma', 'Orbitron', 'Oxanium', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = textColor;
      ctx.strokeStyle = textColor;
      ctx.lineWidth = 1.5;
      ctx.shadowColor = textShadowColor;
      ctx.shadowBlur = 18;
      ctx.strokeText("FRIDAY", cx, cy - 12);
      ctx.fillText("FRIDAY", cx, cy - 12);
      ctx.restore();

      // Status Badge - Eurostile Extended Bold Italic
      let statusLabel = "🎙️ LISTENING";
      if (isErrorActive) {
        statusLabel = "⚠️ ERROR";
      } else if (theme === "yellow") {
        statusLabel = "⚡ THINKING";
      } else if (isSpeakingActive) {
        statusLabel = "🔊 SPEAKING";
      } else if (isMicOn) {
        statusLabel = "🎙️ LISTENING";
      } else {
        statusLabel = "🔇 MIC OFF";
      }

      ctx.save();
      if ("letterSpacing" in ctx) {
        ctx.letterSpacing = "2px";
      }
      ctx.font = "italic 800 10px 'Eurostile Extended', 'Eurostile', 'Microgramma Extended', 'Microgramma', 'Michroma', 'Orbitron', 'Oxanium', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = textColor;
      ctx.shadowColor = textShadowColor;
      ctx.shadowBlur = 8;
      ctx.fillText(statusLabel, cx, cy + 22);
      ctx.restore();

      // Version
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.fillStyle = versionColor;
      ctx.fillText("v3.0.0", cx, cy + 40);

      // Increment animation speeds
      angle += isSpeakingActive ? 0.045 : theme === "yellow" ? 0.028 : 0.012;
      spinAngle += theme === "yellow" ? 0.03 : 0.008;

      requestAnimationFrame(render);
    }

    function toggleMic() {
      isListening = !isListening;
      state = isListening ? "listening" : "idle";
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ action: "toggle_mic" }));
        } catch (e) {}
      }
      fetch("http://localhost:8000/api/v1/voice/toggle-mic", { method: "POST" })
        .then(res => res.json())
        .then(data => {
          if (data && data.state) {
            state = data.state;
            isListening = Boolean(data.is_listening);
            isThinking = Boolean(data.is_thinking);
            isSpeaking = Boolean(data.is_speaking);
          }
        })
        .catch(() => {});
    }

    let isDragging = false;
    let hasMoved = false;
    let startScreenX = 0;
    let startScreenY = 0;
    let initScreenX = 0;
    let initScreenY = 0;

    const onPointerDown = (e) => {
      if (e.button !== 0) return;
      isDragging = true;
      hasMoved = false;
      try { canvas.setPointerCapture(e.pointerId); } catch(err) {}
      startScreenX = e.screenX;
      startScreenY = e.screenY;
      initScreenX = e.screenX;
      initScreenY = e.screenY;
    };

    canvas.addEventListener("pointerdown", onPointerDown);

    window.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      const dx = e.screenX - startScreenX;
      const dy = e.screenY - startScreenY;
      startScreenX = e.screenX;
      startScreenY = e.screenY;

      if (Math.hypot(e.screenX - initScreenX, e.screenY - initScreenY) > 3) {
        hasMoved = true;
        if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.drag_by === "function") {
          window.pywebview.api.drag_by(dx, dy);
        }
      }
    });

    const onPointerUp = (e) => {
      if (isDragging) {
        if (!hasMoved && e.button === 0) {
          toggleMic();
        } else if (hasMoved) {
          if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.save_current_position === "function") {
            window.pywebview.api.save_current_position();
          }
        }
      }
      isDragging = false;
      hasMoved = false;
      try { canvas.releasePointerCapture(e.pointerId); } catch(err) {}
    };

    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);

    // Right click menu
    window.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      ctxMenu.style.display = "block";
      ctxMenu.style.left = `${Math.min(e.clientX, window.innerWidth - 150)}px`;
      ctxMenu.style.top = `${Math.min(e.clientY, window.innerHeight - 110)}px`;
    });

    window.addEventListener("click", () => {
      ctxMenu.style.display = "none";
    });

    document.getElementById("menu-mic").addEventListener("click", () => {
      ctxMenu.style.display = "none";
      toggleMic();
    });

    document.getElementById("menu-reset").addEventListener("click", () => {
      ctxMenu.style.display = "none";
      fetch("http://localhost:8000/api/v1/settings/desktop-overlay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset_position: true })
      }).catch(() => {});
    });

    document.getElementById("menu-close").addEventListener("click", () => {
      fetch("http://localhost:8000/api/v1/settings/desktop-overlay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: false })
      }).catch(() => {});
    });

    // Real-time synchronization loop with timeout and error resilience
    let isSyncing = false;
    async function syncLoop() {
      if (isSyncing) return;
      isSyncing = true;
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 1200);

        const [res, sRes] = await Promise.all([
          fetch("http://localhost:8000/api/v1/settings/desktop-overlay", { signal: ctrl.signal }).catch(() => null),
          fetch("http://localhost:8000/api/v1/voice/state", { signal: ctrl.signal }).catch(() => null)
        ]);
        clearTimeout(tid);

        if (res && res.ok) {
          const cfg = await res.json().catch(() => null);
          if (cfg) {
            if (cfg.opacity !== undefined && Math.abs(cfg.opacity - opacity) > 0.01) {
              opacity = cfg.opacity;
              container.style.opacity = opacity;
            }
            if (cfg.scale !== undefined && Math.abs(cfg.scale - scale) > 0.01) {
              scale = cfg.scale;
              container.style.transform = `scale(${scale})`;
            }
          }
        }

        if (sRes && sRes.ok) {
          const sData = await sRes.json().catch(() => null);
          if (sData) {
            if (sData.state) {
              state = sData.state;
              if (state === "listening" || state === "idle") {
                isThinking = false;
                isSpeaking = false;
                isError = false;
              } else if (state === "thinking") {
                isThinking = true;
                isSpeaking = false;
              } else if (state === "speaking") {
                isSpeaking = true;
                isThinking = false;
              }
            }
            if (sData.is_listening !== undefined) isListening = Boolean(sData.is_listening);
            if (sData.is_thinking !== undefined) isThinking = Boolean(sData.is_thinking);
            if (sData.is_speaking !== undefined) isSpeaking = Boolean(sData.is_speaking);
          }
        }
      } catch (e) {
        // Silently swallow transient network drops during backend reloads
      } finally {
        isSyncing = false;
      }
    }

    // Connect WebSocket with 0ms live broadcast listener and exponential backoff
    let ws = null;
    let wsRetryDelay = 1000;
    let wsReconnectTimer = null;

    function connectWS() {
      if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
      try {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
          return;
        }
        ws = new WebSocket("ws://localhost:8000/ws/voice");

        ws.onopen = () => {
          wsRetryDelay = 1000;
          syncLoop();
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "state" && msg.data) {
              state = msg.data;
              isThinking = (state === "thinking");
              isSpeaking = (state === "speaking");
              isError = (state === "error");
              if (state === "listening" || state === "idle") {
                isThinking = false;
                isSpeaking = false;
                isError = false;
              }
              if (msg.is_listening !== undefined) {
                isListening = Boolean(msg.is_listening);
              }
              if (msg.is_thinking !== undefined) {
                isThinking = Boolean(msg.is_thinking);
              }
              if (msg.is_speaking !== undefined) {
                isSpeaking = Boolean(msg.is_speaking);
              }
            } else if (msg.type === "mic_toggled") {
              isListening = Boolean(msg.is_listening);
              state = msg.state || (isListening ? "listening" : "idle");
              isThinking = false;
              isSpeaking = false;
              isError = false;
            }
          } catch (err) {}
        };

        ws.onerror = () => {
          try { ws.close(); } catch (err) {}
        };

        ws.onclose = () => {
          wsReconnectTimer = setTimeout(() => {
            wsRetryDelay = Math.min(wsRetryDelay * 1.5, 5000);
            connectWS();
          }, wsRetryDelay);
        };
      } catch (err) {
        wsReconnectTimer = setTimeout(() => {
          wsRetryDelay = Math.min(wsRetryDelay * 1.5, 5000);
          connectWS();
        }, wsRetryDelay);
      }
    }

    connectWS();
    setInterval(syncLoop, 500);
    render();
  </script>
</body>
</html>
"""


class DesktopOverlayApi:
    """Clean JS bridge with only callable methods (no window/controller references)."""

    def move_window(self, x, y):
        """Move the overlay window to specific screen coordinates."""
        hwnd = get_overlay_hwnd()
        if hwnd:
            try:
                target_x = int(round(x))
                target_y = int(round(y))
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_NOACTIVATE = 0x0010
                user32.SetWindowPos(
                    hwnd, 0, target_x, target_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                )
            except Exception:
                pass

    def drag_by(self, dx, dy):
        """Move window by delta offset."""
        hwnd = get_overlay_hwnd()
        if hwnd:
            try:
                rect = RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    new_x = int(rect.left + dx)
                    new_y = int(rect.top + dy)
                    SWP_NOSIZE = 0x0001
                    SWP_NOZORDER = 0x0004
                    SWP_NOACTIVATE = 0x0010
                    user32.SetWindowPos(
                        hwnd, 0, new_x, new_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                    )
            except Exception:
                pass

    def save_current_position(self):
        """Save current window coordinates to overlay_config.json."""
        hwnd = get_overlay_hwnd()
        if hwnd:
            try:
                rect = RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    self._save_position(rect.left, rect.top)
            except Exception:
                pass

    def _save_position(self, x, y):
        """Persist new position to overlay_config.json so it is remembered."""
        try:
            cand1 = Path(__file__).resolve().parent / "database" / "overlay_config.json"
            cand2 = Path(__file__).resolve().parent.parent / "database" / "overlay_config.json"
            cfg_path = cand2 if cand2.exists() else cand1
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["position"] = {"x": int(x), "y": int(y)}
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
        except Exception:
            pass


class DesktopOverlayController:
    def __init__(self):
        self.window = None
        self.running = True
        cand1 = Path(__file__).resolve().parent / "database" / "overlay_config.json"
        cand2 = Path(__file__).resolve().parent.parent / "database" / "overlay_config.json"
        self.config_file = cand2 if cand2.exists() else cand1

    def run(self):
        # Calculate optimal top-right screen positioning or restore saved position
        init_x = 1150
        init_y = 40
        try:
            cand1 = Path(__file__).resolve().parent / "database" / "overlay_config.json"
            cand2 = Path(__file__).resolve().parent.parent / "database" / "overlay_config.json"
            cfg_path = cand2 if cand2.exists() else cand1
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "position" in cfg and isinstance(cfg["position"], dict):
                    init_x = int(cfg["position"].get("x", init_x))
                    init_y = int(cfg["position"].get("y", init_y))
            else:
                screens = webview.screens
                primary = screens[0] if screens else None
                screen_w = primary.width if primary else 1536
                init_x = max(20, screen_w - 340)
                init_y = 40
        except Exception:
            pass

        self.window = webview.create_window(
            title="Friday AI Assistant - Neural Core Overlay",
            html=OVERLAY_HTML,
            width=280,
            height=280,
            x=init_x,
            y=init_y,
            frameless=True,
            shadow=False,
            on_top=True,
            transparent=True,
            easy_drag=False,
            js_api=DesktopOverlayApi()
        )
        global GLOBAL_WINDOW
        GLOBAL_WINDOW = self.window

        def on_loaded():
            threading.Thread(target=_apply_windows_transparency, daemon=True).start()

        self.window.events.loaded += on_loaded

        # Safe fallback trigger after WebView2 initialization completes
        def fallback_transparency():
            time.sleep(2.5)
            _apply_windows_transparency()

        threading.Thread(target=fallback_transparency, daemon=True).start()

        # Background thread to monitor config file for reset position or close requests
        threading.Thread(target=self._monitor_config, daemon=True).start()

        # Start WebView2 engine
        webview.start(gui="edgechromium")

    def _monitor_config(self):
        # Allow a 4.0s startup grace period for WebView2 to fully initialize
        time.sleep(4.0)
        while self.running:
            try:
                cand1 = Path(__file__).resolve().parent / "database" / "overlay_config.json"
                cand2 = Path(__file__).resolve().parent.parent / "database" / "overlay_config.json"
                cfg_path = cand2 if cand2.exists() else cand1

                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)

                    # Handle position reset
                    if cfg.get("reset_position", False):
                        try:
                            screens = webview.screens
                            primary = screens[0] if screens else None
                            screen_w = primary.width if primary else 1536
                            target_x = max(20, screen_w - 340)
                            target_y = 40
                            if OVERLAY_HWND:
                                SWP_NOSIZE = 0x0001
                                SWP_NOZORDER = 0x0004
                                SWP_NOACTIVATE = 0x0010
                                ctypes.windll.user32.SetWindowPos(
                                    OVERLAY_HWND, 0, target_x, target_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                                )
                            elif self.window:
                                self.window.move(target_x, target_y)
                        except Exception:
                            pass

                        # Clear reset flag
                        cfg["reset_position"] = False
                        try:
                            with open(cfg_path, "w", encoding="utf-8") as f:
                                json.dump(cfg, f, indent=2)
                        except Exception:
                            pass

                    # Handle shutdown if explicitly disabled after startup
                    if cfg.get("enabled") is False and self.window:
                        self.running = False
                        self.window.destroy()
                        break
            except Exception:
                pass
            time.sleep(4.0)


if __name__ == "__main__":
    controller = DesktopOverlayController()
    controller.run()
