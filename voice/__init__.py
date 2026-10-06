"""
KI.AI Voice Management Package.
Provides centralized VoiceManager, Priority queues, event deduplication,
and interruption-aware speech controllers.
"""

from voice.voice_manager import (
    CoachingEvent,
    Priority,
    SpeechRequest,
    VoiceManager,
    VoiceState,
    get_voice_manager,
)

__all__ = [
    "CoachingEvent",
    "Priority",
    "SpeechRequest",
    "VoiceManager",
    "VoiceState",
    "get_voice_manager",
]
