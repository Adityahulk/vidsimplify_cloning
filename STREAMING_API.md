# Real-Time Streaming Video Dubbing API

This document describes the streaming API for real-time video dubbing with lip-sync. The API supports WebSocket-based bidirectional communication for live video and audio streaming.

## 🚀 Features

- **Real-time Processing**: Sub-second latency for live streaming
- **WebSocket Communication**: Bidirectional streaming with low overhead
- **Multi-language Support**: 100+ languages via M2M100/NLLB
- **Voice Cloning**: Clone original speaker's voice in target language
- **Live Lip-Sync**: Real-time lip synchronization using Wav2Lip
- **Web Interface**: Built-in web demo with camera and microphone support
- **Python Client**: Full-featured Python client for integration
- **JavaScript Client**: Browser-based client for web applications

## 📡 API Endpoints

### WebSocket Streaming
- **URL**: `ws://localhost:8000/ws/stream/{session_id}`
- **Protocol**: WebSocket
- **Purpose**: Real-time bidirectional streaming

### HTTP Endpoints
- **GET** `/` - Web demo interface
- **GET** `/stream/{session_id}/stats` - Get session statistics
- **POST** `/stream/{session_id}/stop` - Stop streaming session
- **GET** `/sessions` - List active sessions

## 🔧 WebSocket Protocol

### Connection Flow

1. **Connect**: Establish WebSocket connection with unique session ID
2. **Configure**: Send configuration message to initialize processing
3. **Stream**: Send video frames and audio data continuously
4. **Receive**: Receive processed frames and transcriptions
5. **Monitor**: Request and receive processing statistics

### Message Types

#### Client → Server

**Configuration Message**
```json
{
  "type": "config",
  "target_language": "es",
  "source_language": "en",
  "enable_voice_cloning": false,
  "chunk_duration": 1.0,
  "whisper_model": "tiny",
  "translation_model": "facebook/m2m100_418M",
  "tts_model": "tts_models/en/ljspeech/tacotron2-DDC"
}
```

**Video Frame Message**
```json
{
  "type": "frame",
  "frame_data": "base64_encoded_jpeg",
  "timestamp": 1640995200000
}
```

**Audio Data Message**
```json
{
  "type": "audio",
  "audio_data": "base64_encoded_float32_array",
  "timestamp": 1640995200000
}
```

**Statistics Request**
```json
{
  "type": "get_stats"
}
```

#### Server → Client

**Ready Message**
```json
{
  "type": "ready",
  "message": "Streaming session initialized"
}
```

**Processed Frame Message**
```json
{
  "type": "processed_frame",
  "frame_data": "base64_encoded_jpeg",
  "timestamp": 1640995200000
}
```

**Transcription Message**
```json
{
  "type": "transcription",
  "original": "Hello world",
  "translated": "Hola mundo",
  "timestamp": 1640995200000
}
```

**Statistics Message**
```json
{
  "type": "stats",
  "frames_processed": 150,
  "audio_chunks_processed": 25,
  "fps": 29.8,
  "processing_time": 45.2
}
```

**Error Message**
```json
{
  "type": "error",
  "message": "Processing failed: CUDA out of memory"
}
```

## 🐍 Python Client Usage

### Basic Usage

```python
import asyncio
from streaming_client import StreamingDubbingClient

async def main():
    # Create client
    client = StreamingDubbingClient("ws://localhost:8000")
    
    # Connect to server
    await client.connect()
    
    # Configure streaming
    await client.configure({
        "target_language": "es",
        "source_language": "en",
        "enable_voice_cloning": False,
        "chunk_duration": 1.0,
        "whisper_model": "tiny"
    })
    
    # Setup callbacks
    def on_frame_received(frame, timestamp):
        print(f"Received frame at {timestamp}")
    
    client.on_frame_received = on_frame_received
    
    # Send frames (implement your own frame capture)
    # await client.send_frame(frame_data)
    
    # Disconnect
    await client.disconnect()

asyncio.run(main())
```

### With Webcam Streaming

```python
from streaming_client import StreamingDubbingClient, WebcamStreamer

async def main():
    client = StreamingDubbingClient()
    webcam = WebcamStreamer()
    
    await client.connect()
    await client.configure({"target_language": "es"})
    
    webcam.start_camera()
    
    while client.is_connected:
        frame = webcam.get_frame()
        if frame is not None:
            await client.send_frame(frame)
        await asyncio.sleep(0.1)
    
    webcam.stop_camera()
    await client.disconnect()
```

### Command Line Usage

```bash
# Basic streaming
python streaming_client.py --target-language es

# With audio
python streaming_client.py --target-language fr --enable-audio

# Custom server
python streaming_client.py --server ws://your-server:8000 --target-language de
```

## 🌐 JavaScript Client Usage

### Basic Usage

```javascript
const client = new StreamingDubbingClient('ws://localhost:8000');

// Connect and configure
await client.connect();
await client.configure({
    target_language: 'es',
    enable_voice_cloning: false
});

// Setup callbacks
client.onFrameReceived = (frameData, timestamp) => {
    console.log('Received processed frame');
    // Display frame in your UI
};

client.onTranscriptionReceived = (data) => {
    console.log(`Transcription: ${data.original} -> ${data.translated}`);
};

// Start streaming
const webcam = new WebcamStreamer();
await webcam.startCamera();

setInterval(async () => {
    const frameData = await webcam.getFrame();
    if (frameData) {
        await client.sendFrame(frameData);
    }
}, 100);
```

