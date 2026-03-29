from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SaveRequest(BaseModel):
    content: str = Field(..., min_length=1)
    base_name: str | None = None


class SaveResponse(BaseModel):
    file_name: str
    file_path: str
    saved_at: str


class AudioSessionResponse(BaseModel):
    session_id: str
    base_name: str


class OllamaModelsResponse(BaseModel):
    models: list[str]
    default_model: str | None = None


class TranscriptionModelsResponse(BaseModel):
    models: list[str]
    current_model: str


class SummaryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    model: str | None = None


class SummaryResponse(BaseModel):
    model: str
    output: str


class AIRequest(BaseModel):
    content: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    instruction: str | None = None
    model: str | None = None


class AIResponse(BaseModel):
    model: str
    action: str
    output: str


class LogEventResponse(BaseModel):
    event_id: int
    timestamp: str
    level: str
    source: str
    message: str
    code: str | None = None
    job_id: str | None = None
    payload: dict[str, Any] | None = None


class RecentLogsResponse(BaseModel):
    events: list[LogEventResponse]


class ServiceStateResponse(BaseModel):
    name: str
    status: str
    detail: str | None = None
    updated_at: str


class SystemStateResponse(BaseModel):
    status: str
    started_at: str
    updated_at: str
    paused: bool
    active_file: str | None = None
    eta: str | None = None
    transcription_model: str | None = None
    ollama_model: str | None = None
    history_dir: str
    log_file: str
    last_error: str | None = None
    services: list[ServiceStateResponse]


class BatchJobResponse(BaseModel):
    job_id: str
    file_name: str
    source: str
    status: str
    created_at: str
    updated_at: str
    output_file_name: str | None = None
    output_file_path: str | None = None
    archived_source_path: str | None = None
    error: str | None = None


class BatchQueueResponse(BaseModel):
    jobs: list[BatchJobResponse]
    input_dir: str
    output_dir: str
    trash_dir: str
    active_job_id: str | None = None


class BatchUploadResponse(BaseModel):
    job: BatchJobResponse


class BatchTranscriptResponse(BaseModel):
    job: BatchJobResponse
    transcript: str


class TranscriptEntryResponse(BaseModel):
    file_name: str
    file_path: str
    updated_at: str


class TranscriptListResponse(BaseModel):
    entries: list[TranscriptEntryResponse]


class TranscriptContentResponse(BaseModel):
    file_name: str
    content: str


class TranscriptUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1)


class TranscriptDeleteResponse(BaseModel):
    file_name: str
    deleted: bool


class WorkbenchTransformRequest(BaseModel):
    content: str = Field(..., min_length=1)
    operation: str = Field(..., min_length=1)
    include_summary: bool = False
    prompt: str | None = None
    model: str | None = None


class WorkbenchTransformResponse(BaseModel):
    model: str | None = None
    operation: str
    output: str
    summary: str | None = None
    version_label: str

