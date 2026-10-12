import React from "react";
import type {
  UserProfile,
  PowerSettings,
  BatteryState,
  WhatsAppSettings,
  WhatsAppLog,
  FeatureScanResult,
  DeviceMonitoringSettings,
  DesktopOverlaySettings
} from "../types/assistant";


interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;

  // Box states
  isBox1Open: boolean;
  setIsBox1Open: (open: boolean) => void;
  isBox2Open: boolean;
  setIsBox2Open: (open: boolean) => void;
  isBox3Open: boolean;
  setIsBox3Open: (open: boolean) => void;
  isBox4Open: boolean;
  setIsBox4Open: (open: boolean) => void;
  isBoxScanOpen: boolean;
  setIsBoxScanOpen: (open: boolean) => void;
  isBox6Open: boolean;
  setIsBox6Open: (open: boolean) => void;
  isBox7Open: boolean;
  setIsBox7Open: (open: boolean) => void;
  isBox8Open?: boolean;
  setIsBox8Open?: (open: boolean) => void;

  // Profile data & actions

  settingsForm: UserProfile;
  setSettingsForm: React.Dispatch<React.SetStateAction<UserProfile>>;
  saveUserProfile: () => void;

  // Lock security
  masterPasswordInput: string;
  setMasterPasswordInput: (pwd: string) => void;
  isLockAuthenticated: boolean;
  verifyMasterPassword: () => void;
  lockMappings: { keyword: string; password: string }[];
  setLockMappings: React.Dispatch<React.SetStateAction<{ keyword: string; password: string }[]>>;
  saveLockConfig: () => void;

  // Master setup
  newMasterPasswordInput: string;
  setNewMasterPasswordInput: (pwd: string) => void;
  saveMasterPassword: () => void;

  // Custom paths
  savedPaths: { route_name: string; path: string }[];
  addRoute: string;
  setAddRoute: (val: string) => void;
  addPathLoc: string;
  setAddPathLoc: (val: string) => void;
  addCustomPath: () => void;
  updateCustomPath?: (oldRouteName: string, newRouteName: string, newPath: string) => void;
  deleteCustomPath: (routeName: string) => void;
  testCustomPath?: (path: string) => void;
  fetchPaths?: () => void;

  // Feature scanner
  isScanningFeatures: boolean;
  featureScanResults: FeatureScanResult[];
  featureSearchQuery: string;
  setFeatureSearchQuery: (query: string) => void;
  runFeatureScan: () => void;

  // WhatsApp
  whatsappSettings: WhatsAppSettings;
  customAutoReplyText: string;
  setCustomAutoReplyText: (text: string) => void;
  whatsappRecipient: string;
  setWhatsappRecipient: (recipient: string) => void;
  whatsappMsgText: string;
  setWhatsappMsgText: (msg: string) => void;
  whatsappLogs: WhatsAppLog[];
  isSendingWhatsApp: boolean;
  isUpdatingWhatsApp: boolean;
  fetchWhatsAppSettings: () => void;
  updateWhatsAppSettings: (enabled: boolean, auto_reply: boolean, custom_msg?: string) => void;
  sendTestWhatsAppMessage: () => void;

  // Power & Battery
  powerSettings: PowerSettings;
  batteryState: BatteryState | null;
  isEcoActive: boolean;
  isUpdatingPower: boolean;
  fetchPowerSettings: () => void;
  updatePowerSettings: (eco: boolean, autoBattery: boolean) => void;

  // Device Monitoring
  deviceSettings?: DeviceMonitoringSettings;
  isUpdatingDevice?: boolean;
  fetchDeviceSettings?: () => void;
  updateDeviceSettings?: (enabled: boolean) => void;

  // Box 9: Desktop HUD Overlay
  isBox9Open?: boolean;
  setIsBox9Open?: (open: boolean) => void;
  overlaySettings?: DesktopOverlaySettings;
  isUpdatingOverlay?: boolean;
  fetchOverlaySettings?: () => void;
  updateOverlaySettings?: (opts: Partial<DesktopOverlaySettings>) => void;

  // Voice test
  onTestVoice?: (lang: "english" | "tamil" | "tanglish", gender: "female" | "male") => void;
}


/**
 * What does this component do:
 * Renders the primary Settings Configuration Modal for Friday AI Assistant.
 * Contains 7 expandable setting modules:
 * 1. User Profile Details, Voice Changer & Multilingual Settings
 * 2. Lock Screen Security Mappings
 * 3. Friday Master Admin Auth
 * 4. Custom Local Paths & App Shortcuts
 * 5. Autonomous Feature Scanner
 * 6. WhatsApp Auto-Monitor & Autonomous Reply Engine
 * 7. Battery & Eco Power Saver Controls
 */
