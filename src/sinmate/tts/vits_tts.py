"""
Sinhala VITS & Piper Neural TTS Synthesizer.

Interfaces with:
- dialoglk/SinhalaVITS-TTS-F1 (Expressive Female voice)
- SafnasKaldeen/Sinhala-Text-to-Speech-VITS-BestInSriLanka (4 Native voices: Isuru, Yasindu, Harini, Dinithi)
Provides sentence-by-sentence streaming playback with immediate cancellation on barge-in.
"""

from typing import Optional
from pathlib import Path


class SinhalaVoiceSynthesizer:
    """
    Synthesizes conversational Sinhala text into natural speech waveforms.
    """

    def __init__(
        self,
        model_name_or_path: str = "dialoglk/SinhalaVITS-TTS-F1",
        voice_id: int = 0
    ):
        self.model_path = model_name_or_path
        self.voice_id = voice_id
        self._is_speaking = False

    def synthesize(self, text: str, output_path: Optional[str] = None):
        """
        Synthesizes the given Sinhala text into audio waveform.
        """
        # Placeholder for VITS inference engine integration
        pass

    def stop_speaking(self):
        """
        Immediate interrupt for barge-in detection.
        """
        self._is_speaking = False
