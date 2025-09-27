"""
Real-time Streaming API for Video Dubbing and Lip-Sync
Handles live video streams with WebSocket support for bidirectional communication
"""
import asyncio
import json
import base64
import cv2
import numpy as np
import io
import time
import threading
from typing import Dict, Optional, Callable, Any
from queue import Queue, Empty
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel

from dubbing_pipeline import DubbingPipeline


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingConfig(BaseModel):
    """Configuration for streaming dubbing"""
    target_language: str = "es"
    source_language: Optional[str] = None
    enable_voice_cloning: bool = False
    chunk_duration: float = 1.0  # Shorter for real-time
    whisper_model: str = "tiny"  # Fastest model
    translation_model: str = "facebook/m2m100_418M"
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC"
    fps: int = 30
    resolution: tuple = (640, 480)
    audio_sample_rate: int = 16000


class StreamProcessor:
    """Handles real-time stream processing"""
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.pipeline = None
        self.is_processing = False
        self.frame_queue = Queue(maxsize=30)  # Buffer for frames
        self.audio_queue = Queue(maxsize=30)  # Buffer for audio
        self.output_queue = Queue(maxsize=30)  # Buffer for processed frames
        
        # Threading locks
        self.processing_lock = threading.Lock()
        self.audio_lock = threading.Lock()
        
        # Audio buffer for continuous processing
        self.audio_buffer = []
        self.audio_buffer_duration = 2.0  # seconds
        self.audio_buffer_size = int(config.audio_sample_rate * self.audio_buffer_duration)
        
        # Frame timing
        self.last_frame_time = 0
        self.frame_interval = 1.0 / config.fps
        
        # Statistics
        self.stats = {
            "frames_processed": 0,
            "audio_chunks_processed": 0,
            "processing_time": 0,
            "fps": 0
        }
    
    async def initialize(self):
        """Initialize the processing pipeline"""
        try:
            self.pipeline = DubbingPipeline(
                chunk_duration=self.config.chunk_duration,
                whisper_model=self.config.whisper_model,
                translation_model=self.config.translation_model,
                tts_model=self.config.tts_model,
                device="auto",
                enable_voice_cloning=self.config.enable_voice_cloning
            )
            logger.info("Streaming pipeline initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize streaming pipeline: {e}")
            return False
    
    def add_frame(self, frame_data: bytes):
        """Add frame to processing queue"""
        try:
            # Decode frame from bytes
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Resize frame if needed
                if frame.shape[:2] != self.config.resolution[::-1]:
                    frame = cv2.resize(frame, self.config.resolution)
                
                # Add to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait((frame, time.time()))
                except:
                    # Queue full, remove oldest frame
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait((frame, time.time()))
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error adding frame: {e}")
    
    def add_audio(self, audio_data: bytes):
        """Add audio data to processing queue"""
        try:
            with self.audio_lock:
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
                self.audio_buffer.extend(audio_array)
                
                # Process when buffer is full
                if len(self.audio_buffer) >= self.audio_buffer_size:
                    audio_chunk = np.array(self.audio_buffer[:self.audio_buffer_size])
                    self.audio_buffer = self.audio_buffer[self.audio_buffer_size:]
                    
                    try:
                        self.audio_queue.put_nowait(audio_chunk)
                    except:
                        # Queue full, remove oldest
                        try:
                            self.audio_queue.get_nowait()
                            self.audio_queue.put_nowait(audio_chunk)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error adding audio: {e}")
    
    async def process_stream(self):
        """Main processing loop for real-time streaming"""
        if self.is_processing:
            return
        
        self.is_processing = True
        logger.info("Starting stream processing...")
        
        try:
            while self.is_processing:
                # Process frames and audio in parallel
                await asyncio.gather(
                    self._process_frames(),
                    self._process_audio(),
                    return_exceptions=True
                )
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Stream processing error: {e}")
        finally:
            self.is_processing = False
            logger.info("Stream processing stopped")
    
    async def _process_frames(self):
        """Process video frames"""
        try:
            frame, timestamp = self.frame_queue.get_nowait()
            
            # Check if we need to process this frame based on timing
            current_time = time.time()
            if current_time - self.last_frame_time >= self.frame_interval:
                self.last_frame_time = current_time
                
                # For now, just pass frame through (lip-sync will be applied later)
                processed_frame = frame
                
                # Add to output queue
                try:
                    self.output_queue.put_nowait((processed_frame, timestamp))
                    self.stats["frames_processed"] += 1
                except:
                    # Output queue full, remove oldest
                    try:
                        self.output_queue.get_nowait()
                        self.output_queue.put_nowait((processed_frame, timestamp))
                    except:
                        pass
                        
        except Empty:
            pass
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    async def _process_audio(self):
        """Process audio chunks"""
        try:
            audio_chunk = self.audio_queue.get_nowait()
            
            # Process audio through pipeline
            # This is a simplified version - in practice you'd need more sophisticated audio processing
            processed_audio = await self._process_audio_chunk(audio_chunk)
            
            # Store processed audio for lip-sync
            # Implementation would depend on your specific needs
            
            self.stats["audio_chunks_processed"] += 1
            
        except Empty:
            pass
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
    
    async def _process_audio_chunk(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Process a single audio chunk through the pipeline"""
        try:
            # This is a placeholder - you'd implement the actual processing here
            # For real-time processing, you might want to use streaming versions of the models
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            # Return processed audio (placeholder)
            return audio_chunk
            
        except Exception as e:
            logger.error(f"Audio chunk processing failed: {e}")
            return audio_chunk
    
    def get_processed_frame(self) -> Optional[tuple]:
        """Get the next processed frame"""
        try:
            return self.output_queue.get_nowait()
        except Empty:
            return None
    
    def stop_processing(self):
        """Stop the processing loop"""
        self.is_processing = False
        
        # Clear queues
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                break
        
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        current_time = time.time()
        
        # Calculate FPS
        if self.stats["frames_processed"] > 0:
            self.stats["fps"] = self.stats["frames_processed"] / max(1, current_time - self.last_frame_time)
        
        return self.stats.copy()


class StreamingManager:
    """Manages multiple streaming sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, StreamProcessor] = {}
        self.active_sessions = set()
    
    def create_session(self, session_id: str, config: StreamingConfig) -> StreamProcessor:
        """Create a new streaming session"""
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        processor = StreamProcessor(config)
        self.sessions[session_id] = processor
        self.active_sessions.add(session_id)
        
        return processor
    
    def get_session(self, session_id: str) -> Optional[StreamProcessor]:
        """Get an existing session"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self.sessions:
            self.sessions[session_id].stop_processing()
            del self.sessions[session_id]
            self.active_sessions.discard(session_id)


# Global streaming manager
streaming_manager = StreamingManager()

# FastAPI app
app = FastAPI(
    title="Real-time Video Dubbing Streaming API",
    description="WebSocket-based streaming API for real-time video dubbing with lip-sync",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint with streaming demo"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real-time Video Dubbing Stream</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .video-container { display: flex; gap: 20px; margin: 20px 0; }
            .video-box { flex: 1; border: 2px solid #ccc; padding: 10px; }
            video { width: 100%; height: auto; }
            .controls { margin: 20px 0; }
            button { padding: 10px 20px; margin: 5px; font-size: 16px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .status.connected { background-color: #d4edda; color: #155724; }
            .status.disconnected { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Real-time Video Dubbing Stream</h1>
            
            <div class="controls">
                <button id="startBtn">Start Stream</button>
                <button id="stopBtn" disabled>Stop Stream</button>
                <button id="captureBtn" disabled>Start Capture</button>
                
                <div>
                    <label>Target Language: </label>
                    <select id="targetLang">
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                        <option value="de">German</option>
                        <option value="ja">Japanese</option>
                        <option value="zh">Chinese</option>
                    </select>
                </div>
            </div>
            
            <div id="status" class="status disconnected">Disconnected</div>
            
            <div class="video-container">
                <div class="video-box">
                    <h3>Input Stream</h3>
                    <video id="inputVideo" autoplay muted></video>
                </div>
                <div class="video-box">
                    <h3>Processed Stream</h3>
                    <video id="outputVideo" autoplay></video>
                </div>
            </div>
            
            <div id="stats"></div>
        </div>
        
        <script>
            let websocket = null;
            let mediaStream = null;
            let sessionId = null;
            
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const captureBtn = document.getElementById('captureBtn');
            const statusDiv = document.getElementById('status');
            const statsDiv = document.getElementById('stats');
            const inputVideo = document.getElementById('inputVideo');
            const outputVideo = document.getElementById('outputVideo');
            
            startBtn.onclick = startStream;
            stopBtn.onclick = stopStream;
            captureBtn.onclick = startCapture;
            
            async function startStream() {
                try {
                    sessionId = 'session_' + Date.now();
                    const targetLang = document.getElementById('targetLang').value;
                    
                    websocket = new WebSocket(`ws://localhost:8000/ws/stream/${sessionId}`);
                    
                    websocket.onopen = function(event) {
                        statusDiv.textContent = 'Connected';
                        statusDiv.className = 'status connected';
                        startBtn.disabled = true;
                        stopBtn.disabled = false;
                        captureBtn.disabled = false;
                        
                        // Send configuration
                        websocket.send(JSON.stringify({
                            type: 'config',
                            target_language: targetLang,
                            source_language: null,
                            enable_voice_cloning: false,
                            chunk_duration: 1.0,
                            whisper_model: 'tiny'
                        }));
                    };
                    
                    websocket.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'processed_frame') {
                            // Display processed frame
                            const img = new Image();
                            img.onload = function() {
                                const canvas = document.createElement('canvas');
                                const ctx = canvas.getContext('2d');
                                canvas.width = img.width;
                                canvas.height = img.height;
                                ctx.drawImage(img, 0, 0);
                                
                                const stream = canvas.captureStream(30);
                                outputVideo.srcObject = stream;
                            };
                            img.src = 'data:image/jpeg;base64,' + data.frame_data;
                        } else if (data.type === 'stats') {
                            statsDiv.innerHTML = `
                                <h3>Statistics</h3>
                                <p>Frames Processed: ${data.frames_processed}</p>
                                <p>Audio Chunks: ${data.audio_chunks_processed}</p>
                                <p>FPS: ${data.fps.toFixed(2)}</p>
                                <p>Processing Time: ${data.processing_time.toFixed(2)}ms</p>
                            `;
                        }
                    };
                    
                    websocket.onclose = function(event) {
                        statusDiv.textContent = 'Disconnected';
                        statusDiv.className = 'status disconnected';
                        startBtn.disabled = false;
                        stopBtn.disabled = true;
                        captureBtn.disabled = true;
                    };
                    
                    websocket.onerror = function(error) {
                        console.error('WebSocket error:', error);
                        statusDiv.textContent = 'Connection Error';
                        statusDiv.className = 'status disconnected';
                    };
                    
                } catch (error) {
                    console.error('Error starting stream:', error);
                    alert('Failed to start stream: ' + error.message);
                }
            }
            
            function stopStream() {
                if (websocket) {
                    websocket.close();
                }
                if (mediaStream) {
                    mediaStream.getTracks().forEach(track => track.stop());
                    mediaStream = null;
                }
                inputVideo.srcObject = null;
                outputVideo.srcObject = null;
            }
            
            async function startCapture() {
                try {
                    mediaStream = await navigator.mediaDevices.getUserMedia({
                        video: { width: 640, height: 480, frameRate: 30 },
                        audio: true
                    });
                    
                    inputVideo.srcObject = mediaStream;
                    
                    // Send frames to WebSocket
                    const videoTrack = mediaStream.getVideoTracks()[0];
                    const imageCapture = new ImageCapture(videoTrack);
                    
                    setInterval(async () => {
                        if (websocket && websocket.readyState === WebSocket.OPEN) {
                            try {
                                const frame = await imageCapture.grabFrame();
                                const canvas = document.createElement('canvas');
                                const ctx = canvas.getContext('2d');
                                canvas.width = frame.width;
                                canvas.height = frame.height;
                                ctx.drawImage(frame, 0, 0);
                                
                                canvas.toBlob((blob) => {
                                    const reader = new FileReader();
                                    reader.onload = () => {
                                        const base64 = reader.result.split(',')[1];
                                        websocket.send(JSON.stringify({
                                            type: 'frame',
                                            frame_data: base64,
                                            timestamp: Date.now()
                                        }));
                                    };
                                    reader.readAsDataURL(blob);
                                }, 'image/jpeg', 0.8);
                            } catch (error) {
                                console.error('Error capturing frame:', error);
                            }
                        }
                    }, 100); // 10 FPS for demo
                    
                    // Send audio data
                    const audioContext = new AudioContext();
                    const source = audioContext.createMediaStreamSource(mediaStream);
                    const processor = audioContext.createScriptProcessor(4096, 1, 1);
                    
                    processor.onaudioprocess = (event) => {
                        if (websocket && websocket.readyState === WebSocket.OPEN) {
                            const audioData = event.inputBuffer.getChannelData(0);
                            const bytes = new Float32Array(audioData).buffer;
                            const base64 = btoa(String.fromCharCode(...new Uint8Array(bytes)));
                            
                            websocket.send(JSON.stringify({
                                type: 'audio',
                                audio_data: base64,
                                timestamp: Date.now()
                            }));
                        }
                    };
                    
                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    
                } catch (error) {
                    console.error('Error starting capture:', error);
                    alert('Failed to start capture: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time streaming"""
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")
    
    processor = None
    processing_task = None
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "config":
                # Initialize streaming session
                config = StreamingConfig(**data)
                processor = streaming_manager.create_session(session_id, config)
                
                # Initialize pipeline
                success = await processor.initialize()
                if not success:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to initialize processing pipeline"
                    })
                    break
                
                # Start processing loop
                processing_task = asyncio.create_task(processor.process_stream())
                
                await websocket.send_json({
                    "type": "ready",
                    "message": "Streaming session initialized"
                })
            
            elif data["type"] == "frame":
                # Process video frame
                if processor:
                    frame_data = base64.b64decode(data["frame_data"])
                    processor.add_frame(frame_data)
            
            elif data["type"] == "audio":
                # Process audio data
                if processor:
                    audio_data = base64.b64decode(data["audio_data"])
                    processor.add_audio(audio_data)
            
            elif data["type"] == "get_stats":
                # Send processing statistics
                if processor:
                    stats = processor.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        **stats
                    })
            
            # Send processed frames back to client
            if processor:
                processed_frame = processor.get_processed_frame()
                if processed_frame:
                    frame, timestamp = processed_frame
                    
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_data = base64.b64encode(buffer).decode('utf-8')
                    
                    await websocket.send_json({
                        "type": "processed_frame",
                        "frame_data": frame_data,
                        "timestamp": timestamp
                    })
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        # Cleanup
        if processing_task:
            processing_task.cancel()
        
        if processor:
            processor.stop_processing()
        
        streaming_manager.remove_session(session_id)
        logger.info(f"Cleaned up session: {session_id}")


@app.get("/stream/{session_id}/stats")
async def get_stream_stats(session_id: str):
    """Get statistics for a streaming session"""
    processor = streaming_manager.get_session(session_id)
    if not processor:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return processor.get_stats()


@app.post("/stream/{session_id}/stop")
async def stop_stream(session_id: str):
    """Stop a streaming session"""
    processor = streaming_manager.get_session(session_id)
    if not processor:
        raise HTTPException(status_code=404, detail="Session not found")
    
    processor.stop_processing()
    streaming_manager.remove_session(session_id)
    
    return {"message": "Stream stopped successfully"}


@app.get("/sessions")
async def list_sessions():
    """List active streaming sessions"""
    return {
        "active_sessions": list(streaming_manager.active_sessions),
        "session_count": len(streaming_manager.active_sessions)
    }


if __name__ == "__main__":
    # Create necessary directories
    import os
    os.makedirs("temp", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    # Run the streaming server
    uvicorn.run(
        "streaming_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