export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  isBox1Open,
  setIsBox1Open,
  isBox2Open,
  setIsBox2Open,
  isBox3Open,
  setIsBox3Open,
  isBox4Open,
  setIsBox4Open,
  isBoxScanOpen,
  setIsBoxScanOpen,
  isBox6Open,
  setIsBox6Open,
  isBox7Open,
  setIsBox7Open,
  isBox8Open = false,
  setIsBox8Open,
  settingsForm,
  setSettingsForm,
  saveUserProfile,
  onTestVoice,
  masterPasswordInput,
  setMasterPasswordInput,
  isLockAuthenticated,
  verifyMasterPassword,
  lockMappings,
  setLockMappings,
  saveLockConfig,
  newMasterPasswordInput,
  setNewMasterPasswordInput,
  saveMasterPassword,
  savedPaths,
  addRoute,
  setAddRoute,
  addPathLoc,
  setAddPathLoc,
  addCustomPath,
  updateCustomPath,
  deleteCustomPath,
  testCustomPath,
  fetchPaths,
  isScanningFeatures,
  featureScanResults,
  featureSearchQuery,
  setFeatureSearchQuery,
  runFeatureScan,
  whatsappSettings,
  customAutoReplyText,
  setCustomAutoReplyText,
  whatsappRecipient,
  setWhatsappRecipient,
  whatsappMsgText,
  setWhatsappMsgText,
  whatsappLogs,
  isSendingWhatsApp,
  isUpdatingWhatsApp,
  fetchWhatsAppSettings,
  updateWhatsAppSettings,
  sendTestWhatsAppMessage,
  powerSettings,
  batteryState,
  isEcoActive,
  isUpdatingPower,
  fetchPowerSettings,
  updatePowerSettings,
  deviceSettings,
  isUpdatingDevice,
  fetchDeviceSettings,
  updateDeviceSettings,
  isBox9Open,
  setIsBox9Open,
  overlaySettings,
  isUpdatingOverlay,
  fetchOverlaySettings,
  updateOverlaySettings
}) => {
  const [internalBox8Open, setInternalBox8Open] = React.useState(false);
  const box8State = isBox8Open !== undefined ? isBox8Open : internalBox8Open;
  const setBox8State = setIsBox8Open || setInternalBox8Open;

  const [internalBox9Open, setInternalBox9Open] = React.useState(false);
  const box9State = isBox9Open !== undefined ? isBox9Open : internalBox9Open;
  const setBox9State = setIsBox9Open || setInternalBox9Open;

  const [editingPathIdx, setEditingPathIdx] = React.useState<number | null>(null);
  const [editRouteName, setEditRouteName] = React.useState<string>("");
  const [editPathValue, setEditPathValue] = React.useState<string>("");
  const [pathSearchQuery, setPathSearchQuery] = React.useState<string>("");

  if (!isOpen) return null;

  return (
    <div className="jarvis-modal-overlay" onClick={onClose}>
      <div
        className="jarvis-glass-card jarvis-modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "650px", maxWidth: "92vw", maxHeight: "88vh", display: "flex", flexDirection: "column", padding: "16px" }}
      >

        {/* Modal Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(0, 240, 255, 0.2)", paddingBottom: "8px", marginBottom: "12px" }}>
          <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "14px", color: "var(--jarvis-cyan)", fontWeight: "bold", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>FRIDAY CONFIGURATION CENTER</span>
            {isEcoActive && (
              <span style={{ fontSize: "9px", background: "rgba(52, 211, 153, 0.2)", border: "1px solid #34d399", color: "#34d399", padding: "1px 6px", borderRadius: "10px" }}>
                🌱 ECO ACTIVE
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "16px", fontWeight: "bold" }}
          >
            ✕
          </button>
        </div>

        {/* Scrollable Accordion Container */}
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px", paddingRight: "4px" }}>

          {/* BOX 1: USER PROFILE, VOICE CHANGER & MULTILINGUAL SETTINGS */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(1, 4, 10, 0.6)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px" }}>
            <div onClick={() => setIsBox1Open(!isBox1Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>
                1. OPERATOR PROFILE, VOICE CHANGER & LANGUAGES
              </span>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox1Open ? "▼" : "▶"}</span>
            </div>
            {isBox1Open && (
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "9px", color: "#94a3b8" }}>Operator Name</label>
                    <input
                      type="text"
                      value={settingsForm.name}
                      onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })}
                      style={{ width: "100%", background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "11px" }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "9px", color: "#94a3b8" }}>Agent Name / Wake Word</label>
                    <input
                      type="text"
                      value={settingsForm.agent_name}
                      onChange={(e) => setSettingsForm({ ...settingsForm, agent_name: e.target.value })}
                      style={{ width: "100%", background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "11px" }}
                    />
                  </div>
                </div>

                {/* VOICE CHANGER (MALE / FEMALE VOICE SELECTION) */}
                <div style={{ padding: "8px", background: "rgba(0, 240, 255, 0.04)", border: "1px solid rgba(0, 240, 255, 0.2)", borderRadius: "4px" }}>
                  <div style={{ fontSize: "10px", color: "#00f0ff", fontWeight: "bold", marginBottom: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>🔊 VOICE CHANGER / SPEECH PERSONA</span>
                    <span style={{ fontSize: "9px", color: "var(--jarvis-cyan)" }}>
                      ACTIVE: {settingsForm.voice_gender === "male" ? "MALE 👨" : "FEMALE 👩"}
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    <button
                      type="button"
                      onClick={() => setSettingsForm({ ...settingsForm, voice_gender: "female" })}
                      style={{
                        padding: "6px 8px",
                        borderRadius: "4px",
                        border: `1px solid ${settingsForm.voice_gender === "female" ? "#00f0ff" : "rgba(255,255,255,0.15)"}`,
                        background: settingsForm.voice_gender === "female" ? "rgba(0, 240, 255, 0.2)" : "#010409",
                        color: settingsForm.voice_gender === "female" ? "#00f0ff" : "#94a3b8",
                        cursor: "pointer",
                        fontSize: "11px",
                        fontWeight: "bold",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px"
                      }}
                    >
                      👩 Female Voice {settingsForm.voice_gender === "female" && "✓"}
                    </button>

                    <button
                      type="button"
                      onClick={() => setSettingsForm({ ...settingsForm, voice_gender: "male" })}
                      style={{
                        padding: "6px 8px",
                        borderRadius: "4px",
                        border: `1px solid ${settingsForm.voice_gender === "male" ? "#00f0ff" : "rgba(255,255,255,0.15)"}`,
                        background: settingsForm.voice_gender === "male" ? "rgba(0, 240, 255, 0.2)" : "#010409",
                        color: settingsForm.voice_gender === "male" ? "#00f0ff" : "#94a3b8",
                        cursor: "pointer",
                        fontSize: "11px",
                        fontWeight: "bold",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px"
                      }}
                    >
                      👨 Male Voice {settingsForm.voice_gender === "male" && "✓"}
                    </button>
                  </div>

                  {/* Audio Preview Buttons */}
                  <div style={{ display: "flex", gap: "6px", marginTop: "8px", alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "9px", color: "#94a3b8" }}>Test Voice Output:</span>
                    <button
                      type="button"
                      onClick={() => onTestVoice && onTestVoice("english", settingsForm.voice_gender || "female")}
                      style={{ background: "rgba(0,240,255,0.1)", border: "1px solid rgba(0,240,255,0.3)", color: "#00f0ff", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                    >
                      🇬🇧 Test English
                    </button>
                    <button
                      type="button"
                      onClick={() => onTestVoice && onTestVoice("tamil", settingsForm.voice_gender || "female")}
                      style={{ background: "rgba(0,240,255,0.1)", border: "1px solid rgba(0,240,255,0.3)", color: "#00f0ff", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                    >
                      🇮🇳 Test தமிழ்
                    </button>
                    <button
                      type="button"
                      onClick={() => onTestVoice && onTestVoice("tanglish", settingsForm.voice_gender || "female")}
                      style={{ background: "rgba(0,240,255,0.1)", border: "1px solid rgba(0,240,255,0.3)", color: "#00f0ff", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                    >
                      🗣️ Test Tanglish
                    </button>
                  </div>
                </div>

                {/* MULTILINGUAL LANGUAGE SELECTION (MULTI-SELECT) */}
                <div style={{ padding: "8px", background: "rgba(0, 240, 255, 0.04)", border: "1px solid rgba(0, 240, 255, 0.2)", borderRadius: "4px" }}>
                  <div style={{ fontSize: "10px", color: "#00f0ff", fontWeight: "bold", marginBottom: "6px" }}>
                    🌐 ACTIVE LANGUAGES (USER CAN SELECT ONE OR MORE)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px" }}>
                    {[
                      { id: "english", label: "🇬🇧 English" },
                      { id: "tamil", label: "🇮🇳 Tamil (தமிழ்)" },
                      { id: "tanglish", label: "🗣️ Tanglish" },
                    ].map((lang) => {
                      const currentLangs = settingsForm.languages || ["english", "tamil", "tanglish"];
                      const isSelected = currentLangs.includes(lang.id);
                      return (
                        <label
                          key={lang.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            background: isSelected ? "rgba(0, 240, 255, 0.15)" : "#010409",
                            border: `1px solid ${isSelected ? "#00f0ff" : "rgba(255,255,255,0.1)"}`,
                            borderRadius: "4px",
                            padding: "6px 8px",
                            cursor: "pointer",
                            fontSize: "10px",
                            color: isSelected ? "#fff" : "#94a3b8"
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              let updated = [...currentLangs];
                              if (e.target.checked) {
                                if (!updated.includes(lang.id)) updated.push(lang.id);
                              } else {
                                if (updated.length > 1) {
                                  updated = updated.filter((l) => l !== lang.id);
                                }
                              }
                              const newPrimary = (settingsForm.language && updated.includes(settingsForm.language)) ? settingsForm.language : (updated[0] || "english");
                              setSettingsForm({ ...settingsForm, languages: updated, language: newPrimary });
                            }}
                            style={{ accentColor: "#00f0ff" }}
                          />
                          <span>{lang.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <button
                  onClick={saveUserProfile}
                  style={{ marginTop: "4px", padding: "6px", background: "linear-gradient(135deg, #00f0ff, #0284c7)", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer", fontSize: "10px", fontFamily: "'Orbitron', sans-serif" }}
                >
                  SAVE PROFILE, VOICE & LANGUAGE SETTINGS
                </button>
              </div>
            )}
          </div>

          {/* BOX 2: LOCK SCREEN SECURITY */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(1, 4, 10, 0.6)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px" }}>
            <div onClick={() => setIsBox2Open(!isBox2Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>2. LOCK SCREEN KEYWORD SECURITY</span>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox2Open ? "▼" : "▶"}</span>
            </div>
            {isBox2Open && (
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {!isLockAuthenticated ? (
                  <div style={{ display: "flex", gap: "6px" }}>
                    <input
                      type="password"
                      placeholder="Enter Master Password..."
                      value={masterPasswordInput}
                      onChange={(e) => setMasterPasswordInput(e.target.value)}
                      style={{ flex: 1, background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "11px" }}
                    />
                    <button onClick={verifyMasterPassword} style={{ padding: "4px 10px", background: "#00f0ff", color: "#010409", fontWeight: "bold", borderRadius: "4px", border: "none", cursor: "pointer", fontSize: "10px" }}>UNLOCK</button>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: "10px", color: "#34d399", marginBottom: "6px" }}>✓ Authenticated. Configure unlock keywords:</div>
                    {lockMappings.map((m, idx) => (
                      <div key={idx} style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                        <input
                          type="text"
                          placeholder="Keyword (e.g. unlock laptop)"
                          value={m.keyword}
                          onChange={(e) => {
                            const copy = [...lockMappings];
                            copy[idx].keyword = e.target.value;
                            setLockMappings(copy);
                          }}
                          style={{ flex: 1, background: "#010409", border: "1px solid rgba(0,240,255,0.2)", borderRadius: "4px", padding: "4px 6px", color: "#fff", fontSize: "10px" }}
                        />
                        <input
                          type="password"
                          placeholder="Password"
                          value={m.password}
                          onChange={(e) => {
                            const copy = [...lockMappings];
                            copy[idx].password = e.target.value;
                            setLockMappings(copy);
                          }}
                          style={{ flex: 1, background: "#010409", border: "1px solid rgba(0,240,255,0.2)", borderRadius: "4px", padding: "4px 6px", color: "#fff", fontSize: "10px" }}
                        />
                      </div>
                    ))}
                    <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
                      <button onClick={() => setLockMappings([...lockMappings, { keyword: "", password: "" }])} style={{ padding: "4px 8px", background: "#334155", color: "#fff", borderRadius: "4px", border: "none", fontSize: "9px", cursor: "pointer" }}>+ ADD MAPPING</button>
                      <button onClick={saveLockConfig} style={{ padding: "4px 8px", background: "#00f0ff", color: "#010409", fontWeight: "bold", borderRadius: "4px", border: "none", fontSize: "9px", cursor: "pointer" }}>SAVE SECURITY MAPPINGS</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* BOX 3: FRIDAY MASTER PASSWORD */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(1, 4, 10, 0.6)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px" }}>
            <div onClick={() => setIsBox3Open(!isBox3Open)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>3. MASTER ADMIN PASSWORD</span>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox3Open ? "▼" : "▶"}</span>
            </div>
            {isBox3Open && (
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <input
                  type="password"
                  placeholder="Set New Master Password..."
                  value={newMasterPasswordInput}
                  onChange={(e) => setNewMasterPasswordInput(e.target.value)}
                  style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "6px 8px", color: "#fff", fontSize: "11px" }}
                />
                <button
                  onClick={saveMasterPassword}
                  style={{ padding: "6px", background: "linear-gradient(135deg, #00f0ff, #0284c7)", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer", fontSize: "10px", fontFamily: "'Orbitron', sans-serif" }}
                >
                  UPDATE MASTER PASSWORD
                </button>
              </div>
            )}
          </div>

          {/* BOX 4: CUSTOM PATHS & APP SHORTCUTS */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(1, 4, 10, 0.6)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px" }}>
            <div
              onClick={() => {
                const nextState = !isBox4Open;
                setIsBox4Open(nextState);
                if (nextState && fetchPaths) {
                  fetchPaths();
                }
              }}
              style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>
                  4. CUSTOM PATHS & SHORTCUTS
                </span>
                <span style={{ fontSize: "9px", background: "rgba(0, 240, 255, 0.15)", border: "1px solid rgba(0, 240, 255, 0.3)", color: "#00f0ff", padding: "1px 6px", borderRadius: "10px" }}>
                  {savedPaths.length} Registered
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {fetchPaths && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      fetchPaths();
                    }}
                    title="Reload shortcuts from database/add_path.json"
                    style={{ background: "transparent", border: "1px solid rgba(0,240,255,0.3)", color: "#00f0ff", borderRadius: "4px", padding: "2px 6px", fontSize: "10px", cursor: "pointer" }}
                  >
                    ⟳ SYNC
                  </button>
                )}
                <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox4Open ? "▼" : "▶"}</span>
              </div>
            </div>

            {isBox4Open && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {/* Description info */}
                <div style={{ fontSize: "10px", color: "#94a3b8", borderLeft: "2px solid #00f0ff", paddingLeft: "8px" }}>
                  Configure voice keywords or custom alias routes mapping to any file, folder, or executable on your system. Linked with <code style={{ color: "#38bdf8", background: "#010409", padding: "1px 4px", borderRadius: "3px" }}>database/add_path.json</code>.
                </div>

                {/* ADD NEW PATH FORM */}
                <div style={{ background: "rgba(0, 240, 255, 0.03)", border: "1px dashed rgba(0, 240, 255, 0.25)", borderRadius: "6px", padding: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ fontSize: "10px", color: "#00f0ff", fontWeight: "bold", fontFamily: "'Orbitron', sans-serif" }}>+ REGISTER NEW SHORTCUT</div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    <input
                      type="text"
                      placeholder="Route Alias (e.g. harishan resume, gaming mouse)"
                      value={addRoute}
                      onChange={(e) => setAddRoute(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") addCustomPath(); }}
                      style={{ flex: 1, minWidth: "180px", background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "6px 8px", color: "#fff", fontSize: "10px" }}
                    />
                    <input
                      type="text"
                      placeholder="Target Path (e.g. C:\Users\Harishan\Desktop\Game.exe)"
                      value={addPathLoc}
                      onChange={(e) => setAddPathLoc(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") addCustomPath(); }}
                      style={{ flex: 1.5, minWidth: "220px", background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "6px 8px", color: "#fff", fontSize: "10px" }}
                    />
                    <button
                      onClick={addCustomPath}
                      style={{ padding: "6px 14px", background: "linear-gradient(135deg, #00f0ff, #0284c7)", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer", fontSize: "10px", fontFamily: "'Orbitron', sans-serif" }}
                    >
                      + ADD
                    </button>
                  </div>
                </div>

                {/* SEARCH FILTER */}
                {savedPaths.length > 3 && (
                  <input
                    type="text"
                    placeholder="Search existing shortcuts..."
                    value={pathSearchQuery}
                    onChange={(e) => setPathSearchQuery(e.target.value)}
                    style={{ background: "#010409", border: "1px solid rgba(0,240,255,0.2)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "10px" }}
                  />
                )}

                {/* EXISTING PATHS LIST */}
                {savedPaths.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "14px", color: "#64748b", fontSize: "10px", background: "rgba(1, 4, 10, 0.4)", borderRadius: "4px" }}>
                    No custom paths configured yet. Add your first file, folder, or application shortcut above.
                  </div>
                ) : (
                  <div style={{ maxHeight: "180px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", paddingRight: "2px" }}>
                    {savedPaths
                      .filter((p) => {
                        if (!pathSearchQuery.trim()) return true;
                        const q = pathSearchQuery.toLowerCase();
                        return (p.route_name || "").toLowerCase().includes(q) || (p.path || "").toLowerCase().includes(q);
                      })
                      .map((p, idx) => {
                        const isEditing = editingPathIdx === idx;
                        return (
                          <div
                            key={idx}
                            style={{
                              background: isEditing ? "rgba(0, 240, 255, 0.08)" : "rgba(1, 4, 10, 0.8)",
                              border: isEditing ? "1px solid #00f0ff" : "1px solid rgba(0, 240, 255, 0.18)",
                              borderRadius: "5px",
                              padding: "6px 8px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "4px"
                            }}
                          >
                            {isEditing ? (
                              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                <div style={{ display: "flex", gap: "6px" }}>
                                  <input
                                    type="text"
                                    value={editRouteName}
                                    onChange={(e) => setEditRouteName(e.target.value)}
                                    placeholder="Route Name"
                                    style={{ flex: 1, background: "#010409", border: "1px solid #00f0ff", borderRadius: "3px", padding: "4px 6px", color: "#fff", fontSize: "10px" }}
                                  />
                                  <input
                                    type="text"
                                    value={editPathValue}
                                    onChange={(e) => setEditPathValue(e.target.value)}
                                    placeholder="Target Path"
                                    style={{ flex: 1.8, background: "#010409", border: "1px solid #00f0ff", borderRadius: "3px", padding: "4px 6px", color: "#fff", fontSize: "10px" }}
                                  />
                                </div>
                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                                  <button
                                    onClick={() => {
                                      if (updateCustomPath) {
                                        updateCustomPath(p.route_name, editRouteName, editPathValue);
                                      }
                                      setEditingPathIdx(null);
                                    }}
                                    style={{ background: "#22c55e", color: "#010409", border: "none", borderRadius: "3px", padding: "3px 8px", fontSize: "9px", fontWeight: "bold", cursor: "pointer" }}
                                  >
                                    ✓ SAVE
                                  </button>
                                  <button
                                    onClick={() => setEditingPathIdx(null)}
                                    style={{ background: "#475569", color: "#fff", border: "none", borderRadius: "3px", padding: "3px 8px", fontSize: "9px", cursor: "pointer" }}
                                  >
                                    ✕ CANCEL
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
                                <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span style={{ color: "#00f0ff", fontWeight: "bold", fontSize: "10px" }}>{p.route_name}</span>
                                    <span style={{ fontSize: "8px", color: "#64748b", background: "rgba(255,255,255,0.05)", padding: "1px 4px", borderRadius: "2px" }}>
                                      open {p.route_name}
                                    </span>
                                  </div>
                                  <span style={{ color: "#94a3b8", fontSize: "9px", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.path}>
                                    {p.path}
                                  </span>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                  {testCustomPath && (
                                    <button
                                      onClick={() => testCustomPath(p.path)}
                                      title="Test Open in File Explorer / App"
                                      style={{ background: "rgba(0, 240, 255, 0.15)", border: "1px solid rgba(0, 240, 255, 0.3)", color: "#00f0ff", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                                    >
                                      ▶ OPEN
                                    </button>
                                  )}
                                  <button
                                    onClick={() => {
                                      setEditingPathIdx(idx);
                                      setEditRouteName(p.route_name);
                                      setEditPathValue(p.path);
                                    }}
                                    title="Edit Shortcut"
                                    style={{ background: "rgba(234, 179, 8, 0.15)", border: "1px solid rgba(234, 179, 8, 0.3)", color: "#eab308", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                                  >
                                    ✎ EDIT
                                  </button>
                                  <button
                                    onClick={() => {
                                      if (confirm(`Remove shortcut '${p.route_name}'?`)) {
                                        deleteCustomPath(p.route_name);
                                      }
                                    }}
                                    title="Delete Shortcut"
                                    style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#ef4444", borderRadius: "3px", padding: "2px 6px", fontSize: "9px", cursor: "pointer" }}
                                  >
                                    ✕
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* BOX 5: AGENT FEATURE SCANNER */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(1, 4, 10, 0.6)", border: "1px solid rgba(0, 240, 255, 0.25)", borderRadius: "6px" }}>
            <div onClick={() => setIsBoxScanOpen(!isBoxScanOpen)} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>5. AGENT FEATURE HEALTH SCANNER</span>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBoxScanOpen ? "▼" : "▶"}</span>
            </div>
            {isBoxScanOpen && (
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", gap: "6px" }}>
                  <input
                    type="text"
                    placeholder="Search scanned features..."
                    value={featureSearchQuery}
                    onChange={(e) => setFeatureSearchQuery(e.target.value)}
                    style={{ flex: 1, background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "10px" }}
                  />
                  <button onClick={runFeatureScan} disabled={isScanningFeatures} style={{ padding: "4px 10px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: isScanningFeatures ? "wait" : "pointer", fontSize: "10px" }}>
                    {isScanningFeatures ? "SCANNING..." : "RUN SCAN"}
                  </button>
                </div>
                {featureScanResults.length > 0 && (
                  <div style={{ maxHeight: "140px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {featureScanResults
                      .filter((f) => (f.feature_name || f.feature || "").toLowerCase().includes(featureSearchQuery.toLowerCase()))
                      .map((f, idx) => {
                        const name = f.feature_name || f.feature || "System Capability";
                        const st = (f.status || f.raw_status || "ONLINE").toUpperCase();
                        const isOk = st === "ONLINE" || st === "WORKING" || st === "OPTIMAL";
                        return (
                          <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#010409", border: "1px solid rgba(0,240,255,0.15)", padding: "4px 8px", borderRadius: "4px", fontSize: "9.5px" }}>
                            <span style={{ color: "#e2e8f0" }}>{name}</span>
                            <span style={{ color: isOk ? "#34d399" : "#f87171", fontWeight: "bold", fontSize: "9px" }}>
                              {isOk ? "● ONLINE" : "▲ FAILED"}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* BOX 6: WHATSAPP AUTO-MONITOR & AGENT PLUGIN */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(0, 119, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
            <div onClick={() => { setIsBox6Open(!isBox6Open); fetchWhatsAppSettings(); }} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>
                  6. WHATSAPP AUTO-MONITOR & AGENT PLUGIN
                </span>
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

                {/* Custom Auto-Reply Text */}
                <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "8px 10px", borderRadius: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ fontSize: "9.5px", color: "#38bdf8", fontWeight: "bold" }}>CUSTOM AUTO-REPLY TEMPLATE</div>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <input
                      type="text"
                      placeholder="e.g. I am currently occupied and will reply shortly."
                      value={customAutoReplyText}
                      onChange={(e) => setCustomAutoReplyText(e.target.value)}
                      style={{ flex: 1, background: "#010409", border: "1px solid rgba(0,240,255,0.3)", borderRadius: "4px", padding: "4px 8px", color: "#fff", fontSize: "10px" }}
                    />
                    <button
                      onClick={() => updateWhatsAppSettings(whatsappSettings.enabled, whatsappSettings.auto_reply, customAutoReplyText.trim())}
                      style={{ padding: "4px 10px", background: "#00f0ff", color: "#010409", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer", fontSize: "10px" }}
                    >
                      SAVE
                    </button>
                    <button
                      onClick={() => {
                        setCustomAutoReplyText("");
                        updateWhatsAppSettings(whatsappSettings.enabled, whatsappSettings.auto_reply, "");
                      }}
                      style={{ padding: "4px 10px", background: "rgba(248, 113, 113, 0.2)", color: "#f87171", fontWeight: "bold", border: "1px solid rgba(248, 113, 113, 0.4)", borderRadius: "4px", cursor: "pointer", fontSize: "10px" }}
                      title="Clear custom auto-reply template"
                    >
                      REMOVE
                    </button>
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
                    style={{ background: "#010409", border: "1px solid rgba(0, 240, 255, 0.3)", borderRadius: "4px", padding: "6px 8px", fontSize: "10px", color: "#fff", outline: "none" }}
                  />
                  <input
                    type="text"
                    placeholder="Message content..."
                    value={whatsappMsgText}
                    onChange={(e) => setWhatsappMsgText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") sendTestWhatsAppMessage(); }}
                    style={{ background: "#010409", border: "1px solid rgba(0, 240, 255, 0.3)", borderRadius: "4px", padding: "6px 8px", fontSize: "10px", color: "#fff", outline: "none" }}
                  />
                  <button
                    onClick={sendTestWhatsAppMessage}
                    disabled={isSendingWhatsApp}
                    style={{ padding: "6px 12px", background: isSendingWhatsApp ? "rgba(0, 240, 255, 0.2)" : "#00f0ff", color: isSendingWhatsApp ? "#00f0ff" : "#010409", fontWeight: "bold", fontFamily: "'Orbitron', sans-serif", fontSize: "10px", borderRadius: "4px", border: "none", cursor: isSendingWhatsApp ? "wait" : "pointer" }}
                  >
                    {isSendingWhatsApp ? "⚡ DISPATCHING..." : "▶ SEND WHATSAPP MESSAGE"}
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
                          {log.reply && <div style={{ color: "#34d399", paddingLeft: "8px", fontStyle: "italic" }}>🤖 Auto-Reply: {log.reply}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* BOX 7: BATTERY & ECO POWER SAVER */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(52, 211, 153, 0.35)", borderRadius: "6px" }}>
            <div onClick={() => { setIsBox7Open(!isBox7Open); fetchPowerSettings(); }} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>
                  7. BATTERY & ECO POWER SAVER
                </span>
                <span style={{
                  fontSize: "9px",
                  padding: "1px 6px",
                  borderRadius: "10px",
                  background: isEcoActive ? "rgba(52, 211, 153, 0.2)" : "rgba(148, 163, 184, 0.2)",
                  border: `1px solid ${isEcoActive ? "#34d399" : "#64748b"}`,
                  color: isEcoActive ? "#34d399" : "#94a3b8"
                }}>
                  {isEcoActive ? "⚡ ECO ACTIVE" : "🔋 STANDARD POWER"}
                </span>
                {batteryState && (
                  <span style={{
                    fontSize: "9px",
                    padding: "1px 6px",
                    borderRadius: "10px",
                    background: batteryState.power_plugged ? "rgba(56, 189, 248, 0.2)" : "rgba(251, 191, 36, 0.2)",
                    border: `1px solid ${batteryState.power_plugged ? "#38bdf8" : "#fbbf24"}`,
                    color: batteryState.power_plugged ? "#38bdf8" : "#fbbf24"
                  }}>
                    {batteryState.power_plugged ? `⚡ AC PLUGGED (${batteryState.percent}%)` : `🔋 ON BATTERY (${batteryState.percent}%)`}
                  </span>
                )}
              </div>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{isBox7Open ? "▼" : "▶"}</span>
            </div>

            {isBox7Open && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {/* Controls Row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  {/* Master Eco Mode Toggle */}
                  <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(52, 211, 153, 0.25)", padding: "8px 10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>Eco / Battery Saver</div>
                      <div style={{ fontSize: "8.5px", color: "#94a3b8" }}>Halt dGPU wakeups & relax timers</div>
                    </div>
                    <button
                      onClick={() => updatePowerSettings(!powerSettings.eco_mode, powerSettings.auto_battery_saver)}
                      disabled={isUpdatingPower}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "4px",
                        fontWeight: "bold",
                        fontSize: "10px",
                        fontFamily: "'Orbitron', sans-serif",
                        cursor: isUpdatingPower ? "wait" : "pointer",
                        background: powerSettings.eco_mode ? "linear-gradient(135deg, #10b981, #059669)" : "#334155",
                        color: "#fff",
                        border: `1px solid ${powerSettings.eco_mode ? "#34d399" : "#475569"}`,
                        boxShadow: powerSettings.eco_mode ? "0 0 8px rgba(52, 211, 153, 0.4)" : "none"
                      }}
                    >
                      {powerSettings.eco_mode ? "ON" : "OFF"}
                    </button>
                  </div>

                  {/* Auto-Activate on Battery Toggle */}
                  <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(52, 211, 153, 0.25)", padding: "8px 10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>Auto-On Battery</div>
                      <div style={{ fontSize: "8.5px", color: "#94a3b8" }}>Auto-engage when unplugged</div>
                    </div>
                    <button
                      onClick={() => updatePowerSettings(powerSettings.eco_mode, !powerSettings.auto_battery_saver)}
                      disabled={isUpdatingPower}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "4px",
                        fontWeight: "bold",
                        fontSize: "10px",
                        fontFamily: "'Orbitron', sans-serif",
                        cursor: isUpdatingPower ? "wait" : "pointer",
                        background: powerSettings.auto_battery_saver ? "linear-gradient(135deg, #34d399, #059669)" : "#334155",
                        color: powerSettings.auto_battery_saver ? "#010409" : "#fff",
                        border: `1px solid ${powerSettings.auto_battery_saver ? "#34d399" : "#475569"}`,
                        boxShadow: powerSettings.auto_battery_saver ? "0 0 8px rgba(52, 211, 153, 0.4)" : "none"
                      }}
                    >
                      {powerSettings.auto_battery_saver ? "ON" : "OFF"}
                    </button>
                  </div>
                </div>

                {/* Live Battery & Hardware Stats Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(1, 4, 10, 0.95)", border: "1px solid rgba(52, 211, 153, 0.2)", padding: "8px", borderRadius: "6px" }}>
                  <div>
                    <div style={{ fontSize: "8.5px", color: "#6ee7b7", textTransform: "uppercase" }}>Battery Level</div>
                    <div style={{ fontSize: "14px", fontWeight: "bold", color: batteryState ? (batteryState.percent > 20 ? "#34d399" : "#ef4444") : "#94a3b8", fontFamily: "'Orbitron', sans-serif" }}>
                      {batteryState ? `${batteryState.percent}%` : "AC Power"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "8.5px", color: "#6ee7b7", textTransform: "uppercase" }}>Power Source</div>
                    <div style={{ fontSize: "11px", fontWeight: "bold", color: "#e2e8f0", marginTop: "2px" }}>
                      {batteryState ? (batteryState.power_plugged ? "🔌 AC Adapter" : "🔋 Discharging") : "AC Connected"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "8.5px", color: "#6ee7b7", textTransform: "uppercase" }}>RTX GPU State</div>
                    <div style={{ fontSize: "11px", fontWeight: "bold", color: isEcoActive ? "#34d399" : "#38bdf8", marginTop: "2px" }}>
                      {isEcoActive ? "💤 D3 Sleep / Standby" : "⚡ Active Polling"}
                    </div>
                  </div>
                </div>

                {/* Explanatory Info Card */}
                <div style={{ background: "rgba(1, 4, 10, 0.7)", border: "1px solid rgba(52, 211, 153, 0.15)", padding: "8px 10px", borderRadius: "6px", fontSize: "9px", color: "#cbd5e1", lineHeight: "1.4" }}>
                  <div style={{ fontWeight: "bold", color: "#34d399", marginBottom: "3px" }}>🌱 How Friday Eco Mode Saves Laptop Battery:</div>
                  <div>• Stops continuous <code style={{ color: "#6ee7b7" }}>nvidia-smi</code> GPU probes so your NVIDIA RTX 3050 enters ultra-low power D3 sleep (saving 15W–25W+).</div>
                  <div>• Eliminates background PowerShell subprocess spawning to prevent CPU wakeups.</div>
                  <div>• Dynamically extends telemetry intervals on battery (6.0s) allowing CPU cores to reach deep C-states.</div>
                </div>
              </div>
            )}
          </div>

          {/* BOX 8: DEVICE MONITORING & DESKTOP CONTROL */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(168, 85, 247, 0.08)", border: "1px solid rgba(168, 85, 247, 0.35)", borderRadius: "6px" }}>
            <div onClick={() => { setBox8State(!box8State); fetchDeviceSettings && fetchDeviceSettings(); }} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#a855f7", fontWeight: "bold" }}>
                  8. DEVICE MONITORING & DESKTOP CONTROL
                </span>
                <span style={{
                  fontSize: "9px",
                  padding: "1px 6px",
                  borderRadius: "10px",
                  background: deviceSettings?.device_monitoring_enabled ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.2)",
                  border: `1px solid ${deviceSettings?.device_monitoring_enabled ? "#34d399" : "#ef4444"}`,
                  color: deviceSettings?.device_monitoring_enabled ? "#34d399" : "#f87171"
                }}>
                  {deviceSettings?.device_monitoring_enabled ? "🟢 MONITORING ON" : "🔴 MONITORING OFF"}
                </span>
              </div>
              <span style={{ color: "#a855f7", fontSize: "11px" }}>{box8State ? "▼" : "▶"}</span>
            </div>

            {box8State && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {/* Master Device Monitoring Toggle */}
                <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(168, 85, 247, 0.25)", padding: "10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>Enable Device Monitoring</div>
                    <div style={{ fontSize: "8.5px", color: "#94a3b8", marginTop: "2px" }}>
                      {deviceSettings?.device_monitoring_enabled
                        ? "Friday can inspect your screen and perform authorized desktop actions."
                        : "Allow Friday to view and interact with your desktop when requested."}
                    </div>
                  </div>
                  <button
                    onClick={() => updateDeviceSettings && updateDeviceSettings(!deviceSettings?.device_monitoring_enabled)}
                    disabled={isUpdatingDevice}
                    style={{
                      padding: "4px 12px",
                      borderRadius: "4px",
                      fontWeight: "bold",
                      fontSize: "10px",
                      fontFamily: "'Orbitron', sans-serif",
                      cursor: isUpdatingDevice ? "wait" : "pointer",
                      background: deviceSettings?.device_monitoring_enabled ? "linear-gradient(135deg, #10b981, #059669)" : "#334155",
                      color: "#fff",
                      border: `1px solid ${deviceSettings?.device_monitoring_enabled ? "#34d399" : "#475569"}`,
                      boxShadow: deviceSettings?.device_monitoring_enabled ? "0 0 8px rgba(52, 211, 153, 0.4)" : "none"
                    }}
                  >
                    {deviceSettings?.device_monitoring_enabled ? "ON" : "OFF"}
                  </button>
                </div>

                {/* Explanatory Info Card */}
                <div style={{ background: "rgba(1, 4, 10, 0.7)", border: "1px solid rgba(168, 85, 247, 0.15)", padding: "8px 10px", borderRadius: "6px", fontSize: "9px", color: "#cbd5e1", lineHeight: "1.4" }}>
                  <div style={{ fontWeight: "bold", color: "#c084fc", marginBottom: "3px" }}>🛡️ Desktop Privacy & Permissions Guard:</div>
                  <div>• Screen capture and UI inspection only run on-demand when requested by user commands.</div>
                  <div>• All external communication and sensitive file operations require explicit human confirmation.</div>
                  <div>• Disabling Device Monitoring blocks all desktop screen reading, UI automation, and mouse/keyboard tools.</div>
                </div>
              </div>
            )}
          </div>

          {/* BOX 9: DESKTOP HUD OVERLAY WIDGET */}
          <div className="jarvis-glass-card" style={{ padding: "12px", background: "rgba(0, 240, 255, 0.08)", border: "1px solid rgba(0, 240, 255, 0.35)", borderRadius: "6px" }}>
            <div onClick={() => { setBox9State(!box9State); fetchOverlaySettings && fetchOverlaySettings(); }} style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: "11px", color: "#00f0ff", fontWeight: "bold" }}>
                  9. DESKTOP HUD OVERLAY WIDGET
                </span>
                <span style={{
                  fontSize: "9px",
                  padding: "1px 6px",
                  borderRadius: "10px",
                  background: overlaySettings?.enabled ? "rgba(52, 211, 153, 0.2)" : "rgba(239, 68, 68, 0.2)",
                  border: `1px solid ${overlaySettings?.enabled ? "#34d399" : "#ef4444"}`,
                  color: overlaySettings?.enabled ? "#34d399" : "#f87171"
                }}>
                  {overlaySettings?.enabled ? "🟢 OVERLAY ACTIVE" : "🔴 OVERLAY DISABLED"}
                </span>
              </div>
              <span style={{ color: "#00f0ff", fontSize: "11px" }}>{box9State ? "▼" : "▶"}</span>
            </div>

            {box9State && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {/* Master Overlay Toggle */}
                <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.25)", padding: "10px", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: "10px", fontWeight: "bold", color: "#e2e8f0" }}>Enable Floating Desktop HUD</div>
                    <div style={{ fontSize: "8.5px", color: "#94a3b8", marginTop: "2px" }}>
                      {overlaySettings?.enabled
                        ? "Friday circular neural HUD is floating on your desktop (frameless & transparent)."
                        : "Show a floating, draggable transparent Friday circular widget on your Windows desktop."}
                    </div>
                  </div>
                  <button
                    onClick={() => updateOverlaySettings && updateOverlaySettings({ enabled: !overlaySettings?.enabled })}
                    disabled={isUpdatingOverlay}
                    style={{
                      padding: "4px 12px",
                      borderRadius: "4px",
                      fontWeight: "bold",
                      fontSize: "10px",
                      fontFamily: "'Orbitron', sans-serif",
                      cursor: isUpdatingOverlay ? "wait" : "pointer",
                      background: overlaySettings?.enabled ? "linear-gradient(135deg, #00f0ff, #0284c7)" : "#334155",
                      color: overlaySettings?.enabled ? "#010409" : "#fff",
                      border: `1px solid ${overlaySettings?.enabled ? "#00f0ff" : "#475569"}`,
                      boxShadow: overlaySettings?.enabled ? "0 0 10px rgba(0, 240, 255, 0.5)" : "none"
                    }}
                  >
                    {overlaySettings?.enabled ? "ON" : "OFF"}
                  </button>
                </div>

                {/* Opacity and Scale Controls */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  {/* Opacity Slider */}
                  <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.2)", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "9.5px", fontWeight: "bold", color: "#38bdf8" }}>HUD Transparency / Opacity</span>
                      <span style={{ fontSize: "10px", fontFamily: "'Orbitron', sans-serif", color: "#00f0ff", fontWeight: "bold" }}>
                        {Math.round((overlaySettings?.opacity ?? 1.0) * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.2"
                      max="1.0"
                      step="0.05"
                      value={overlaySettings?.opacity ?? 1.0}
                      onChange={(e) => updateOverlaySettings && updateOverlaySettings({ opacity: parseFloat(e.target.value) })}
                      style={{ width: "100%", accentColor: "#00f0ff", cursor: "pointer" }}
                    />
                  </div>

                  {/* Scale Slider */}
                  <div style={{ background: "rgba(1, 4, 10, 0.8)", border: "1px solid rgba(0, 240, 255, 0.2)", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "9.5px", fontWeight: "bold", color: "#38bdf8" }}>HUD Scale / Size</span>
                      <span style={{ fontSize: "10px", fontFamily: "'Orbitron', sans-serif", color: "#00f0ff", fontWeight: "bold" }}>
                        {Math.round((overlaySettings?.scale ?? 0.85) * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="1.5"
                      step="0.05"
                      value={overlaySettings?.scale ?? 0.85}
                      onChange={(e) => updateOverlaySettings && updateOverlaySettings({ scale: parseFloat(e.target.value) })}
                      style={{ width: "100%", accentColor: "#00f0ff", cursor: "pointer" }}
                    />
                  </div>
                </div>

                {/* Reset Position Button */}
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={() => updateOverlaySettings && updateOverlaySettings({ reset_position: true })}
                    disabled={isUpdatingOverlay}
                    style={{
                      padding: "5px 12px",
                      background: "rgba(0, 240, 255, 0.12)",
                      border: "1px solid rgba(0, 240, 255, 0.4)",
                      borderRadius: "4px",
                      color: "#00f0ff",
                      fontSize: "9.5px",
                      fontFamily: "'Orbitron', sans-serif",
                      fontWeight: "bold",
                      cursor: "pointer",
                      transition: "all 0.2s ease"
                    }}
                  >
                    ✥ Reset to Top-Right Screen Position
                  </button>
                </div>

                {/* Explanatory Info Card */}
                <div style={{ background: "rgba(1, 4, 10, 0.7)", border: "1px solid rgba(0, 240, 255, 0.15)", padding: "8px 10px", borderRadius: "6px", fontSize: "9px", color: "#cbd5e1", lineHeight: "1.4" }}>
                  <div style={{ fontWeight: "bold", color: "#38bdf8", marginBottom: "3px" }}>✨ Floating Desktop HUD Features:</div>
                  <div>• <b>GPU Accelerated & 100% Transparent</b>: Built on Edge WebView2 with DWM Glass rendering.</div>
                  <div>• <b>Interactive Controls</b>: Left-click toggles voice mic; drag anywhere on the HUD to move; right-click opens quick menu.</div>
                  <div>• <b>Real-time State Sync</b>: Instantly reflects listening (cyan/blue), thinking (yellow/gold), speaking, and idle states.</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Close Button */}
        <button
          type="button"
          onClick={onClose}
          style={{ marginTop: "8px", padding: "6px", background: "#1e293b", color: "#e2e8f0", borderRadius: "4px", fontWeight: "bold", border: "none", cursor: "pointer" }}
        >
          CLOSE SETTINGS
        </button>
      </div>
    </div>
  );
};
