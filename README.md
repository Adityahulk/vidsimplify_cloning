# Sync API Wrapper

A simple FastAPI wrapper for the Sync API.

## Setup

### Option 1: Docker

```bash
# Build
docker build -t vidsimplify-api .

# Run
docker run -d \
  --name vidsimplify-api \
  -p 8000:8000 \
  -e SYNC_API_KEY="your_sync_api_key" \
  -e ELEVENLABS_API_KEY="your_elevenlabs_api_key" \
  -e GCS_BUCKET_NAME="vidsimplify" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/gcs-key.json" \
  -v $(pwd)/your-gcs-credentials.json:/app/gcs-key.json:ro \
  vidsimplify-api
```

📖 See [DOCKER_USAGE.md](DOCKER_USAGE.md) for detailed Docker commands and troubleshooting.

---

### Option 2: Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your API keys and configure Google Cloud Storage:
```bash
export SYNC_API_KEY="your_sync_api_key"
export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
export GCS_BUCKET_NAME="vidsimplify"
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/your-gcs-credentials.json"
```

**Note:** For video upload functionality, you need:
- A Google Cloud Storage bucket
- Service account credentials JSON file
- The bucket should allow public access for uploaded files

3. Run the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/video` | Upload video to Google Cloud Storage |
| POST | `/generations` | Create lip-sync generation |
| GET | `/generations/{id}` | Get generation status |
| POST | `/generations/estimate-cost` | Estimate generation cost |
| GET | `/voices/{voice_id}` | Get voice information |
| POST | `/voice-cloning/ivc` | Create instant voice clone |

**Base URL:** `http://localhost:8000`

---

## API Endpoints

### 1. Upload Video to Cloud Storage
**POST** `/upload/video`

Upload a video file to Google Cloud Storage and receive a public URL.

**Content-Type:** `multipart/form-data`

**Form Field:**
- `file` - Video file (supports: mp4, mov, avi, mkv, webm, flv, wmv)

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/upload/video" \
  -F "file=@myvideo.mp4"
```

**Response:**
```json
{
  "url": "https://storage.googleapis.com/vidsimplify/20251009_143052_abc12345_myvideo.mp4",
  "filename": "20251009_143052_abc12345_myvideo.mp4",
  "size_bytes": 5242880,
  "uploaded_at": "2025-10-09T14:30:52.123456"
}
```

---

### 2. Create Generation (Lip Sync)
**POST** `/generations`

Create a new lip-sync generation by combining video with audio or TTS.

**Request Body:**
```json
{
  "input": [
    {
      "type": "video",
      "url": "https://example.com/video.mp4"
    },
    {
      "type": "audio",
      "url": "https://example.com/audio.mp3"
    }
  ],
  "model": "sync-2",
  "options": {
    "sync_mode": "loop"
  }
}
```

**Alternative - Video + TTS:**
```json
{
  "input": [
    {
      "type": "video",
      "url": "https://example.com/video.mp4"
    },
    {
      "type": "text",
      "provider": {
        "ElevenLabs": {
          "name": "elevenlabs",
          "voiceId": "21m00Tcm4TlvDq8ikWAM",
          "script": "Hello, this is the text to be spoken."
        }
      }
    }
  ],
  "model": "sync-2",
  "options": {
    "sync_mode": "loop"
  }
}
```

**Parameters:**
- `input` (array, required): Array of input items
  - `type` (string): "video", "audio", or "text"
  - `url` (string): URL for video/audio
  - `provider` (object): For TTS input
- `model` (string): "sync-2" or "lipsync-2"
- `options` (object, optional):
  - `sync_mode` (string): "loop" or other sync modes

**Response:**
```json
{
  "id": "b46f7373-7dab-4bd1-b6eb-0e09ca26ffc9",
  "status": "PENDING",
  "created_at": "2025-10-08T18:33:33.878Z",
  "model": "sync-2",
  "input": [...],
  "options": {
    "sync_mode": "loop"
  },
  "output_url": null,
  "output_duration": null
}
```

---

### 3. Get Generation Status
**GET** `/generations/{generation_id}`

Retrieve the status and results of a generation.

**Example:** `GET /generations/b46f7373-7dab-4bd1-b6eb-0e09ca26ffc9`

**Response:**
```json
{
  "id": "b46f7373-7dab-4bd1-b6eb-0e09ca26ffc9",
  "status": "COMPLETED",
  "created_at": "2025-10-08T18:33:33.878Z",
  "model": "sync-2",
  "output_url": "https://storage.googleapis.com/output.mp4",
  "output_duration": 15.5
}
```

**Status values:** `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

---

### 4. Estimate Generation Cost
**POST** `/generations/estimate-cost`

Estimate the cost before creating a generation.

**Request Body:** (Same format as Create Generation)

**Response:**
```json
{
  "estimatedFrameCount": 6692,
  "estimatedGenerationCost": 13.38
}
```

---

### 5. Get Voice Information
**GET** `/voices/{voice_id}`

Get details about a specific ElevenLabs voice.

**Example:** `GET /voices/21m00Tcm4TlvDq8ikWAM`

**Response:**
```json
{
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "name": "Rachel",
  "category": "professional",
  "description": "A warm, expressive voice",
  "preview_url": "https://storage.googleapis.com/preview.mp3",
  "labels": {
    "accent": "American",
    "age": "middle-aged",
    "gender": "female",
    "use_case": "social media"
  },
  "settings": {
    "stability": 0.75,
    "similarity_boost": 0.75,
    "style": 0,
    "use_speaker_boost": true
  }
}
```

---

### 6. Create Instant Voice Clone
**POST** `/voice-cloning/ivc`

Create a voice clone by uploading audio samples.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `name` (string, required): Name for the voice clone
- `files` (files, required): Audio files (mp3, wav, etc.)

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/voice-cloning/ivc" \
  -F "name=My Voice Clone" \
  -F "files=@sample1.mp3" \
  -F "files=@sample2.mp3"
```

**Example using JavaScript:**
```javascript
const formData = new FormData();
formData.append('name', 'My Voice Clone');
formData.append('files', audioFile1);
formData.append('files', audioFile2);

fetch('http://localhost:8000/voice-cloning/ivc', {
  method: 'POST',
  body: formData
});
```

**Response:**
```json
{
  "voice_id": "abc123xyz456",
  "name": "My Voice Clone",
  "description": null
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
