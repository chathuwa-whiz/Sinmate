"""
Proactive Heartbeat Loop for Sinmate.

Simulates human-like spontaneity by checking:
- Current local time (late nights, early mornings, lunch hours)
- Silence duration (user inactive for > 30-45 minutes)
- Upcoming events or stored user facts
Triggers spontaneous conversational prompts to the Brain engine.
"""

import datetime
from typing import Callable, Optional


class HeartbeatMonitor:
    """
    Monitors user activity intervals and evaluates proactive trigger conditions.
    """

    def __init__(self, silence_threshold_minutes: int = 35):
        self.silence_threshold = silence_threshold_minutes
        self.last_activity_time = datetime.datetime.now()

    def record_activity(self):
        """Resets the silence timer whenever user speaks or interacts."""
        self.last_activity_time = datetime.datetime.now()

    def check_trigger_condition(self) -> Optional[dict]:
        """
        Evaluates whether a proactive event should fire.
        Returns context metadata if trigger conditions are met.
        """
        now = datetime.datetime.now()
        silence_duration = (now - self.last_activity_time).total_seconds() / 60.0

        if silence_duration >= self.silence_threshold:
            hour = now.hour
            time_context = "late_night" if (hour >= 23 or hour < 4) else (
                "morning" if 6 <= hour < 10 else (
                    "evening" if 18 <= hour < 22 else "work_hours"
                )
            )
            return {
                "event_type": "PROACTIVE_CHECK_IN",
                "silence_minutes": round(silence_duration, 1),
                "time_context": time_context,
                "current_time": now.strftime("%I:%M %p")
            }
        return None
