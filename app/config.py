from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parent.parent
    input_dir: Path = base_dir / os.getenv("AUDIO_JOURNAL_INPUT_DIR", "Input")
    output_dir: Path = base_dir / os.getenv("AUDIO_JOURNAL_OUTPUT_DIR", "Output")
    trash_dir: Path = base_dir / os.getenv("AUDIO_JOURNAL_TRASH_DIR", "Trash")
    history_dir: Path = output_dir
    recordings_dir: Path = output_dir / "audio"
    static_dir: Path = base_dir / "static"
    model_dir: Path = base_dir / ".models"
    server_log_file: Path = base_dir / os.getenv("SERVER_LOG_FILE", "server_activity.log")
    server_host: str = os.getenv("AUDIO_JOURNAL_HOST", "127.0.0.1")
    server_port: int = int(os.getenv("AUDIO_JOURNAL_PORT", "8000"))
    server_reload: bool = _env_bool("AUDIO_JOURNAL_RELOAD", False)
    systray_poll_interval_seconds: float = float(os.getenv("AUDIO_JOURNAL_SYSTRAY_POLL_SECONDS", "5.0"))
    systray_title: str = os.getenv("AUDIO_JOURNAL_SYSTRAY_TITLE", "Audio Journal")
    systray_icon_path: Path = base_dir / os.getenv("AUDIO_JOURNAL_ICON", "")
    available_whisper_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv(
            "FASTER_WHISPER_AVAILABLE_MODELS",
            "tiny,base,small,medium,large-v1,large-v2,large-v3,large-v3-turbo",
        ).split(",")
        if model.strip()
    )
    static_version: str = os.getenv("AUDIO_JOURNAL_STATIC_VERSION", "2026-03-25-2")
    default_suffix: str = os.getenv("AUDIO_JOURNAL_SUFFIX", "OrenHome")
    model_name: str = os.getenv("FASTER_WHISPER_MODEL", "small")
    language: str = "fr"
    target_sample_rate: int = 16000
    silence_threshold: float = float(os.getenv("AUDIO_JOURNAL_SILENCE_THRESHOLD", "0.008"))
    min_speech_ms: int = int(os.getenv("AUDIO_JOURNAL_MIN_SPEECH_MS", "120"))
    pause_duration_ms: int = int(os.getenv("AUDIO_JOURNAL_PAUSE_MS", "900"))
    partial_interval_ms: int = int(os.getenv("AUDIO_JOURNAL_PARTIAL_INTERVAL_MS", "900"))
    partial_step_ms: int = int(os.getenv("AUDIO_JOURNAL_PARTIAL_STEP_MS", "700"))
    compute_type: str = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
    log_level: str = os.getenv("AUDIO_JOURNAL_LOG_LEVEL", "INFO")
    batch_scan_interval_seconds: float = float(os.getenv("AUDIO_JOURNAL_BATCH_SCAN_SECONDS", "3.0"))
    batch_stability_check_seconds: float = float(os.getenv("AUDIO_JOURNAL_BATCH_STABILITY_SECONDS", "2.0"))
    batch_stability_required_checks: int = int(os.getenv("AUDIO_JOURNAL_BATCH_STABILITY_REQUIRED_CHECKS", "2"))
    batch_stability_max_checks: int = int(os.getenv("AUDIO_JOURNAL_BATCH_STABILITY_MAX_CHECKS", "10"))
    batch_supported_extensions: tuple[str, ...] = tuple(
        extension.strip().lower()
        for extension in os.getenv(
            "AUDIO_JOURNAL_BATCH_EXTENSIONS",
            ".mp3,.m4a,.wav,.flac,.ogg,.amr,.webm,.mp4,.mov,.avi,.mkv,.mpeg,.mpg,.m4v",
        ).split(",")
        if extension.strip()
    )
    huggingface_token: str = os.getenv("HUGGINGFACE_HUB_TOKEN", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")


settings = Settings()
