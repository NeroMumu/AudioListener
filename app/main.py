from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from app.batch import BatchProcessor
from app.config import settings
from app.core.events import event_bus
from app.core.logging import configure_logging
from app.core.state import system_state
from app.models import (
    AIRequest,
    AIResponse,
    AudioSessionResponse,
    BatchJobResponse,
    BatchQueueResponse,
    BatchTranscriptResponse,
    BatchUploadResponse,
    LogEventResponse,
    OllamaModelsResponse,
    RecentLogsResponse,
    SaveRequest,
    SaveResponse,
    SystemStateResponse,
    SummaryRequest,
    SummaryResponse,
    TranscriptContentResponse,
    TranscriptDeleteResponse,
    TranscriptListResponse,
    TranscriptUpdateRequest,
    TranscriptionModelsResponse,
    WorkbenchTransformRequest,
    WorkbenchTransformResponse,
)
from app.ollama import OllamaError, generate_ai_output, generate_summary_actions, get_default_summary_model, list_local_models
from app.storage import (
    append_audio_chunk,
    delete_saved_transcript,
    discard_audio_recording,
    finalize_audio_recording,
    list_saved_transcripts,
    read_saved_transcript,
    save_audio_recording,
    save_transcript,
    start_audio_recording_session,
    update_saved_transcript,
)
from app.transcription import TranscriptionEngine


configure_logging(settings.server_log_file, settings.log_level)
logger = logging.getLogger(__name__)
app = FastAPI(title="Audio Journal", version="1.0.0")
engine = TranscriptionEngine()
batch_processor = BatchProcessor(engine)
startup_preload_task: asyncio.Task[None] | None = None

