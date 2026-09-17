"""
Friday Whisper Wake Word

Wake word:
    Friday

This version intentionally does NOT use Picovoice.

It uses the existing Faster-Whisper STT system
to detect the wake word.

IMPORTANT:
While Friday is idle, arbitrary speech is ignored.
Only speech containing the wake word activates Friday.
"""

from __future__ import annotations

import re
import time

from app.speech.whisper_stt import whisper_stt


class WakeWordService:

    def __init__(
        self,
        wake_words=None,
        listen_duration: float = 2.0,
    ):

        print(
            "[Wake] Initializing Whisper wake-word service..."
        )

        if wake_words is None:

            wake_words = [
                "friday",
            ]

        self.wake_words = [
            word.lower().strip()
            for word in wake_words
            if word.strip()
        ]

        self.listen_duration = (
            listen_duration
        )

        self.running = False

    # =========================================================
    # NORMALIZE TEXT
    # =========================================================

    def _normalize(
        self,
        text: str,
    ) -> str:

        if not text:

            return ""

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # =========================================================
    # CHECK WAKE WORD
    # =========================================================

    def contains_wake_word(
        self,
        text: str,
    ) -> bool:

        normalized = self._normalize(
            text
        )

        if not normalized:

            return False

        words = set(
            normalized.split()
        )

        for wake_word in self.wake_words:

            if wake_word in words:

                return True

        return False

    # =========================================================
    # WAIT FOR WAKE WORD
    #
    # This function blocks until:
    #
    # Friday is heard
    #
    # or the application is stopped.
    # =========================================================

    def wait_for_wake_word(
        self,
        stop_event=None,
    ) -> bool:

        self.running = True

        print()
        print(
            "[Wake] ======================================="
        )

        print(
            "[Wake] Waiting for wake word..."
        )

        print(
            "[Wake] Say: Friday"
        )

        print(
            "[Wake] ======================================="
        )

        last_status_time = 0

        try:

            while self.running:

                if (
                    stop_event is not None
                    and stop_event.is_set()
                ):

                    return False

                # -------------------------------------------------
                # Record only a short window.
                #
                # This is intentional. Friday is idle here.
                # -------------------------------------------------

                try:

                    text = whisper_stt.listen(
                        duration=self.listen_duration
                    )

                except Exception as e:

                    print(
                        f"[Wake] Listening error: {e}"
                    )

                    time.sleep(
                        0.2
                    )

                    continue

                if not text:

                    continue

                print(
                    f"[Wake] Heard: {text}"
                )

                if self.contains_wake_word(
                    text
                ):

                    print(
                        "[Wake] Wake word detected!"
                    )

                    return True

                # Don't spam terminal constantly.
                now = time.monotonic()

                if (
                    now - last_status_time
                    > 5
                ):

                    print(
                        "[Wake] Still waiting for 'Friday'..."
                    )

                    last_status_time = now

        except KeyboardInterrupt:

            self.running = False

            return False

        finally:

            self.running = False

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        self.running = False

        print(
            "[Wake] Wake-word service stopped."
        )


# =============================================================
# SINGLETON
# =============================================================

wake_word = WakeWordService(
    wake_words=[
        "friday",
    ],
    listen_duration=2.0,
)