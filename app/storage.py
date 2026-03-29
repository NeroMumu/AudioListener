from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.config import settings
from app.models import AudioSessionResponse, SaveResponse, TranscriptEntryResponse


@dataclass(frozen=True)
class AudioRecordingSession:
    session_id: str
    base_name: str
    source_extension: str
    temporary_path: Path


_audio_sessions: dict[str, AudioRecordingSession] = {}
_audio_sessions_lock = Lock()


def _build_base_name(now: datetime) -> str:
    return f"{now:%Y-%m-%d_%Hh%M}_{settings.default_suffix}"


def _normalize_content(content: str) -> str:
    normalized_lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    normalized = "\n".join(normalized_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", normalized)


def _next_available_path(directory: Path, extension: str, now: datetime) -> Path:
    base_name = _build_base_name(now)
    candidate = directory / f"{base_name}{extension}"
    index = 1

    while candidate.exists():
        candidate = directory / f"{base_name}_{index:02d}{extension}"
        index += 1

    return candidate


def _next_available_base_name(directory: Path, now: datetime) -> str:
    base_name = _build_base_name(now)
    candidate = base_name
    index = 1

    with _audio_sessions_lock:
        active_base_names = {session.base_name for session in _audio_sessions.values()}

    while (
        (directory / f"{candidate}.txt").exists()
        or (directory / f"{candidate}.mp3").exists()
        or candidate in active_base_names
    ):
        candidate = f"{base_name}_{index:02d}"
        index += 1

    return candidate


def _normalize_extension(extension: str | None) -> str:
    cleaned_extension = (extension or ".webm").strip().lower()
    if not cleaned_extension:
        return ".webm"
    if not cleaned_extension.startswith("."):
        cleaned_extension = f".{cleaned_extension}"
    if not re.fullmatch(r"\.[a-z0-9]+", cleaned_extension):
        return ".webm"
    return cleaned_extension


def _normalize_base_name(base_name: str) -> str:
    cleaned_base_name = base_name.strip()
    if not cleaned_base_name:
        raise ValueError("Nom de base audio manquant.")
    if cleaned_base_name != Path(cleaned_base_name).name:
        raise ValueError("Nom de base audio invalide.")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", cleaned_base_name):
        raise ValueError("Nom de base audio invalide.")
    return cleaned_base_name


def _resolve_base_name(base_name: str | None, now: datetime) -> str:
    if base_name and base_name.strip():
        return _normalize_base_name(base_name)
    return _next_available_base_name(settings.history_dir, now)


def _get_audio_session(session_id: str) -> AudioRecordingSession:
    with _audio_sessions_lock:
        session = _audio_sessions.get(session_id)

    if session is None:
        raise ValueError("Session audio introuvable.")

    return session


def _convert_audio_to_mp3(source_path: Path, target_path: Path) -> None:
    try:
        process = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(target_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("FFmpeg est introuvable. Impossible de convertir l'enregistrement en MP3.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("La conversion MP3 a dépassé le délai autorisé.") from error

    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "Erreur FFmpeg inconnue."
        raise RuntimeError(f"Échec de conversion MP3 : {stderr}")


def save_transcript(content: str, base_name: str | None = None) -> SaveResponse:
    cleaned_content = _normalize_content(content)
    if not cleaned_content:
        raise ValueError("Impossible de sauvegarder une transcription vide.")

    settings.history_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    if base_name and base_name.strip():
        candidate = settings.history_dir / f"{_normalize_base_name(base_name)}.txt"
    else:
        candidate = _next_available_path(settings.history_dir, ".txt", now)

    candidate.write_text(cleaned_content + "\n", encoding="utf-8")

    return SaveResponse(
        file_name=candidate.name,
        file_path=str(candidate),
        saved_at=now.isoformat(timespec="seconds"),
    )


def save_audio_recording(content: bytes, base_name: str | None = None, extension: str | None = None) -> SaveResponse:
    if not content:
        raise ValueError("Impossible de sauvegarder un enregistrement audio vide.")

    settings.history_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    safe_base_name = _resolve_base_name(base_name, now)
    source_extension = _normalize_extension(extension)
    target_path = settings.history_dir / f"{safe_base_name}.mp3"

    with tempfile.NamedTemporaryFile(delete=False, suffix=source_extension, dir=settings.history_dir) as temporary_file:
        temporary_file.write(content)
        temporary_path = Path(temporary_file.name)

    try:
        _convert_audio_to_mp3(temporary_path, target_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return SaveResponse(
        file_name=target_path.name,
        file_path=str(target_path),
        saved_at=now.isoformat(timespec="seconds"),
    )


def start_audio_recording_session(extension: str | None = None) -> AudioSessionResponse:
    settings.history_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    safe_extension = _normalize_extension(extension)
    base_name = _next_available_base_name(settings.history_dir, now)
    session_id = uuid4().hex
    temporary_path = settings.history_dir / f".audio-session-{session_id}{safe_extension}"
    temporary_path.write_bytes(b"")

    session = AudioRecordingSession(
        session_id=session_id,
        base_name=base_name,
        source_extension=safe_extension,
        temporary_path=temporary_path,
    )

    with _audio_sessions_lock:
        _audio_sessions[session_id] = session

    return AudioSessionResponse(session_id=session_id, base_name=base_name)


def append_audio_chunk(session_id: str, content: bytes) -> None:
    if not content:
        return

    session = _get_audio_session(session_id)
    with session.temporary_path.open("ab") as handle:
        handle.write(content)


def finalize_audio_recording(session_id: str) -> SaveResponse:
    session = _get_audio_session(session_id)

    if not session.temporary_path.exists() or session.temporary_path.stat().st_size == 0:
        discard_audio_recording(session_id)
        raise ValueError("Impossible de finaliser un enregistrement audio vide.")

    target_path = settings.history_dir / f"{session.base_name}.mp3"
    now = datetime.now().astimezone()

    try:
        _convert_audio_to_mp3(session.temporary_path, target_path)
    finally:
        discard_audio_recording(session_id)

    return SaveResponse(
        file_name=target_path.name,
        file_path=str(target_path),
        saved_at=now.isoformat(timespec="seconds"),
    )


def discard_audio_recording(session_id: str) -> None:
    with _audio_sessions_lock:
        session = _audio_sessions.pop(session_id, None)

    if session is not None:
        session.temporary_path.unlink(missing_ok=True)


def list_saved_transcripts(limit: int = 100) -> list[TranscriptEntryResponse]:
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    candidates = sorted(
        (path for path in settings.output_dir.glob("*.txt") if path.is_file() and path.stat().st_size > 0),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    entries: list[TranscriptEntryResponse] = []
    for path in candidates[:limit]:
        updated_at = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        entries.append(
            TranscriptEntryResponse(
                file_name=path.name,
                file_path=str(path),
                updated_at=updated_at,
            )
        )

    return entries


def _normalize_transcript_file_name(file_name: str) -> str:
    cleaned_name = Path((file_name or "").strip()).name
    if not cleaned_name or cleaned_name != Path(cleaned_name).name:
        raise ValueError("Transcript introuvable.")
    if Path(cleaned_name).suffix.lower() != ".txt":
        raise ValueError("Transcript introuvable.")
    return cleaned_name


def read_saved_transcript(file_name: str) -> tuple[str, str]:
    safe_name = _normalize_transcript_file_name(file_name)
    target_path = settings.output_dir / safe_name
    if not target_path.exists() or not target_path.is_file():
        raise ValueError("Transcript introuvable.")

    return target_path.name, target_path.read_text(encoding="utf-8")


def update_saved_transcript(file_name: str, content: str) -> tuple[str, str]:
    safe_name = _normalize_transcript_file_name(file_name)
    target_path = settings.output_dir / safe_name
    if not target_path.exists() or not target_path.is_file():
        raise ValueError("Transcript introuvable.")

    cleaned_content = _normalize_content(content)
    if not cleaned_content:
        raise ValueError("Impossible d'écraser un transcript avec un contenu vide.")

    target_path.write_text(cleaned_content + "\n", encoding="utf-8")
    return target_path.name, cleaned_content


def delete_saved_transcript(file_name: str) -> str:
    safe_name = _normalize_transcript_file_name(file_name)
    target_path = settings.output_dir / safe_name
    if not target_path.exists() or not target_path.is_file():
        raise ValueError("Transcript introuvable.")

    target_path.unlink()
    return target_path.name
