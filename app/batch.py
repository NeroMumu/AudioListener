from __future__ import annotations

import asyncio
import logging
import queue
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings
from app.core.events import event_bus
from app.core.state import system_state
from app.transcription import TranscribedSegment, TranscriptionEngine


logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _format_seconds(value: float) -> str:
    total_seconds = max(int(value), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


@dataclass
class BatchJob:
    job_id: str
    file_name: str
    input_path: str
    source: str
    status: str
    created_at: str
    updated_at: str
    output_file_name: str | None = None
    output_file_path: str | None = None
    archived_source_path: str | None = None
    transcript_text: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "file_name": self.file_name,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "output_file_name": self.output_file_name,
            "output_file_path": self.output_file_path,
            "archived_source_path": self.archived_source_path,
            "error": self.error,
        }


class BatchProcessor:
    def __init__(self, engine: TranscriptionEngine) -> None:
        self.engine = engine
        self._jobs: dict[str, BatchJob] = {}
        self._jobs_by_path: dict[str, str] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._started = False
        self._stop_event = threading.Event()
        self._active_job_id: str | None = None
        self._pyannote_pipeline: Any | None = None
        self._pyannote_lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True

        self._ensure_directories()
        self._scan_input_directory()
        threading.Thread(target=self._scan_loop, daemon=True).start()
        threading.Thread(target=self._worker_loop, daemon=True).start()
        system_state.update_service("batch", "ready", f"Surveillance Input → {settings.input_dir}")
        logger.info("Batch processor started | input=%s | output=%s | trash=%s", settings.input_dir, settings.output_dir, settings.trash_dir)

    def save_uploaded_file(self, file_name: str, content: bytes) -> BatchJob:
        normalized_name = Path((file_name or "").strip()).name
        if not normalized_name:
            raise ValueError("Nom de fichier manquant.")
        if not content:
            raise ValueError("Fichier vide.")

        suffix = Path(normalized_name).suffix.lower()
        if suffix not in settings.batch_supported_extensions:
            raise ValueError(f"Extension non supportée pour le batch: {suffix or '(aucune)'}.")

        target_path = self._next_available_path(settings.input_dir, normalized_name)
        target_path.write_bytes(content)
        logger.info("Batch upload stored in Input | file=%s", target_path.name)
        return self._register_input_file(target_path, source="upload")

    def list_jobs(self) -> tuple[list[dict[str, Any]], str | None]:
        with self._lock:
            ordered_jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
            active_job_id = self._active_job_id
        return [job.to_dict() for job in ordered_jobs], active_job_id

    def get_job(self, job_id: str) -> BatchJob:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise ValueError("Job batch introuvable.")
        return job

    def get_transcript(self, job_id: str) -> tuple[BatchJob, str]:
        job = self.get_job(job_id)
        if not job.transcript_text:
            raise ValueError("Transcript batch indisponible.")
        return job, job.transcript_text

    def _ensure_directories(self) -> None:
        settings.input_dir.mkdir(parents=True, exist_ok=True)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        settings.trash_dir.mkdir(parents=True, exist_ok=True)

    def _scan_loop(self) -> None:
        while not self._stop_event.is_set():
            self._scan_input_directory()
            time.sleep(settings.batch_scan_interval_seconds)

    def _scan_input_directory(self) -> None:
        settings.input_dir.mkdir(parents=True, exist_ok=True)
        for candidate in settings.input_dir.iterdir():
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in settings.batch_supported_extensions:
                continue
            self._register_input_file(candidate, source="input")

    def _register_input_file(self, path: Path, source: str) -> BatchJob:
        resolved_path = str(path.resolve())
        with self._lock:
            existing_job_id = self._jobs_by_path.get(resolved_path)
            if existing_job_id is not None:
                return self._jobs[existing_job_id]

            now = _utc_now()
            job = BatchJob(
                job_id=uuid4().hex,
                file_name=path.name,
                input_path=resolved_path,
                source=source,
                status="queued",
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.job_id] = job
            self._jobs_by_path[resolved_path] = job.job_id
            self._queue.put(job.job_id)

        self._publish_job_event(job, "INFO", f"Fichier ajouté à la file batch : {job.file_name}", code="batch.enqueued")
        return job

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                job = self.get_job(job_id)
            except ValueError:
                self._queue.task_done()
                continue

            input_path = Path(job.input_path)
            if not input_path.exists():
                self._fail_job(job, "Fichier introuvable dans Input.")
                self._queue.task_done()
                continue

            if not self._wait_until_ready(input_path, job):
                self._fail_job(job, "Fichier toujours en cours d'écriture ou verrouillé.")
                self._queue.task_done()
                continue

            self._set_active_job(job.job_id)
            self._update_job(job, status="processing", error=None)
            self._publish_job_event(job, "INFO", f"Traitement batch démarré : {job.file_name}", code="batch.processing")
            system_state.update(status="processing", active_file=job.file_name)
            system_state.update_service("batch", "processing", job.file_name)

            try:
                transcript_text = self._process_job(input_path)
                output_path = self._write_transcript_file(input_path.stem, transcript_text)
                archived_source_path = self._archive_source_file(input_path)
                self._complete_job(job, transcript_text, output_path, archived_source_path)
            except Exception as error:
                archived_source_path = None
                if input_path.exists():
                    try:
                        archived_source_path = str(self._archive_source_file(input_path))
                    except Exception:
                        archived_source_path = None
                self._fail_job(job, str(error), archived_source_path)
            finally:
                self._set_active_job(None)
                system_state.update(status="idle", active_file=None)
                system_state.update_service("batch", "ready", f"En attente dans {settings.input_dir.name}")
                self._queue.task_done()

    def _process_job(self, input_path: Path) -> str:
        _, segments = asyncio.run(self.engine.transcribe_file(input_path))
        if not segments:
            raise RuntimeError("Aucun segment Whisper exploitable n'a été produit.")

        speakers = self._resolve_speakers(input_path, segments)
        return self._format_transcript_paragraphs(segments, speakers)

    def _format_transcript_paragraphs(
        self,
        segments: list[TranscribedSegment],
        speakers: list[str],
    ) -> str:
        paragraphs: list[str] = []
        buffer_speaker: str | None = None
        buffer_text: list[str] = []
        buffer_start = 0.0
        buffer_end = 0.0

        for segment, speaker in zip(segments, speakers):
            cleaned_text = segment.text.strip()
            if not cleaned_text:
                continue

            if speaker == buffer_speaker:
                buffer_text.append(cleaned_text)
                buffer_end = segment.end
                continue

            if buffer_speaker is not None and buffer_text:
                paragraphs.append(
                    f"[{_format_seconds(buffer_start)} -> {_format_seconds(buffer_end)}] [{buffer_speaker}] {' '.join(buffer_text).strip()}"
                )

            buffer_speaker = speaker
            buffer_text = [cleaned_text]
            buffer_start = segment.start
            buffer_end = segment.end

        if buffer_speaker is not None and buffer_text:
            paragraphs.append(
                f"[{_format_seconds(buffer_start)} -> {_format_seconds(buffer_end)}] [{buffer_speaker}] {' '.join(buffer_text).strip()}"
            )

        return "\n\n".join(paragraphs).strip()

    def _resolve_speakers(self, input_path: Path, segments: list[TranscribedSegment]) -> list[str]:
        if not segments:
            return []

        try:
            pipeline = self._get_pyannote_pipeline()
            if pipeline is None:
                raise RuntimeError("Pipeline Pyannote indisponible")

            import numpy as np
            import soundfile as sf
            import torch

            audio_data, sample_rate = sf.read(str(input_path))
            waveform = np.asarray(audio_data, dtype=np.float32)
            if waveform.ndim == 1:
                waveform = waveform[np.newaxis, :]
            else:
                waveform = waveform.T
            audio_tensor = torch.from_numpy(waveform).float()
            diarization = pipeline({"waveform": audio_tensor, "sample_rate": sample_rate})

            aliases: dict[str, str] = {}
            labels: list[str] = []
            for segment in segments:
                best_speaker: str | None = None
                best_overlap = 0.0
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    overlap = max(0.0, min(float(turn.end), segment.end) - max(float(turn.start), segment.start))
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_speaker = str(speaker)

                if best_speaker is None:
                    labels.append("Interlocuteur 1")
                    continue

                if best_speaker not in aliases:
                    aliases[best_speaker] = f"Interlocuteur {len(aliases) + 1}"
                labels.append(aliases[best_speaker])

            logger.info("Pyannote diarization completed for %s", input_path.name)
            return labels
        except Exception as error:
            logger.warning("Pyannote unavailable for %s, fallback mono-speaker | %s", input_path.name, error)
            return ["Interlocuteur 1"] * len(segments)

    def _get_pyannote_pipeline(self) -> Any | None:
        with self._pyannote_lock:
            if self._pyannote_pipeline is not None:
                return self._pyannote_pipeline

            try:
                from pyannote.audio import Pipeline

                kwargs: dict[str, Any] = {}
                if settings.huggingface_token:
                    kwargs["use_auth_token"] = settings.huggingface_token
                self._pyannote_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", **kwargs)
                return self._pyannote_pipeline
            except Exception as error:
                logger.warning("Unable to initialize Pyannote pipeline | %s", error)
                return None

    def _wait_until_ready(self, input_path: Path, job: BatchJob) -> bool:
        previous_size = -1
        stable_count = 0

        for attempt in range(settings.batch_stability_max_checks):
            if not input_path.exists():
                return False

            try:
                current_size = input_path.stat().st_size
                logger.info(
                    "Batch readiness check | file=%s | attempt=%s/%s | size=%s | previous=%s | stable=%s",
                    job.file_name,
                    attempt + 1,
                    settings.batch_stability_max_checks,
                    current_size,
                    previous_size,
                    stable_count,
                )

                if current_size == previous_size and current_size > 0:
                    stable_count += 1
                else:
                    previous_size = current_size
                    stable_count = 0

                if stable_count >= settings.batch_stability_required_checks:
                    with input_path.open("ab"):
                        pass
                    return True
            except OSError:
                stable_count = 0

            time.sleep(settings.batch_stability_check_seconds)

        return False

    def _write_transcript_file(self, original_stem: str, transcript_text: str) -> Path:
        output_path = self._next_available_path(settings.output_dir, f"{original_stem}.txt")
        output_path.write_text(transcript_text + "\n", encoding="utf-8")
        return output_path

    def _archive_source_file(self, input_path: Path) -> Path:
        archived_path = self._next_available_path(settings.trash_dir, input_path.name)
        shutil.move(str(input_path), str(archived_path))
        return archived_path

    def _complete_job(self, job: BatchJob, transcript_text: str, output_path: Path, archived_source_path: Path) -> None:
        self._update_job(
            job,
            status="completed",
            output_file_name=output_path.name,
            output_file_path=str(output_path),
            archived_source_path=str(archived_source_path),
            transcript_text=transcript_text,
            error=None,
        )
        self._publish_job_event(job, "INFO", f"Traitement batch terminé : {job.file_name}", code="batch.completed")

    def _fail_job(self, job: BatchJob, error_message: str, archived_source_path: str | None = None) -> None:
        self._update_job(job, status="failed", error=error_message, archived_source_path=archived_source_path)
        self._publish_job_event(job, "ERROR", f"Échec batch pour {job.file_name} : {error_message}", code="batch.failed")
        system_state.update(status="error", last_error=error_message)

    def _update_job(self, job: BatchJob, **fields: Any) -> None:
        with self._lock:
            current_job = self._jobs[job.job_id]
            for key, value in fields.items():
                setattr(current_job, key, value)
            current_job.updated_at = _utc_now()

    def _publish_job_event(self, job: BatchJob, level: str, message: str, *, code: str) -> None:
        event_bus.publish(
            level=level,
            source="batch",
            message=message,
            code=code,
            job_id=job.job_id,
            payload={"job": job.to_dict()},
        )
        logger.log(logging.ERROR if level.upper() == "ERROR" else logging.INFO, message)

    def _set_active_job(self, job_id: str | None) -> None:
        with self._lock:
            self._active_job_id = job_id

    def _next_available_path(self, directory: Path, file_name: str) -> Path:
        base_path = directory / Path(file_name).name
        stem = base_path.stem
        suffix = base_path.suffix
        candidate = base_path
        index = 1
        while candidate.exists():
            candidate = directory / f"{stem}_{index:02d}{suffix}"
            index += 1
        return candidate
