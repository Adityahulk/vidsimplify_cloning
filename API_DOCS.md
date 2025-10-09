# API Documentation for UI Developers

**Base URL:** `http://localhost:8000`

## Endpoints Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/upload/video` | Upload video to Google Cloud Storage |
| POST | `/generations` | Create lip-sync video |
| GET | `/generations/{id}` | Check generation status |
| POST | `/generations/estimate-cost` | Estimate cost before generation |
| GET | `/voices/{voice_id}` | Get voice details |
| POST | `/voice-cloning/ivc` | Upload audio to clone voice |

---

## 1. Upload Video to Cloud Storage

**POST** `/upload/video`

Upload a video file to Google Cloud Storage and get a public URL.

### Request

**Content-Type:** `multipart/form-data`

**Form Field:**
- `file` (file, required) - Video file to upload

**Supported formats:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('file', videoFile);

const response = await fetch('http://localhost:8000/upload/video', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log('Video URL:', data.url);
```

### Response

```json
{
  "url": "https://storage.googleapis.com/vidsimplify/20251009_143052_abc12345_video.mp4",
  "filename": "20251009_143052_abc12345_video.mp4",
  "size_bytes": 5242880,
  "uploaded_at": "2025-10-09T14:30:52.123456"
}
```

**Response Fields:**
- `url` (string) - Public URL to access the video
- `filename` (string) - Unique filename in cloud storage
- `size_bytes` (number) - File size in bytes
- `uploaded_at` (string) - ISO timestamp of upload

---

## 2. Create Lip Sync Generation

**POST** `/generations`

Combines a video with audio or TTS to create lip-synced output.

### Request

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

### Request with TTS

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
          "script": "Text to be spoken"
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

### Response

```json
{
  "id": "b46f7373-7dab-4bd1-b6eb-0e09ca26ffc9",
  "status": "PENDING",
  "created_at": "2025-10-08T18:33:33.878Z",
  "model": "sync-2",
  "output_url": null
}
```

---

## 3. Get Generation Status

**GET** `/generations/{generation_id}`

Check if generation is complete and get output URL.

### Response

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

**Status Values:**
- `PENDING` - Job queued
- `PROCESSING` - Currently generating
- `COMPLETED` - Ready, check `output_url`
- `FAILED` - Error occurred

---

## 4. Estimate Generation Cost

**POST** `/generations/estimate-cost`

Calculate cost before creating generation. Uses same request format as `/generations`.

### Response

```json
{
  "estimatedFrameCount": 6692,
  "estimatedGenerationCost": 13.38
}
```

---

## 5. Get Voice Information

**GET** `/voices/{voice_id}`

Get information about an ElevenLabs voice.

### Response

```json
{
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "name": "Rachel",
  "category": "professional",
  "description": "A warm, expressive voice",
  "preview_url": "https://storage.googleapis.com/preview.mp3",
  "labels": {
    "accent": "American",
    "gender": "female",
    "age": "middle-aged"
  },
  "settings": {
    "stability": 0.75,
    "similarity_boost": 0.75,
    "use_speaker_boost": true
  }
}
```

---

## 6. Create Voice Clone

**POST** `/voice-cloning/ivc`

Upload audio samples to clone a voice.

### Request

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `name` (string) - Voice name
- `files` (files) - Audio files

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('name', 'My Voice Clone');
formData.append('files', audioFile1);
formData.append('files', audioFile2);

const response = await fetch('http://localhost:8000/voice-cloning/ivc', {
  method: 'POST',
  body: formData
});

const data = await response.json();
```

### Response

```json
{
  "voice_id": "abc123xyz456",
  "name": "My Voice Clone",
  "description": null
}
```

---

## Common Use Cases

### Case 1: Upload Video + Audio Lip Sync

```javascript
// 1. Upload video file
const videoFormData = new FormData();
videoFormData.append('file', videoFile);

const uploadResponse = await fetch('/upload/video', {
  method: 'POST',
  body: videoFormData
});

const { url: videoUrl } = await uploadResponse.json();

// 2. Upload audio file (or use existing audio URL)
const audioUrl = "https://example.com/audio.mp3";

// 3. Estimate cost (optional)
const costEstimate = await fetch('/generations/estimate-cost', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    input: [
      { type: "video", url: videoUrl },
      { type: "audio", url: audioUrl }
    ],
    model: "sync-2",
    options: { sync_mode: "loop" }
  })
});

// 4. Create generation
const generation = await fetch('/generations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    input: [
      { type: "video", url: videoUrl },
      { type: "audio", url: audioUrl }
    ],
    model: "sync-2",
    options: { sync_mode: "loop" }
  })
});

const { id } = await generation.json();

// 5. Poll for completion
const checkStatus = async () => {
  const status = await fetch(`/generations/${id}`);
  const data = await status.json();
  
  if (data.status === 'COMPLETED') {
    console.log('Video ready:', data.output_url);
  } else if (data.status === 'FAILED') {
    console.error('Generation failed');
  } else {
    // Still processing, check again in 5 seconds
    setTimeout(checkStatus, 5000);
  }
};

checkStatus();
```

### Case 2: Video + TTS Lip Sync

```javascript
// 1. Get voice information
const voiceInfo = await fetch('/voices/21m00Tcm4TlvDq8ikWAM');

// 2. Create generation with TTS
const generation = await fetch('/generations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    input: [
      { type: "video", url: videoUrl },
      { 
        type: "text",
        provider: {
          ElevenLabs: {
            name: "elevenlabs",
            voiceId: "21m00Tcm4TlvDq8ikWAM",
            script: "Hello, this is my script"
          }
        }
      }
    ],
    model: "sync-2",
    options: { sync_mode: "loop" }
  })
});
```

### Case 3: Voice Cloning

```javascript
// 1. Upload audio to create voice clone
const formData = new FormData();
formData.append('name', 'Custom Voice');
formData.append('files', audioFile1);
formData.append('files', audioFile2);

const voiceClone = await fetch('/voice-cloning/ivc', {
  method: 'POST',
  body: formData
});

const { voice_id } = await voiceClone.json();

// 2. Use cloned voice in generation
const generation = await fetch('/generations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    input: [
      { type: "video", url: videoUrl },
      { 
        type: "text",
        provider: {
          ElevenLabs: {
            name: "elevenlabs",
            voiceId: voice_id,  // Use the cloned voice
            script: "Script with my cloned voice"
          }
        }
      }
    ],
    model: "sync-2"
  })
});
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `400` - Bad request (missing required fields)
- `401` - Unauthorized (invalid API key)
- `404` - Not found
- `500` - Server error

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Example Error Handling

```javascript
try {
  const response = await fetch('/generations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  const data = await response.json();
  // Handle success
  
} catch (error) {
  console.error('API Error:', error.message);
  // Show error to user
}
```

---

## Interactive API Documentation

For testing and exploring the API interactively:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

