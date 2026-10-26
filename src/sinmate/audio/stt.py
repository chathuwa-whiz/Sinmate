"""
Faster-Whisper Sinhala Speech-to-Text (STT) Transcriber.

Optimized for:
- SinhaSpeech/whisper-small-sinhala-run11
- Lingalingeswaran/whisper-small-sinhala
Runs on CTranslate2 with CPU INT8 or GPU FP16.
"""

from typing import Optional
from pathlib import Path


class SinhalaTranscriber:
    """
    Transcribes spoken Sinhala audio chunks into Unicode text using Faster-Whisper.
    """

    def __init__(
        self,
        model_size_or_path: str = "SinhaSpeech/whisper-small-sinhala-run11",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_path = model_size_or_path
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load_model(self):
        """Loads Faster-Whisper model into memory."""
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type
            )
        except Exception as e:
            self.model = None
            raise RuntimeError(f"Failed to load Faster-Whisper Sinhala model: {e}")

    def transcribe(self, audio_file_or_array) -> str:
        """Transcribes audio and returns normalized Sinhala text."""
        if self.model is None:
            self.load_model()

        segments, _ = self.model.transcribe(
            audio_file_or_array,
            language="si",
            beam_size=5,
            vad_filter=True
        )
        text_segments = [s.text.strip() for s in segments]
        return " ".join(text_segments)
