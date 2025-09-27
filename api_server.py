"""
FastAPI server for the Video Dubbing and Lip-Sync System
"""
import asyncio
import os
import uuid
import tempfile
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from dubbing_pipeline import DubbingPipeline


# Pydantic models
class DubbingRequest(BaseModel):
    target_language: str
    source_language: Optional[str] = None
    enable_voice_cloning: bool = False
    chunk_duration: float = 2.0
    whisper_model: str = "tiny"
    translation_model: str = "facebook/m2m100_418M"
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC"


class DubbingResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    output_file: Optional[str] = None
    error: Optional[str] = None


# Global variables
app = FastAPI(
    title="Video Dubbing and Lip-Sync API",
    description="Real-time video dubbing with lip-sync using AI models",
    version="1.0.0"
)

# In-memory job storage (use Redis in production)
jobs = {}
pipeline = None


@app.on_event("startup")
async def startup_event():
    """Initialize the dubbing pipeline on startup"""
    global pipeline
    try:
        pipeline = DubbingPipeline(
            chunk_duration=2.0,
            whisper_model="tiny",
            device="auto"
        )
        print("✅ Dubbing pipeline initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize dubbing pipeline: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Video Dubbing and Lip-Sync API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    return {
        "status": "healthy",
        "pipeline": "ready",
        "supported_languages": len(pipeline.get_supported_languages().get("transcription", [])),
        "available_models": sum(len(models) for models in pipeline.get_available_models().values())
    }


@app.get("/languages")
async def get_supported_languages():
    """Get supported languages"""
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    return pipeline.get_supported_languages()


@app.get("/models")
async def get_available_models():
    """Get available models"""
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    return pipeline.get_available_models()


@app.post("/dub", response_model=DubbingResponse)
async def create_dubbing_job(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    target_language: str = "es",
    source_language: Optional[str] = None,
    enable_voice_cloning: bool = False,
    speaker_reference: Optional[UploadFile] = File(None),
    chunk_duration: float = 2.0,
    whisper_model: str = "tiny",
    translation_model: str = "facebook/m2m100_418M",
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC"
):
    """Create a new dubbing job"""
    global pipeline, jobs
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Validate file types
    if not video_file.content_type or not video_file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    if speaker_reference and (not speaker_reference.content_type or not speaker_reference.content_type.startswith('audio/')):
        raise HTTPException(status_code=400, detail="Speaker reference must be an audio file")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_dir = os.path.join("temp", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save uploaded files
    video_path = os.path.join(job_dir, "input_video.mp4")
    with open(video_path, "wb") as f:
        f.write(await video_file.read())
    
    speaker_path = None
    if speaker_reference:
        speaker_path = os.path.join(job_dir, "speaker_reference.wav")
        with open(speaker_path, "wb") as f:
            f.write(await speaker_reference.read())
    
    # Initialize job status
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Job created, waiting to start",
        "output_file": None,
        "error": None,
        "job_dir": job_dir,
        "video_path": video_path,
        "speaker_path": speaker_path
    }
    
    # Start background processing
    background_tasks.add_task(
        process_dubbing_job,
        job_id,
        target_language,
        source_language,
        enable_voice_cloning,
        chunk_duration,
        whisper_model,
        translation_model,
        tts_model
    )
    
    return DubbingResponse(
        job_id=job_id,
        status="pending",
        message="Dubbing job created successfully"
    )


async def process_dubbing_job(
    job_id: str,
    target_language: str,
    source_language: Optional[str],
    enable_voice_cloning: bool,
    chunk_duration: float,
    whisper_model: str,
    translation_model: str,
    tts_model: str
):
    """Process a dubbing job in the background"""
    global jobs, pipeline
    
    try:
        # Update job status
        jobs[job_id].update({
            "status": "processing",
            "progress": 10,
            "message": "Initializing pipeline..."
        })
        
        # Create pipeline with custom settings
        custom_pipeline = DubbingPipeline(
            chunk_duration=chunk_duration,
            whisper_model=whisper_model,
            translation_model=translation_model,
            tts_model=tts_model,
            device="auto",
            enable_voice_cloning=enable_voice_cloning
        )
        
        # Prepare output path
        job_data = jobs[job_id]
        output_path = os.path.join(job_data["job_dir"], "output_video.mp4")
        
        jobs[job_id].update({
            "progress": 20,
            "message": "Processing video..."
        })
        
        # Process video
        result = await custom_pipeline.process_video(
            input_video_path=job_data["video_path"],
            target_language=target_language,
            output_video_path=output_path,
            source_language=source_language,
            speaker_reference=job_data["speaker_path"]
        )
        
        if result['success']:
            jobs[job_id].update({
                "status": "completed",
                "progress": 100,
                "message": "Dubbing completed successfully",
                "output_file": output_path
            })
        else:
            jobs[job_id].update({
                "status": "failed",
                "progress": 100,
                "message": "Dubbing failed",
                "error": result.get('error', 'Unknown error')
            })
            
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "message": "Processing failed",
            "error": str(e)
        })


@app.get("/job/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a dubbing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data["progress"],
        message=job_data["message"],
        output_file=job_data["output_file"],
        error=job_data["error"]
    )


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download the result of a completed dubbing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    output_file = job_data["output_file"]
    if not output_file or not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        output_file,
        media_type='video/mp4',
        filename=f"dubbed_{job_id}.mp4"
    )


@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a dubbing job and its files"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    job_dir = job_data["job_dir"]
    
    # Delete files
    try:
        import shutil
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
    except Exception as e:
        print(f"Warning: Failed to delete job files: {e}")
    
    # Remove from memory
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}


@app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "progress": job_data["progress"],
                "message": job_data["message"]
            }
            for job_id, job_data in jobs.items()
        ]
    }


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("temp", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