### Web Demo

Access the built-in web demo at `http://localhost:8000` to test the streaming functionality directly in your browser.

## ⚙️ Configuration Options

### Streaming Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_language` | string | "es" | Target language code |
| `source_language` | string | null | Source language (auto-detect if null) |
| `enable_voice_cloning` | boolean | false | Enable voice cloning |
| `chunk_duration` | float | 1.0 | Audio chunk duration in seconds |
| `whisper_model` | string | "tiny" | Whisper model size |
| `translation_model` | string | "facebook/m2m100_418M" | Translation model |
| `tts_model` | string | "tts_models/en/ljspeech/tacotron2-DDC" | TTS model |

### Model Selection Guide

**Whisper Models** (Speed vs Quality):
- `tiny`: Fastest, lowest accuracy (~39 MB)
- `base`: Balanced speed/accuracy (~74 MB)
- `small`: Better accuracy (~244 MB)
- `medium`: High accuracy (~769 MB)
- `large`: Best accuracy (~1550 MB)

**Translation Models**:
- `facebook/m2m100_418M`: Good balance, 418M parameters
- `facebook/nllb-200-distilled-600M`: Better quality, 600M parameters

**TTS Models**:
- `tts_models/en/ljspeech/tacotron2-DDC`: Standard English
- `tts_models/multilingual/multi-dataset/your_tts`: Multilingual with voice cloning

## 📊 Performance Optimization

### For Real-time Streaming

1. **Use Smaller Models**:
   ```json
   {
     "whisper_model": "tiny",
     "translation_model": "facebook/m2m100_418M",
     "chunk_duration": 1.0
   }
   ```

2. **Optimize Frame Rate**:
   - Lower FPS reduces processing load
   - 15-30 FPS is usually sufficient for lip-sync

3. **Reduce Resolution**:
   - 640x480 is optimal for most use cases
   - Higher resolution increases processing time

4. **Enable GPU Acceleration**:
   ```bash
   # Ensure CUDA is available
   python -c "import torch; print(torch.cuda.is_available())"
   ```

### Latency Optimization

1. **Chunk Duration**: 1-2 seconds for real-time, 3-5 seconds for better quality
2. **Buffer Management**: Keep queues small to reduce latency
3. **Parallel Processing**: Process audio and video simultaneously
4. **Network Optimization**: Use local server for minimal network latency

## 🔧 Server Setup

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup Wav2Lip (required for lip-sync)
git clone https://github.com/Rudrabha/Wav2Lip.git
cd Wav2Lip
pip install -r requirements.txt
wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth -O models/wav2lip_gan.pth
cp inference.py ../
cd ..
```

### Running the Server

```bash
# Start streaming server
python streaming_api.py

# Server will be available at:
# - WebSocket: ws://localhost:8000
# - Web demo: http://localhost:8000
```

### Production Deployment

```bash
# Use Gunicorn with Uvicorn workers
gunicorn streaming_api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use Docker
docker build -t streaming-dubbing .
docker run -p 8000:8000 streaming-dubbing
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Ensure server is running on correct port
   - Check firewall settings
   - Verify WebSocket URL format

2. **High Latency**:
   - Use smaller models (`tiny` Whisper)
   - Reduce chunk duration
   - Enable GPU acceleration
   - Check network connection

3. **Out of Memory**:
   - Use smaller models
   - Reduce video resolution
   - Increase chunk duration
   - Monitor GPU memory usage

4. **Audio Not Working**:
   - Check microphone permissions
   - Verify audio sample rate (16kHz)
   - Ensure PyAudio is installed (Python client)

5. **Poor Lip-Sync Quality**:
   - Use higher quality Whisper model
   - Ensure good audio quality
   - Check face detection in video
   - Verify Wav2Lip installation

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Monitoring

Monitor server statistics:

```bash
# Get session stats
curl http://localhost:8000/stream/{session_id}/stats

# List active sessions
curl http://localhost:8000/sessions
```

## 📈 Performance Benchmarks

### Latency Measurements

| Configuration | Latency | Quality | GPU Memory |
|---------------|---------|---------|------------|
| tiny + 1s chunks | ~0.8s | Good | 2GB |
| base + 2s chunks | ~1.5s | Better | 3GB |
| medium + 2s chunks | ~2.5s | High | 4GB |
| large + 3s chunks | ~4.0s | Best | 6GB |

### Throughput

- **Video**: 15-30 FPS depending on model
- **Audio**: Real-time processing
- **Concurrent Sessions**: 4-8 depending on GPU memory

## 🔐 Security Considerations

1. **Authentication**: Implement session authentication for production
2. **Rate Limiting**: Add rate limiting to prevent abuse
3. **Input Validation**: Validate all incoming data
4. **Resource Limits**: Limit concurrent sessions and processing time
5. **HTTPS/WSS**: Use secure connections in production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Facebook M2M100](https://github.com/pytorch/fairseq) for translation
- [Coqui TTS](https://github.com/coqui-ai/TTS) for text-to-speech
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) for lip-sync
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [WebSockets](https://websockets.readthedocs.io/) for real-time communication
