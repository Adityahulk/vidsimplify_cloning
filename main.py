from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sync import Sync
from sync.common import Audio, GenerationOptions, Video, Tts
from elevenlabs.client import ElevenLabs
from google.cloud import storage
from google.oauth2 import service_account
from io import BytesIO
from dotenv import load_dotenv
import os
import uuid
import json
import base64
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Sync API Wrapper")

# Initialize clients (API keys from environment variables)
SYNC_API_KEY = os.getenv("SYNC_API_KEY", "YOUR_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_API_KEY")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-bucket-name")

client = Sync(api_key=SYNC_API_KEY)
elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Initialize Google Cloud Storage client
def initialize_gcs_client():
    """Initialize GCS client with support for both file and env var credentials"""
    try:
        # Check if credentials are provided as base64 encoded JSON in env var
        gcs_creds_base64 = os.getenv("GCS_CREDENTIALS_BASE64")
        if gcs_creds_base64:
            print("Using GCS credentials from GCS_CREDENTIALS_BASE64 environment variable")
            creds_json = base64.b64decode(gcs_creds_base64).decode('utf-8')
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            return storage.Client(credentials=credentials, project=creds_dict.get('project_id'))
        
        # Check if credentials JSON is provided directly in env var
        gcs_creds_json = os.getenv("GCS_CREDENTIALS_JSON")
        if gcs_creds_json:
            print("Using GCS credentials from GCS_CREDENTIALS_JSON environment variable")
            creds_dict = json.loads(gcs_creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            return storage.Client(credentials=credentials, project=creds_dict.get('project_id'))
        
        # Fall back to default credentials (file path or application default)
        print("Using GCS default credentials (GOOGLE_APPLICATION_CREDENTIALS or application default)")
        return storage.Client()
    
    except Exception as e:
        print(f"Warning: Could not initialize GCS client: {e}")
        return None

storage_client = initialize_gcs_client()


# Request/Response models
class ElevenLabsProvider(BaseModel):
    name: str = "elevenlabs"
    voiceId: str  # id of the voice to be used for generation
    script: str   # script to be used for generation

class Provider(BaseModel):
    ElevenLabs: ElevenLabsProvider

class TTSInput(BaseModel):
    type: str = "text"
    provider: Provider

class InputItem(BaseModel):
    type: str  # "video", "audio", or "text"
    url: Optional[str] = None  # For video/audio
    provider: Optional[Provider] = None  # For TTS


class GenerationOptionsModel(BaseModel):
    sync_mode: Optional[str] = None


class CreateGenerationRequest(BaseModel):
    input: List[InputItem]
    model: str = "lipsync-2"
    options: Optional[GenerationOptionsModel] = None


class GenerationResponse(BaseModel):
    createdAt: str
    id: str
    input: List[Dict[str, str]]
    model: str
    status: str
    error: str
    options: Dict[str, Any]
    outputDuration: float
    outputUrl: str
    webhookUrl: str


class EstimateCostResponse(BaseModel):
    estimatedFrameCount: float
    estimatedGenerationCost: float


# Voice cloning models
class VoiceCloneResponse(BaseModel):
    voice_id: str
    name: str
    description: Optional[str] = None


class VoiceInfoResponse(BaseModel):
    voice_id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None


class ProfessionalVoiceCloneRequest(BaseModel):
    name: str
    language: str = "en"
    description: Optional[str] = None


class VideoUploadResponse(BaseModel):
    url: str
    filename: str
    size_bytes: int
    uploaded_at: str


# Endpoints
@app.post("/generations", response_model=Dict)
async def create_generation(request: CreateGenerationRequest):
    """Create a new generation"""
    try:
        # Convert input items to appropriate types
        input_items = []
        for item in request.input:
            if item.type == "video":
                if not item.url:
                    raise HTTPException(status_code=400, detail="URL is required for video input")
                input_items.append(Video(url=item.url))
            elif item.type == "audio":
                if not item.url:
                    raise HTTPException(status_code=400, detail="URL is required for audio input")
                input_items.append(Audio(url=item.url))
            elif item.type == "text":
                if not item.provider:
                    raise HTTPException(status_code=400, detail="Provider is required for TTS input")
                # Create TTS object with Eleven Labs provider
                elevenlabs_config = item.provider.ElevenLabs
                tts_obj = Tts(
                    type="text",
                    provider={
                        "name": elevenlabs_config.name,
                        "voiceId": elevenlabs_config.voiceId,
                        "script": elevenlabs_config.script
                    }
                )
                input_items.append(tts_obj)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid input type: {item.type}")
        
        # Prepare options
        options = None
        if request.options:
            options = GenerationOptions(
                sync_mode=request.options.sync_mode
            )
        
        print(input_items)
        # Create generation
        response = client.generations.create(
            input=input_items,
            model=request.model,
            options=options
        )
        
        # Convert response object to dict
        return response.dict() if hasattr(response, 'dict') else response.__dict__
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generations/{generation_id}", response_model=Dict)
async def get_generation(generation_id: str):
    """Get a generation by ID"""
    try:
        response = client.generations.get(id=generation_id)
        # Convert response object to dict
        return response.dict() if hasattr(response, 'dict') else response.__dict__
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generations/estimate-cost", response_model=Dict)
async def estimate_cost(request: CreateGenerationRequest):
    """Estimate the cost of a generation"""
    try:
        # Convert input items to appropriate types
        input_items = []
        for item in request.input:
            if item.type == "video":
                if not item.url:
                    raise HTTPException(status_code=400, detail="URL is required for video input")
                input_items.append(Video(url=item.url))
            elif item.type == "audio":
                if not item.url:
                    raise HTTPException(status_code=400, detail="URL is required for audio input")
                input_items.append(Audio(url=item.url))
            elif item.type == "text":
                if not item.provider:
                    raise HTTPException(status_code=400, detail="Provider is required for TTS input")
                # Create TTS object with Eleven Labs provider
                elevenlabs_config = item.provider.ElevenLabs
                tts_obj = Tts(
                    type="text",
                    provider={
                        "name": elevenlabs_config.name,
                        "voiceId": elevenlabs_config.voiceId,
                        "script": elevenlabs_config.script
                    }
                )
                input_items.append(tts_obj)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid input type: {item.type}")
        
        # Prepare options
        options = None
        if request.options:
            options = GenerationOptions(
                sync_mode=request.options.sync_mode
            )
        
        # Estimate cost
        response = client.generations.estimate_cost(
            input=input_items,
            model=request.model,
            options=options
        )
        
        # Convert response object to dict if needed
        return response.dict() if hasattr(response, 'dict') else response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice-cloning/ivc", response_model=VoiceCloneResponse)
async def create_instant_voice_clone(
    name: str,
    files: List[UploadFile] = File(...)
):
    """Create an instant voice clone using uploaded audio files"""
    try:
        # Convert uploaded files to BytesIO objects
        audio_files = []
        for file in files:
            content = await file.read()
            audio_files.append(BytesIO(content))
        
        # Create voice clone
        voice = elevenlabs.voices.ivc.create(
            name=name,
            files=audio_files
        )
        
        return VoiceCloneResponse(
            voice_id=voice.voice_id,
            name=voice.name,
            description=getattr(voice, 'description', None)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voices/{voice_id}", response_model=VoiceInfoResponse)
async def get_voice(voice_id: str):
    """Get voice information by voice ID"""
    try:
        voice = elevenlabs.voices.get(voice_id=voice_id)
        
        return VoiceInfoResponse(
            voice_id=voice.voice_id,
            name=voice.name,
            category=getattr(voice, 'category', None),
            description=getattr(voice, 'description', None),
            preview_url=getattr(voice, 'preview_url', None),
            labels=getattr(voice, 'labels', None),
            settings=getattr(voice, 'settings', None)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/video", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file to Google Cloud Storage and return public URL"""
    try:
        # Check if GCS client is initialized
        if storage_client is None:
            raise HTTPException(
                status_code=500, 
                detail="Google Cloud Storage is not configured. Please set up GCS credentials."
            )
        
        # Validate file type
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{timestamp}_{unique_id}_{file.filename}"
        
        # Upload to GCS
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(safe_filename)
        
        # Set content type based on file extension
        content_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv'
        }
        content_type = content_types.get(file_extension, 'video/mp4')
        
        # Upload the file
        blob.upload_from_string(content, content_type=content_type)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Get public URL
        public_url = blob.public_url
        
        return VideoUploadResponse(
            url=public_url,
            filename=safe_filename,
            size_bytes=file_size,
            uploaded_at=datetime.now().isoformat()
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Sync API Wrapper is running"}
