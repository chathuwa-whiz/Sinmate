"""
Silero VAD (Voice Activity Detection) Wrapper for Sinmate.

Provides low-latency speech detection (<30ms) to support real-time audio recording
and instant barge-in interruption of active TTS playback.
"""

from typing import Callable, Optional
import numpy as np


class SileroVADDetector:
    """
    Detects voice presence in audio chunks using Silero VAD.
    """

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = None
        self._is_initialized = False

    def initialize(self):
        """Loads Silero VAD model via torch hub or local ONNX runtime."""
        try:
            import torch
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=True
            )
            self.model = model
            self._is_initialized = True
        except Exception as e:
            # Fallback or stub mode for offline initialization
            self._is_initialized = False
            self.init_error = str(e)

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Determines if the provided 16kHz audio chunk contains human voice.
        """
        if not self._is_initialized or self.model is None:
            # Fallback energy threshold if torch model not yet loaded
            energy = np.mean(np.abs(audio_chunk))
            return bool(energy > 0.02)

        import torch
        tensor_chunk = torch.from_numpy(audio_chunk).float()
        with torch.no_grad():
            confidence = self.model(tensor_chunk, self.sample_rate).item()
        return confidence >= self.threshold
