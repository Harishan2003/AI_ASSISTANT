"""
Friday AI Assistant - Autonomous Real-Time Alarm & Timer Background Service.
Handles background timers, alarms, audible multi-frequency chime beeps, native Windows notifications,
WebSocket alerts, and voice reminders.
"""

import asyncio
import datetime
import logging
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlarmItem:
    def __init__(self, alarm_id: str, label: str, duration_seconds: float, target_time: datetime.datetime):
        self.alarm_id = alarm_id
        self.label = label
        self.duration_seconds = duration_seconds
        self.target_time = target_time
        self.is_active = True
        self.cancelled = False
        self.timer_thread: Optional[threading.Thread] = None

    def remaining_seconds(self) -> float:
        now = datetime.datetime.now()
        rem = (self.target_time - now).total_seconds()
        return max(0.0, rem)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alarm_id": self.alarm_id,
            "label": self.label,
            "target_time": self.target_time.strftime("%I:%M %p"),
            "target_time_iso": self.target_time.isoformat(),
            "remaining_seconds": round(self.remaining_seconds()),
            "remaining_formatted": f"{int(self.remaining_seconds() // 60)}m {int(self.remaining_seconds() % 60)}s",
            "is_active": self.is_active,
        }


class AlarmService:
    """Manages active alarms and countdown timers."""

    def __init__(self):
        self._alarms: Dict[str, AlarmItem] = {}
        self._lock = threading.Lock()

    def set_timer(self, seconds: float, label: str = "Alarm") -> Dict[str, Any]:
        """Sets a timer for the given number of seconds and runs the countdown in background."""
        alarm_id = f"alarm_{uuid.uuid4().hex[:6]}"
        target_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        with self._lock:
            # Prevent duplicate looping timers if user repeated the command within 15 seconds
            for old_id, existing in list(self._alarms.items()):
                if existing.is_active and not existing.cancelled:
                    if existing.label.lower() == label.lower() and abs((existing.target_time - target_time).total_seconds()) < 15:
                        logger.info(f"Replacing duplicate timer '{label}' ({old_id}) with new timer ({alarm_id})")
                        existing.cancelled = True
                        existing.is_active = False

            alarm = AlarmItem(alarm_id, label, seconds, target_time)
            self._alarms[alarm_id] = alarm

        def _runner():
            logger.info(f"Alarm {alarm_id} started for {seconds}s: '{label}'")
            sleep_chunk = 0.5
            while True:
                if alarm.cancelled:
                    logger.info(f"Alarm {alarm_id} was cancelled.")
                    return
                now = datetime.datetime.now()
                if now >= target_time:
                    break
                time.sleep(min(sleep_chunk, (target_time - now).total_seconds()))

            with self._lock:
                if alarm.cancelled or not alarm.is_active:
                    return
                alarm.is_active = False

            self._fire_alarm(alarm)

        t = threading.Thread(target=_runner, daemon=True)
        alarm.timer_thread = t
        t.start()

        return alarm.to_dict()

    def _fire_alarm(self, alarm: AlarmItem):
        """Fires the alarm with sound, notification, and Friday's Neural Voice Persona."""
        logger.info(f"🔔 ALARM FIRING: '{alarm.label}' at {datetime.datetime.now().strftime('%I:%M %p')}")

        # 1. Play audible sound (multi-frequency pulsing chimes)
        if os.name == "nt":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                for _ in range(2):
                    winsound.Beep(1200, 150)
                    winsound.Beep(1500, 150)
                    winsound.Beep(1800, 250)
                    time.sleep(0.1)
            except Exception as e:
                logger.warning(f"winsound beep failed: {e}")

        # 2. Native Windows Toast / Msg Notification
        try:
            if os.name == "nt":
                import subprocess
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
                $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
                $text = $xml.GetElementsByTagName("text")
                $text.Item(0).InnerText = "FRIDAY REMINDER: {alarm.label}"
                $text.Item(1).InnerText = "Scheduled timer completed at {alarm.target_time.strftime('%I:%M %p')}"
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Friday AI Assistant").Show($toast)
                '''
                subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # 3. Voice Speech Reminder using Friday's Neural Voice Persona & Selected Profile
        def _speak_neural_reminder():
            try:
                # Query user profile for persona voice, name, language, and gender
                from app.services.user_persona_service import user_persona_service
                from app.services.tts_service import tts_service
                
                profile = user_persona_service.get_profile()
                user_name = profile.get("user_name", "Harishan")
                comm_style = profile.get("communication_style", {})
                lang = (comm_style.get("language") or "english").lower()
                gender = (profile.get("voice_gender") or "female").lower()

                # Compose localized, persona-aligned alert
                if lang == "tamil" or re.search(r"[\u0B80-\u0BFF]", alarm.label):
                    alert_text = f"கவனம் {user_name}! உங்கள் நேர நினைவூட்டல் முடிந்தது: {alarm.label}."
                elif lang == "tanglish":
                    alert_text = f"Attention {user_name}! Unga timer complete aaiduchu. Reminder: {alarm.label}."
                else:
                    alert_text = f"Attention {user_name}! Your timer is complete. Reminder: {alarm.label}."

                # Synthesize studio-grade neural audio via edge-tts/gTTS
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    audio_bytes = loop.run_until_complete(tts_service.synthesize(alert_text, language=lang, gender=gender))
                finally:
                    loop.close()

                if audio_bytes:
                    import io
                    import pygame
                    pygame.mixer.init()
                    sound_file = io.BytesIO(audio_bytes)
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                    return
            except Exception as e:
                logger.warning(f"Neural TTS reminder alert fallback notice: {e}")

            # Fallback to Windows native SAPI with COM initialization
            if os.name == "nt":
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(f"Attention Harishan! Your timer is complete. Reminder: {alarm.label}.")
                    pythoncom.CoUninitialize()
                except Exception as fallback_err:
                    logger.warning(f"Alarm SAPI voice alert failed: {fallback_err}")

        threading.Thread(target=_speak_neural_reminder, daemon=True).start()

    def list_active_alarms(self) -> List[Dict[str, Any]]:
        """Returns all currently running alarms."""
        with self._lock:
            active = [a.to_dict() for a in self._alarms.values() if a.is_active and not a.cancelled]
            return active

    def cancel_alarm(self, alarm_id: Optional[str] = None) -> bool:
        """Cancels a specific alarm or all active alarms if alarm_id is None."""
        with self._lock:
            if alarm_id and alarm_id in self._alarms:
                self._alarms[alarm_id].cancelled = True
                self._alarms[alarm_id].is_active = False
                return True
            elif not alarm_id:
                for a in self._alarms.values():
                    a.cancelled = True
                    a.is_active = False
                return True
        return False


alarm_service = AlarmService()


def parse_alarm_or_reminder_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Parses natural language requests for timers, alarms, and reminders.
    Examples:
      - 'inform me in 2 minutes I need to cook' -> seconds=120, label='I need to cook'
      - 'remind me in 2 mins to cook' -> seconds=120, label='Cook'
      - 'set alarm for 5 minutes' -> seconds=300, label='Alarm'
      - 'notify me in 10 minutes meeting' -> seconds=600, label='Meeting'
      - 'cancel alarm' -> action='cancel'
      - 'alarm status' / 'list alarms' -> action='list'
    """
    q = query.lower().strip()

    # Cancel alarm
    if any(k in q for k in ["cancel alarm", "cancel all alarms", "cancel timer", "stop alarm", "stop timer", "delete alarm"]):
        alarm_service.cancel_alarm()
        return {"action": "cancelled", "message": "All active alarms and timers have been cancelled."}

    # Query alarm status
    if any(k in q for k in ["alarm status", "list alarms", "what alarms", "how much time left", "check alarm", "check timer"]):
        active = alarm_service.list_active_alarms()
        if not active:
            return {"action": "status", "message": "No active alarms or timers are currently running."}
        desc = "\n".join([f"• **{a['label']}**: {a['remaining_formatted']} remaining (rings at {a['target_time']})" for a in active])
        return {"action": "status", "message": f"Active Alarms & Timers ({len(active)}):\n{desc}"}

    # Check if query is about setting an alarm/timer/reminder/inform/notify
    alarm_keywords = [
        "alarm", "timer", "remind", "reminder", "remember", "inform", "notify", 
        "alert", "ping", "warn", "wake me", "wake me up", "tell me in", "tell me after"
    ]
    is_alarm_intent = any(k in q for k in alarm_keywords)
    
    # Or standalone short durations like "5 min", "1 min", "5 mins", "10 min"
    is_standalone_duration = bool(re.match(r"^(?:set\s+)?(?:a\s+)?(\d+)\s*(?:min|mins|minute|minutes|sec|secs|second|seconds|hr|hrs|hour|hours)(?:\s+alarm|\s+timer)?$", q))

    if not is_alarm_intent and not is_standalone_duration:
        return None

    # Extract hours, minutes, seconds
    total_seconds = 0

    # Hours
    hr_match = re.search(r'(\d+)\s*(?:hour|hours|hr|hrs)', q)
    if hr_match:
        total_seconds += int(hr_match.group(1)) * 3600

    # Minutes
    min_match = re.search(r'(\d+)\s*(?:minute|minutes|min|mins)', q)
    if min_match:
        total_seconds += int(min_match.group(1)) * 60

    # Seconds
    sec_match = re.search(r'(\d+)\s*(?:second|seconds|sec|secs)', q)
    if sec_match:
        total_seconds += int(sec_match.group(1))

    # Bare numbers fallback if "alarm" or "timer" was mentioned (e.g. "alarm 5")
    if total_seconds == 0:
        bare_num_match = re.search(r'(?:alarm|timer)\s+(?:for\s+)?(\d+)', q)
        if bare_num_match:
            total_seconds = int(bare_num_match.group(1)) * 60

    if total_seconds <= 0:
        return None

    # Extract label (e.g. 'i need to cook' or 'to cook' or 'cook')
    label = "Reminder"
    label_patterns = [
        r'(?:inform me in|notify me in|remind me in|alert me in|ping me in)\s+\d+\s*(?:minute|minutes|min|mins|second|seconds|sec|secs|hour|hours|hr|hrs)\s+(?:that\s+|about\s+|i\s+need\s+to\s+|to\s+)?(.+)$',
        r'(?:inform me after|notify me after|remind me after)\s+\d+\s*(?:minute|minutes|min|mins|second|seconds|sec|secs|hour|hours|hr|hrs)\s+(?:that\s+|about\s+|to\s+)?(.+)$',
        r'(?:remind me to|remember to|need to|to)\s+([^0-9\n\r]+)$',
        r'(?:for\s+)([^0-9\n\r]+)$'
    ]
    for pat in label_patterns:
        match = re.search(pat, q)
        if match:
            extracted = match.group(1).strip()
            # Clean unwanted tokens
            extracted = re.sub(r'^(that\s+|about\s+|i\s+)', '', extracted).strip()
            if extracted and len(extracted) > 1 and not any(k in extracted for k in ["minute", "min", "second", "sec", "hour"]):
                label = extracted.capitalize()
                break

    # Set timer
    res = alarm_service.set_timer(total_seconds, label=label)
    
    # Format human response
    formatted_duration = ""
    if total_seconds >= 3600:
        formatted_duration += f"{int(total_seconds // 3600)} hour{'s' if total_seconds >= 7200 else ''} "
    rem_min = int((total_seconds % 3600) // 60)
    if rem_min > 0:
        formatted_duration += f"{rem_min} minute{'s' if rem_min > 1 else ''} "
    rem_sec = int(total_seconds % 60)
    if rem_sec > 0:
        formatted_duration += f"{rem_sec} second{'s' if rem_sec > 1 else ''} "

    formatted_duration = formatted_duration.strip()

    target_time_str = res["target_time"]
    msg = f"Got it! I have set a **{formatted_duration} reminder** for you ('{label}'). It will go off at **{target_time_str}** with an audible chime, spoken alert, and desktop notification."
    return {
        "action": "set",
        "alarm": res,
        "message": msg
    }
