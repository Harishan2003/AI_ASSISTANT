/**
 * Friday AI Assistant - Type Definitions
 * Shared TypeScript interfaces and data models for Friday UI and Backend communications.
 */

export interface Message {
  id: string;
  sender: "user" | "friday" | "system";
  text: string;
  timestamp: string;
  muted?: boolean;
}

export interface ConversationItem {
  conversation_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface UserProfile {
  name: string;
  agent_name: string;
  age: string;
  email: string;
  city: string;
  voice_gender?: "female" | "male";
  languages?: string[];
}

export interface GpuInfo {
  id: string;
  label: string;
  shortName: string;
  load: number;
  temp: number;
}

export interface PowerSettings {
  eco_mode: boolean;
  auto_battery_saver: boolean;
  telemetry_interval_battery: number;
  telemetry_interval_ac: number;
}

export interface BatteryState {
  percent: number;
  power_plugged: boolean;
  secsleft?: number | null;
}

export interface WhatsAppSettings {
  enabled: boolean;
  auto_reply: boolean;
  monitoring_active: boolean;
  custom_auto_reply_message?: string;
  replied_count: number;
  last_activity?: string;
}

export interface WhatsAppLog {
  sender?: string;
  recipient?: string;
  message?: string;
  text?: string;
  reply?: string;
  timestamp: number | string;
  is_urgent?: boolean;
}

export interface UrgentAlert {
  sender: string;
  message: string;
  timestamp: number | string;
}

export interface FeatureScanResult {
  feature_name?: string;
  feature?: string;
  category?: string;
  status: string;
  raw_status?: string;
  details?: string;
  duration_ms?: number;
  error?: string | null;
}

export interface DeviceMonitoringSettings {
  device_monitoring_enabled: boolean;
  ocr_enabled: boolean;
  action_delay_ms: number;
  verification_enabled: boolean;
  privacy_blur_sensitive: boolean;
}

