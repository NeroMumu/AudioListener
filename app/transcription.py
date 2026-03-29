from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock

import numpy as np
from faster_whisper import WhisperModel

from app.audio import resample_audio, rms_level, unpack_audio_message
from app.config import settings


logger = logging.getLogger(__name__)
DebugCallback = Callable[[str], Awaitable[None]]


@dataclass
class SessionState:
    active: bool = False
    speaking: bool = False
    model_name: str = ""
    current_chunks: list[np.ndarray] = field(default_factory=list)
    speech_ms: int = 0
    silence_ms: int = 0
    speech_timestamp: str | None = None
    last_partial_at: float = 0.0
    last_partial_speech_ms: int = 0
    last_partial_text: str = ""

    def reset(self) -> None:
        self.speaking = False
        self.current_chunks.clear()
        self.speech_ms = 0
        self.silence_ms = 0
        self.speech_timestamp = None
        self.last_partial_at = 0.0
        self.last_partial_speech_ms = 0
        self.last_partial_text = ""


@dataclass(frozen=True)
class TranscribedSegment:
    start: float
    end: float
    text: str


class TranscriptionEngine:
    def __init__(self) -> None:
        self._models: dict[str, WhisperModel] = {}
        self._model_lock = Lock()
        self._active_model_name = self._resolve_model_name(settings.model_name)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        settings.model_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_model_name(self, model_name: str | None) -> str:
        candidate = (model_name or self._active_model_name or settings.model_name).strip()
        if candidate not in settings.available_whisper_models:
            raise ValueError(
                f"Modèle de transcription invalide: {candidate}. Modèles disponibles: {', '.join(settings.available_whisper_models)}"
            )
        return candidate

    def list_available_models(self) -> list[str]:
        return list(settings.available_whisper_models)

    def get_active_model(self) -> str:
        return self._active_model_name

    def select_model(self, model_name: str | None) -> str:
        selected_model = self._resolve_model_name(model_name)
        self._active_model_name = selected_model
        return selected_model

    async def ensure_model(self, model_name: str | None = None) -> None:
        selected_model = self._resolve_model_name(model_name)
        if selected_model not in self._models:
            await asyncio.to_thread(self._load_model, selected_model)

    def _load_model(self, model_name: str) -> None:
        if model_name in self._models:
            return
        with self._model_lock:
            if model_name in self._models:
                return
            self._models[model_name] = WhisperModel(
                model_name,
                device="cpu",
                compute_type=settings.compute_type,
                download_root=str(settings.model_dir),
            )

    def create_session(self) -> SessionState:
        return SessionState()

    async def _emit_debug(self, debug_callback: DebugCallback | None, message: str) -> None:
        logger.info(message)
        if debug_callback is not None:
            await debug_callback(message)

    async def process_audio_bytes(
        self,
        session: SessionState,
        payload: bytes,
        debug_callback: DebugCallback | None = None,
    ) -> list[dict[str, str]]:
        sample_rate, samples = unpack_audio_message(payload)
        resampled = resample_audio(samples, sample_rate, settings.target_sample_rate)
        if resampled.size == 0:
            return []

        chunk_ms = int((resampled.size / settings.target_sample_rate) * 1000)
        level = rms_level(resampled)
        is_voice = level >= settings.silence_threshold
        events: list[dict[str, str]] = []

        if is_voice:
            if not session.speaking:
                session.speaking = True
                session.speech_timestamp = datetime.now().strftime("%H:%M")
                await self._emit_debug(
                    debug_callback,
                    f"Voix détectée · RMS {level:.5f} · horodatage [{session.speech_timestamp}]",
                )

            session.current_chunks.append(resampled)
            session.speech_ms += chunk_ms
            session.silence_ms = 0

            enough_audio = session.speech_ms >= settings.min_speech_ms
            enough_delay = (time.monotonic() - session.last_partial_at) * 1000 >= settings.partial_interval_ms
            enough_new_audio = (session.speech_ms - session.last_partial_speech_ms) >= settings.partial_step_ms
            if enough_audio and enough_delay and enough_new_audio:
                session.last_partial_at = time.monotonic()
                session.last_partial_speech_ms = session.speech_ms
                partial_text = await self._transcribe_current_buffer(session)
                if partial_text and partial_text != session.last_partial_text:
                    session.last_partial_text = partial_text
                    await self._emit_debug(debug_callback, f"Partiel : {partial_text}")
                    events.append(
                        {
                            "type": "partial",
                            "timestamp": session.speech_timestamp or datetime.now().strftime("%H:%M"),
                            "text": partial_text,
                        }
                    )
        elif session.speaking:
            session.current_chunks.append(resampled)
            session.silence_ms += chunk_ms
            if session.silence_ms >= settings.pause_duration_ms and session.speech_ms >= settings.min_speech_ms:
                await self._emit_debug(
                    debug_callback,
                    f"Pause détectée · finalisation du bloc après {session.speech_ms} ms de parole",
                )
                final_text = await self._transcribe_current_buffer(session)
                if final_text:
                    await self._emit_debug(debug_callback, f"Final : {final_text}")
                    events.append(
                        {
                            "type": "final",
                            "timestamp": session.speech_timestamp or datetime.now().strftime("%H:%M"),
                            "text": final_text,
                        }
                    )
                session.reset()

        return events

    async def flush(self, session: SessionState, debug_callback: DebugCallback | None = None) -> list[dict[str, str]]:
        if not session.current_chunks or session.speech_ms < settings.min_speech_ms:
            session.reset()
            return []

        final_text = await self._transcribe_current_buffer(session)
        events: list[dict[str, str]] = []
        if final_text:
            await self._emit_debug(debug_callback, f"Final : {final_text}")
            events.append(
                {
                    "type": "final",
                    "timestamp": session.speech_timestamp or datetime.now().strftime("%H:%M"),
                    "text": final_text,
                }
            )
        session.reset()
        return events

    async def _transcribe_current_buffer(self, session: SessionState) -> str:
        model_name = session.model_name or self.get_active_model()
        await self.ensure_model(model_name)
        if model_name not in self._models or not session.current_chunks:
            return ""

        audio = np.concatenate(session.current_chunks).astype(np.float32)
        return (await asyncio.to_thread(self._transcribe_sync, audio, model_name)).strip()

    async def transcribe_file(
        self,
        file_path: str | Path,
        model_name: str | None = None,
    ) -> tuple[str, list[TranscribedSegment]]:
        selected_model = self._resolve_model_name(model_name)
        await self.ensure_model(selected_model)
        return await asyncio.to_thread(self._transcribe_file_sync, str(file_path), selected_model)

    def _transcribe_sync(self, audio: np.ndarray, model_name: str) -> str:
        model = self._models.get(model_name)
        if model is None:
            return ""

        with self._model_lock:
            segments, _ = model.transcribe(
                audio,
                language=settings.language,
                task="transcribe",
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=False,
                temperature=0.0,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
            return text

    def _transcribe_file_sync(self, file_path: str, model_name: str) -> tuple[str, list[TranscribedSegment]]:
        model = self._models.get(model_name)
        if model is None:
            return "", []

        with self._model_lock:
            segments, _ = model.transcribe(
                file_path,
                language=settings.language,
                task="transcribe",
                beam_size=5,
                best_of=5,
                condition_on_previous_text=False,
                vad_filter=True,
                temperature=0.0,
            )
            collected_segments: list[TranscribedSegment] = []
            text_parts: list[str] = []

            for segment in segments:
                cleaned_text = segment.text.strip()
                if not cleaned_text:
                    continue
                collected_segments.append(
                    TranscribedSegment(start=float(segment.start), end=float(segment.end), text=cleaned_text)
                )
                text_parts.append(cleaned_text)

            return " ".join(text_parts).strip(), collected_segments