system_state.set_paths(history_dir=str(settings.history_dir), log_file=str(settings.server_log_file))
system_state.update(
    status="starting",
    transcription_model=engine.get_active_model(),
    ollama_model=settings.ollama_model or None,
)
system_state.update_service("api", "starting", "Initialisation FastAPI")
system_state.update_service("transcription", "starting", f"Préchargement du modèle {engine.get_active_model()}")
system_state.update_service("ollama", "unknown", settings.ollama_base_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.middleware("http")
async def disable_cache_for_ui(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


async def _preload_transcription_model() -> None:
    system_state.update_service("api", "ready", "Serveur HTTP prêt")
    system_state.update_service("transcription", "loading", f"Chargement du modèle {engine.get_active_model()}")
    try:
        logger.info("Preloading transcription model %s", engine.get_active_model())
        await engine.ensure_model()
        batch_processor.start()
        logger.info("Transcription model ready")
        system_state.update(status="idle", transcription_model=engine.get_active_model(), last_error=None)
        system_state.update_service("transcription", "ready", engine.get_active_model())
    except Exception:  # pragma: no cover - startup diagnostics only
        logger.exception("Unable to preload transcription model")
        system_state.update(status="error", last_error="Unable to preload transcription model")
        system_state.update_service("transcription", "error", "Préchargement impossible")


@app.on_event("startup")
async def preload_transcription_model() -> None:
    global startup_preload_task

    system_state.update_service("api", "ready", "Serveur HTTP prêt")
    startup_preload_task = asyncio.create_task(_preload_transcription_model())


@app.get("/")
async def read_index() -> FileResponse:
    return FileResponse(
        settings.static_dir / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/health")
async def healthcheck() -> dict[str, str]:
    logger.info("Healthcheck requested | whisper_model=%s | language=%s", engine.get_active_model(), settings.language)
    return {
        "status": "ok",
        "model": engine.get_active_model(),
        "language": settings.language,
        "history_dir": str(settings.history_dir),
        "ollama_url": settings.ollama_base_url,
    }


@app.get("/api/system/state", response_model=SystemStateResponse)
async def get_system_state() -> SystemStateResponse:
    return SystemStateResponse(**system_state.snapshot())


@app.get("/api/logs/recent", response_model=RecentLogsResponse)
async def get_recent_logs(limit: int = Query(default=100, ge=1, le=500)) -> RecentLogsResponse:
    events = [LogEventResponse(**event.to_dict()) for event in event_bus.recent(limit)]
    return RecentLogsResponse(events=events)


@app.get("/api/transcription/models", response_model=TranscriptionModelsResponse)
async def get_transcription_models() -> TranscriptionModelsResponse:
    return TranscriptionModelsResponse(models=engine.list_available_models(), current_model=engine.get_active_model())


@app.post("/api/batch/upload", response_model=BatchUploadResponse)
async def upload_batch_file(request: Request) -> BatchUploadResponse:
    raw_file_name = request.headers.get("X-Upload-Filename", "")
    file_name = os.path.basename(raw_file_name)
    content = await request.body()

    try:
        job = batch_processor.save_uploaded_file(file_name, content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return BatchUploadResponse(job=BatchJobResponse(**job.to_dict()))


@app.get("/api/batch/jobs", response_model=BatchQueueResponse)
async def get_batch_jobs() -> BatchQueueResponse:
    jobs, active_job_id = batch_processor.list_jobs()
    return BatchQueueResponse(
        jobs=[BatchJobResponse(**job) for job in jobs],
        input_dir=str(settings.input_dir),
        output_dir=str(settings.output_dir),
        trash_dir=str(settings.trash_dir),
        active_job_id=active_job_id,
    )


@app.get("/api/batch/jobs/{job_id}/transcript", response_model=BatchTranscriptResponse)
async def get_batch_transcript(job_id: str) -> BatchTranscriptResponse:
    try:
        job, transcript = batch_processor.get_transcript(job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return BatchTranscriptResponse(job=BatchJobResponse(**job.to_dict()), transcript=transcript)


@app.get("/api/transcripts", response_model=TranscriptListResponse)
async def get_saved_transcripts(limit: int = Query(default=100, ge=1, le=500)) -> TranscriptListResponse:
    return TranscriptListResponse(entries=list_saved_transcripts(limit))


@app.get("/api/transcripts/{file_name}", response_model=TranscriptContentResponse)
async def get_saved_transcript(file_name: str) -> TranscriptContentResponse:
    try:
        resolved_name, content = read_saved_transcript(file_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return TranscriptContentResponse(file_name=resolved_name, content=content)


@app.put("/api/transcripts/{file_name}", response_model=TranscriptContentResponse)
async def update_transcript(file_name: str, payload: TranscriptUpdateRequest) -> TranscriptContentResponse:
    try:
        resolved_name, content = update_saved_transcript(file_name, payload.content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info("Transcript updated | file=%s", resolved_name)
    return TranscriptContentResponse(file_name=resolved_name, content=content)


@app.delete("/api/transcripts/{file_name}", response_model=TranscriptDeleteResponse)
async def delete_transcript(file_name: str) -> TranscriptDeleteResponse:
    try:
        resolved_name = delete_saved_transcript(file_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    logger.info("Transcript deleted | file=%s", resolved_name)
    return TranscriptDeleteResponse(file_name=resolved_name, deleted=True)


@app.post("/api/workbench/transform", response_model=WorkbenchTransformResponse)
async def transform_workbench_document(payload: WorkbenchTransformRequest) -> WorkbenchTransformResponse:
    try:
        model_name, transformed_output = await asyncio.to_thread(
            generate_ai_output,
            payload.operation,
            payload.content,
            payload.prompt,
            payload.model,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OllamaError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    summary_output: str | None = None
    final_output = transformed_output
    version_label = payload.operation.strip().lower()

    if payload.include_summary:
        try:
            summary_model, summary_output = await asyncio.to_thread(
                generate_ai_output,
                "summarize",
                transformed_output,
                None,
                payload.model,
            )
            model_name = summary_model or model_name
        except (ValueError, OllamaError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        final_output = f"Résumé\n\n{summary_output.strip()}\n\n---\n\n{transformed_output.strip()}"
        version_label = f"{version_label} + résumé"

    logger.info("Workbench transform generated with model %s for operation %s", model_name, payload.operation)
    return WorkbenchTransformResponse(
        model=model_name,
        operation=payload.operation,
        output=final_output,
        summary=summary_output,
        version_label=version_label,
    )


@app.get("/api/ollama/models", response_model=OllamaModelsResponse)
async def get_ollama_models() -> OllamaModelsResponse:
    try:
        models = await asyncio.to_thread(list_local_models)
    except OllamaError as error:
        system_state.update_service("ollama", "error", str(error))
        raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        default_model = get_default_summary_model(models) if models else None
    except OllamaError:
        default_model = settings.ollama_model or (models[0] if models else None)

    system_state.update(ollama_model=default_model)
    system_state.update_service("ollama", "ready" if models else "empty", default_model or "Aucun modèle")

    return OllamaModelsResponse(models=models, default_model=default_model)


@app.post("/api/summary", response_model=SummaryResponse)
async def generate_summary(payload: SummaryRequest) -> SummaryResponse:
    try:
        model_name, output = await asyncio.to_thread(generate_summary_actions, payload.content, payload.model)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OllamaError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    logger.info("Summary generated with Ollama model %s", model_name)
    system_state.update(ollama_model=model_name, last_error=None)
    system_state.update_service("ollama", "ready", model_name)
    return SummaryResponse(model=model_name, output=output)


@app.post("/api/ai", response_model=AIResponse)
async def generate_ai_result(payload: AIRequest) -> AIResponse:
    try:
        model_name, output = await asyncio.to_thread(
            generate_ai_output,
            payload.action,
            payload.content,
            payload.instruction,
            payload.model,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OllamaError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    logger.info("AI response generated with Ollama model %s for action %s", model_name, payload.action)
    system_state.update(ollama_model=model_name, last_error=None)
    system_state.update_service("ollama", "ready", model_name)
    return AIResponse(model=model_name, action=payload.action, output=output)


@app.post("/api/save", response_model=SaveResponse)
async def save_note(payload: SaveRequest) -> SaveResponse:
    try:
        return save_transcript(payload.content, payload.base_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/audio/start", response_model=AudioSessionResponse)
async def start_audio(request: Request) -> AudioSessionResponse:
    extension = request.headers.get("X-Audio-Extension")

    try:
        return start_audio_recording_session(extension)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/audio/chunk")
async def append_audio(request: Request) -> dict[str, str]:
    audio_bytes = await request.body()
    session_id = request.headers.get("X-Audio-Session-Id", "")

    try:
        append_audio_chunk(session_id, audio_bytes)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"status": "ok"}


@app.post("/api/audio/finish", response_model=SaveResponse)
async def finish_audio(request: Request) -> SaveResponse:
    session_id = request.headers.get("X-Audio-Session-Id", "")

    try:
        response = finalize_audio_recording(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    logger.info("Audio recording finalized to %s", response.file_name)
    return response


@app.post("/api/audio/discard")
async def discard_audio(request: Request) -> dict[str, str]:
    session_id = request.headers.get("X-Audio-Session-Id", "")
    if session_id:
        discard_audio_recording(session_id)
    return {"status": "ok"}


@app.post("/api/audio/save", response_model=SaveResponse)
async def save_audio(request: Request) -> SaveResponse:
    audio_bytes = await request.body()
    extension = request.headers.get("X-Audio-Extension")
    base_name = request.headers.get("X-Audio-Basename", "")

    try:
        response = save_audio_recording(audio_bytes, base_name, extension)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    logger.info("Audio recording saved to %s", response.file_name)
    return response


@app.post("/api/history/open")
async def open_history_folder() -> dict[str, str]:
    try:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(settings.output_dir))  # type: ignore[attr-defined]
    except OSError as error:
        raise HTTPException(status_code=500, detail="Impossible d'ouvrir le dossier Output.") from error

    return {"status": "ok", "path": str(settings.output_dir)}


@app.post("/api/input/open")
async def open_input_folder() -> dict[str, str]:
    try:
        settings.input_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(settings.input_dir))  # type: ignore[attr-defined]
    except OSError as error:
        raise HTTPException(status_code=500, detail="Impossible d'ouvrir le dossier Input.") from error

    return {"status": "ok", "path": str(settings.input_dir)}


@app.post("/api/trash/open")
async def open_trash_folder() -> dict[str, str]:
    try:
        settings.trash_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(settings.trash_dir))  # type: ignore[attr-defined]
    except OSError as error:
        raise HTTPException(status_code=500, detail="Impossible d'ouvrir le dossier Trash.") from error

    return {"status": "ok", "path": str(settings.trash_dir)}


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected | active_whisper_model=%s | language=%s", engine.get_active_model(), settings.language)
    system_state.update_service("live", "connected", "Client navigateur connecté")
    session = engine.create_session()
    session.model_name = engine.get_active_model()

    async def send_debug(message: str) -> None:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "debug", "message": message})

    await websocket.send_json(
        {
            "type": "ready",
            "historyDir": str(settings.output_dir),
            "model": engine.get_active_model(),
            "language": settings.language,
        }
    )
    logger.info("Live session ready | model=%s | language=%s", engine.get_active_model(), settings.language)
    await send_debug("Modèle de transcription prêt")

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                if not session.active:
                    continue

                for event in await engine.process_audio_bytes(session, message["bytes"], send_debug):
                    await websocket.send_json(event)
                continue

            if message.get("text") is None:
                continue

            payload = json.loads(message["text"])
            message_type = payload.get("type")

            if message_type == "start":
                requested_model = payload.get("model")
                try:
                    selected_model = engine.select_model(requested_model)
                    session.model_name = selected_model
                    await engine.ensure_model(selected_model)
                    system_state.update(transcription_model=selected_model, status="starting", last_error=None)
                    system_state.update_service("transcription", "ready", selected_model)
                except ValueError as error:
                    await websocket.send_json({"type": "error", "message": str(error)})
                    system_state.update(status="error", last_error=str(error))
                    continue

                logger.info(
                    "Received start command | whisper_model=%s | session_active_before=%s",
                    session.model_name,
                    session.active,
                )
                session.active = True
                session.reset()
                session.model_name = selected_model
                system_state.update(status="listening", transcription_model=session.model_name, active_file=None, eta=None)
                logger.info("Capture démarrée · modèle %s", session.model_name)
                await send_debug(f"Capture démarrée · modèle {session.model_name}")
                await websocket.send_json({"type": "status", "status": "listening", "model": session.model_name})
            elif message_type == "stop":
                logger.info(
                    "Received stop command | buffered_chunks=%s | speech_ms=%s",
                    len(session.current_chunks),
                    session.speech_ms,
                )
                session.active = False
                system_state.update(status="stopping")
                logger.info("Capture arrêtée, finalisation du bloc en cours")
                await send_debug("Capture arrêtée, finalisation du bloc en cours")
                for event in await engine.flush(session, send_debug):
                    await websocket.send_json(event)
                system_state.update(status="idle")
                await websocket.send_json({"type": "status", "status": "stopped"})
            elif message_type == "reset":
                logger.info(
                    "Received reset command | buffered_chunks=%s | speech_ms=%s",
                    len(session.current_chunks),
                    session.speech_ms,
                )
                session.reset()
                system_state.update(status="inactive")
                logger.info("Transcription courante effacée")
                await send_debug("Transcription courante effacée")
                await websocket.send_json({"type": "status", "status": "inactive"})

    except (WebSocketDisconnect, RuntimeError):
        logger.info("WebSocket client disconnected | active=%s", session.active)
        session.active = False
        session.reset()
        system_state.update(status="idle")
        system_state.update_service("live", "disconnected", "Aucun client actif")
    except Exception as error:  # pragma: no cover - surfaced to UI
        session.active = False
        session.reset()
        system_state.update(status="error", last_error=str(error))
        system_state.update_service("live", "error", str(error))

        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": str(error)})
            await websocket.close(code=1011)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Logs WebSocket client connected")
    queue = event_bus.subscribe()

    try:
        await websocket.send_json(
            {
                "type": "snapshot",
                "events": [event.to_dict() for event in event_bus.recent(200)],
            }
        )

        while True:
            event = await queue.get()
            await websocket.send_json({"type": "event", "event": event.to_dict()})
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Logs WebSocket client disconnected")
    finally:
        event_bus.unsubscribe(queue)
