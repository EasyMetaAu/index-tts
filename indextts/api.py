"""
FastAPI-based REST API for IndexTTS2.

This module provides a reusable API that can be mounted alongside Gradio WebUI
or run standalone. It accepts an initialized IndexTTS2 instance to avoid
duplicate model loading.

Usage:
    from indextts.api import create_api_app
    api_app = create_api_app(tts_instance)
"""

import os
import time
import uuid
import threading
from enum import Enum
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TTSRequest(BaseModel):
    """Request model for TTS task creation."""
    text: str = Field(..., description="Text to synthesize")
    prompt_audio: str = Field(..., description="Path to speaker reference audio file")
    emo_audio_prompt: Optional[str] = Field(None, description="Path to emotion reference audio")
    emo_weight: float = Field(0.65, ge=0.0, le=1.0, description="Emotion weight")
    emo_vector: Optional[list[float]] = Field(None, description="8-dimensional emotion vector")
    max_text_tokens_per_segment: int = Field(120, ge=20, le=500, description="Max tokens per segment")
    sync: bool = Field(False, description="If true, wait for completion and return audio directly")

    # Generation parameters
    do_sample: bool = Field(True, description="Whether to use sampling")
    temperature: float = Field(0.8, ge=0.1, le=2.0)
    top_p: float = Field(0.8, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(30, ge=0, le=100)
    repetition_penalty: float = Field(10.0, ge=0.1, le=20.0)


class TaskResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: TaskStatus
    message: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None


class TaskStore:
    """Thread-safe in-memory task store."""

    def __init__(self, output_dir: str = "outputs/tasks"):
        self.tasks: dict[str, dict] = {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())
        with self._lock:
            self.tasks[task_id] = {
                "status": TaskStatus.PENDING,
                "created_at": time.time(),
                "completed_at": None,
                "output_path": None,
                "error": None,
            }
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        with self._lock:
            return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs):
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)

    def get_output_path(self, task_id: str) -> Path:
        return self.output_dir / f"{task_id}.wav"


def create_api_app(tts, output_dir: str = "outputs/tasks") -> FastAPI:
    """
    Create a FastAPI application for TTS inference.

    Args:
        tts: Initialized IndexTTS2 instance
        output_dir: Directory for storing generated audio files

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="IndexTTS2 API",
        description="REST API for IndexTTS2 Text-to-Speech synthesis",
        version="2.0.0",
    )

    task_store = TaskStore(output_dir)

    def run_tts_task(task_id: str, request: TTSRequest):
        """Background task for TTS generation."""
        try:
            task_store.update_task(task_id, status=TaskStatus.PROCESSING)

            output_path = str(task_store.get_output_path(task_id))

            # Prepare generation kwargs
            kwargs = {
                "do_sample": request.do_sample,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k if request.top_k and request.top_k > 0 else None,
                "repetition_penalty": request.repetition_penalty,
            }

            # Run inference
            result = tts.infer(
                spk_audio_prompt=request.prompt_audio,
                text=request.text,
                output_path=output_path,
                emo_audio_prompt=request.emo_audio_prompt,
                emo_alpha=request.emo_weight,
                emo_vector=request.emo_vector,
                max_text_tokens_per_segment=request.max_text_tokens_per_segment,
                **kwargs
            )

            if result and os.path.exists(output_path):
                task_store.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    completed_at=time.time(),
                    output_path=output_path
                )
            else:
                task_store.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    completed_at=time.time(),
                    error="TTS generation returned no output"
                )

        except Exception as e:
            task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                completed_at=time.time(),
                error=str(e)
            )

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "model_version": getattr(tts, "model_version", "unknown")}

    @app.post("/api/v1/tts/tasks", response_model=TaskResponse)
    async def create_tts_task(
        request: TTSRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Create a new TTS task.

        If sync=true, waits for completion and returns audio directly.
        Otherwise, returns task ID for polling.
        """
        # Validate prompt audio exists
        if not os.path.exists(request.prompt_audio):
            raise HTTPException(status_code=400, detail=f"Prompt audio file not found: {request.prompt_audio}")

        if request.emo_audio_prompt and not os.path.exists(request.emo_audio_prompt):
            raise HTTPException(status_code=400, detail=f"Emotion audio file not found: {request.emo_audio_prompt}")

        task_id = task_store.create_task()

        if request.sync:
            # Synchronous mode: run immediately and return audio
            run_tts_task(task_id, request)
            task = task_store.get_task(task_id)

            if task["status"] == TaskStatus.COMPLETED and task["output_path"]:
                return FileResponse(
                    task["output_path"],
                    media_type="audio/wav",
                    filename=f"{task_id}.wav"
                )
            else:
                raise HTTPException(status_code=500, detail=task.get("error", "TTS generation failed"))
        else:
            # Async mode: queue task and return immediately
            background_tasks.add_task(run_tts_task, task_id, request)
            task = task_store.get_task(task_id)

            return TaskResponse(
                task_id=task_id,
                status=task["status"],
                message="Task queued for processing",
                created_at=task["created_at"]
            )

    @app.get("/api/v1/tts/tasks")
    async def sync_tts(
        text: str = Query(..., description="Text to synthesize"),
        prompt_audio: str = Query(..., description="Path to speaker reference audio"),
        emo_audio_prompt: Optional[str] = Query(None, description="Path to emotion reference audio"),
        emo_weight: float = Query(0.65, ge=0.0, le=1.0),
        max_text_tokens_per_segment: int = Query(120, ge=20, le=500),
    ):
        """
        Synchronous TTS generation via GET request.

        Returns audio file directly.
        """
        if not os.path.exists(prompt_audio):
            raise HTTPException(status_code=400, detail=f"Prompt audio file not found: {prompt_audio}")

        if emo_audio_prompt and not os.path.exists(emo_audio_prompt):
            raise HTTPException(status_code=400, detail=f"Emotion audio file not found: {emo_audio_prompt}")

        task_id = task_store.create_task()
        output_path = str(task_store.get_output_path(task_id))

        try:
            task_store.update_task(task_id, status=TaskStatus.PROCESSING)

            result = tts.infer(
                spk_audio_prompt=prompt_audio,
                text=text,
                output_path=output_path,
                emo_audio_prompt=emo_audio_prompt,
                emo_alpha=emo_weight,
                max_text_tokens_per_segment=max_text_tokens_per_segment,
            )

            if result and os.path.exists(output_path):
                task_store.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    completed_at=time.time(),
                    output_path=output_path
                )
                return FileResponse(
                    output_path,
                    media_type="audio/wav",
                    filename=f"{task_id}.wav"
                )
            else:
                raise HTTPException(status_code=500, detail="TTS generation failed")

        except Exception as e:
            task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                completed_at=time.time(),
                error=str(e)
            )
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/tts/tasks/{task_id}", response_model=TaskResponse)
    async def get_task_status(task_id: str):
        """Get the status of a TTS task."""
        task = task_store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return TaskResponse(
            task_id=task_id,
            status=task["status"],
            message=task.get("error"),
            created_at=task["created_at"],
            completed_at=task.get("completed_at")
        )

    @app.get("/api/v1/tts/tasks/{task_id}/result")
    async def get_task_result(task_id: str):
        """Download the audio result of a completed task."""
        task = task_store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        if task["status"] != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Task not completed. Current status: {task['status']}"
            )

        output_path = task.get("output_path")
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Audio file not found")

        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"{task_id}.wav"
        )

    return app
