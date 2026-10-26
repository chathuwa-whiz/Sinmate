"""
Local LLM engine for Sinmate: Ollama client, sentence streaming for TTS, and the Brain conversation loop.

- OllamaEngine talks to a local Ollama server (/api/chat, streaming NDJSON) using only the standard library.
- iter_sentences() regroups the token stream into speakable sentences so the Mouth can start talking before the
  full reply is generated.
- Brain ties a PersonaManager, the engine, and a short rolling history together. Closing the sentence generator
  (barge-in) aborts generation and records only what was actually spoken.

All text going in and out is normalized to Unicode NFC.
"""

import json
import os
import re
import socket
import urllib.error
import urllib.request
from typing import Dict, Iterable, Iterator, List, Optional

from .normalizer import normalize_sinhala_text
from .personas import PersonaManager, PersonaRole

DEFAULT_MODEL = "gemma3:1b-it-qat"
DEFAULT_HOST = "http://127.0.0.1:11434"

Message = Dict[str, str]


class LLMError(RuntimeError):
    """The LLM backend returned an error."""


class OllamaUnavailableError(LLMError):
    """The Ollama server could not be reached."""


def _resolve_host(host: Optional[str]) -> str:
    # Accept the standard OLLAMA_HOST form too ("127.0.0.1:11434" without a scheme).
    host = host or os.environ.get("SINMATE_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
    if "://" not in host:
        host = "http://" + host
    return host.rstrip("/")


# A terminator run is only followed by whitespace once the next token arrives, so a sentence is released one token
# after its last character. That keeps "3.5" and a trailing "." that may still grow into "..." intact.
_TERMINATOR = re.compile(r"[.?!…]+(?=\s)|\n+")


def _find_sentence_end(buf: str, min_chars: int) -> Optional[int]:
    """Index just past the first real sentence boundary in buf, or None."""
    for match in _TERMINATOR.finditer(buf):
        run = match.group()
        # Ellipsis ("හ්ම්ම්...") is a spoken pause, not the end of a sentence.
        is_end = "\n" in run or run == "." or "?" in run or "!" in run
        if is_end and len(buf[: match.end()].strip()) >= min_chars:
            return match.end()
    return None


def iter_sentences(chunks: Iterable[str], min_chars: int = 6) -> Iterator[str]:
    """
    Regroup streamed text chunks into sentences. Boundaries are ". ? !" followed by whitespace, and newlines.
    Fragments shorter than min_chars are merged into the next sentence. Closing this generator closes `chunks`.
    """
    buf = ""
    try:
        for chunk in chunks:
            buf += chunk
            while True:
                end = _find_sentence_end(buf, min_chars)
                if end is None:
                    break
                sentence, buf = buf[:end].strip(), buf[end:].lstrip()
                if sentence:
                    yield sentence
        tail = buf.strip()
        if tail:
            yield tail
    finally:
        close = getattr(chunks, "close", None)
        if close:
            close()


class OllamaEngine:
    """Minimal Ollama chat client with streaming."""

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
        max_tokens: int = 128,
        timeout: float = 60.0,
        keep_alive: str = "30m",
    ):
        self.model = model or os.environ.get("SINMATE_MODEL") or DEFAULT_MODEL
        self.host = _resolve_host(host)
        self.options = {
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "num_predict": max_tokens,
        }
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _open(self, path: str, payload: Optional[dict] = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.host + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            exc.close()
            try:
                detail = json.loads(detail).get("error", detail)
            except ValueError:
                pass
            hint = " (is the model created? check `ollama list`)" if exc.code == 404 else ""
            raise LLMError(f"Ollama returned HTTP {exc.code}: {detail}{hint}") from exc
        except (urllib.error.URLError, ConnectionError, socket.timeout) as exc:
            raise OllamaUnavailableError(
                f"Cannot reach Ollama at {self.host}. Is it running? Start it with `ollama serve`."
            ) from exc

    def is_available(self) -> bool:
        """True if the Ollama server answers."""
        try:
            self.list_models()
            return True
        except LLMError:
            return False

    def list_models(self) -> List[str]:
        with self._open("/api/tags") as response:
            body = json.loads(response.read().decode("utf-8"))
        return [m.get("name", "") for m in body.get("models", [])]

    def stream_chat(self, messages: List[Message]) -> Iterator[str]:
        """Yield raw text chunks as the model produces them. Closing the generator aborts generation."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": self.options,
            "keep_alive": self.keep_alive,
        }
        response = self._open("/api/chat", payload)
        try:
            for raw in response:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw.decode("utf-8"))
                except ValueError as exc:
                    raise LLMError(f"Malformed response line from Ollama: {raw[:200]!r}") from exc
                if event.get("error"):
                    raise LLMError(f"Ollama error: {event['error']}")
                content = event.get("message", {}).get("content", "")
                if content:
                    yield content
                if event.get("done"):
                    return
        except socket.timeout as exc:
            raise LLMError(f"Ollama did not respond within {self.timeout:.0f}s") from exc
        finally:
            response.close()

    def stream_sentences(self, messages: List[Message], min_chars: int = 6) -> Iterator[str]:
        """Yield NFC-normalized sentences, ready to hand to TTS one at a time."""
        for sentence in iter_sentences(self.stream_chat(messages), min_chars=min_chars):
            sentence = normalize_sinhala_text(sentence)
            if sentence:
                yield sentence

    def chat(self, messages: List[Message]) -> str:
        """Blocking convenience wrapper: the full reply as one NFC-normalized string."""
        return normalize_sinhala_text("".join(self.stream_chat(messages)))


class Brain:
    """Persona + engine + rolling history. One instance per conversation."""

    def __init__(
        self,
        engine: Optional[OllamaEngine] = None,
        personas: Optional[PersonaManager] = None,
        prompt_style: str = "compact",
        max_history_messages: int = 12,
        min_sentence_chars: int = 6,
    ):
        self.engine = engine or OllamaEngine()
        self.personas = personas or PersonaManager()
        self.prompt_style = prompt_style
        self.max_history_messages = max_history_messages
        self.min_sentence_chars = min_sentence_chars
        self._history: List[Message] = []

    def set_persona(self, role: PersonaRole) -> None:
        self.personas.set_persona(role)

    def reset_history(self) -> None:
        self._history.clear()

    def build_messages(self, user_text: str, memory_context: Optional[str] = None) -> List[Message]:
        system = self.personas.get_system_prompt(memory_context=memory_context, style=self.prompt_style)
        return [{"role": "system", "content": system}, *self._history, {"role": "user", "content": user_text}]

    def _remember(self, user_text: str, reply: str) -> None:
        self._history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
        self._history = self._history[-self.max_history_messages :]
        # Gemma's chat template needs the conversation to start with a user turn.
        if self._history and self._history[0]["role"] != "user":
            self._history.pop(0)

    def respond_stream(self, user_text: str, memory_context: Optional[str] = None) -> Iterator[str]:
        """
        Yield the reply sentence by sentence. If the caller closes the generator early (barge-in), generation is
        aborted and only the sentences already yielded are kept in history, so the next turn doesn't assume the
        user heard the rest.
        """
        user_text = normalize_sinhala_text(user_text)
        if not user_text:
            return
        stream = self.engine.stream_sentences(
            self.build_messages(user_text, memory_context), min_chars=self.min_sentence_chars
        )
        spoken: List[str] = []
        try:
            for sentence in stream:
                spoken.append(sentence)
                yield sentence
        finally:
            stream.close()
            if spoken:
                self._remember(user_text, " ".join(spoken))

    def respond(self, user_text: str, memory_context: Optional[str] = None) -> str:
        """Blocking convenience wrapper around respond_stream()."""
        return " ".join(self.respond_stream(user_text, memory_context))
