"""
Simplified Streaming Demo Server
A lightweight version for testing WebSocket functionality without heavy ML dependencies
"""
import asyncio
import json
import base64
import time
import logging
from typing import Dict, Optional
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Simple Streaming Demo",
    description="Lightweight streaming demo for testing WebSocket functionality",
    version="1.0.0"
)

# Simple session storage
active_sessions = {}

class SimpleStreamProcessor:
    """Simplified stream processor for demo purposes"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_processing = False
        self.frame_count = 0
        self.start_time = time.time()
        
    def process_frame(self, frame_data: str) -> str:
        """Process frame - in this demo, just add a timestamp overlay"""
        try:
            # Decode base64 image
            frame_bytes = base64.b64decode(frame_data)
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Add timestamp overlay
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Frame: {self.frame_count}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Session: {self.session_id[:8]}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Re-encode as JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                processed_data = base64.b64encode(buffer).decode('utf-8')
                
                self.frame_count += 1
                return processed_data
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
        
        return frame_data  # Return original if processing fails
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        elapsed_time = time.time() - self.start_time
        fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        
        return {
            "session_id": self.session_id,
            "frames_processed": self.frame_count,
            "processing_time": elapsed_time,
            "fps": fps,
            "status": "active"
        }

@app.get("/")
async def root():
    """Root endpoint with streaming demo"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Streaming Demo</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background-color: #f0f0f0;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .video-container { 
                display: flex; 
                gap: 20px; 
                margin: 20px 0; 
                flex-wrap: wrap;
            }
            .video-box { 
                flex: 1; 
                min-width: 300px;
                border: 2px solid #ddd; 
                padding: 15px; 
                border-radius: 8px;
                background: #fafafa;
            }
            video { 
                width: 100%; 
                height: auto; 
                border-radius: 5px;
                background: #000;
            }
            .controls { 
                margin: 20px 0; 
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            button { 
                padding: 12px 24px; 
                margin: 8px; 
                font-size: 16px; 
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-primary { background-color: #007bff; color: white; }
            .btn-primary:hover { background-color: #0056b3; }
            .btn-danger { background-color: #dc3545; color: white; }
            .btn-danger:hover { background-color: #c82333; }
            .btn-success { background-color: #28a745; color: white; }
            .btn-success:hover { background-color: #218838; }
            button:disabled { 
                background-color: #6c757d; 
                cursor: not-allowed; 
            }
            .status { 
                padding: 15px; 
                margin: 15px 0; 
                border-radius: 8px; 
                font-weight: bold;
                text-align: center;
            }
            .status.connected { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.disconnected { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .status.connecting { background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
            .stats { 
                margin: 20px 0; 
                padding: 15px;
                background: #e9ecef;
                border-radius: 8px;
                font-family: monospace;
            }
            .stats h3 { margin-top: 0; color: #495057; }
            .language-selector {
                margin: 10px 0;
            }
            .language-selector select {
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #ddd;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Simple Streaming Demo</h1>
            <p>This is a lightweight demo of the streaming API. It processes video frames in real-time and adds timestamp overlays.</p>
            
            <div class="controls">
                <button id="startBtn" class="btn-primary">🚀 Start Stream</button>
                <button id="stopBtn" class="btn-danger" disabled>⏹️ Stop Stream</button>
                <button id="captureBtn" class="btn-success" disabled>📹 Start Capture</button>
                
                <div class="language-selector">
                    <label for="targetLang"><strong>Target Language:</strong> </label>
                    <select id="targetLang">
                        <option value="es">🇪🇸 Spanish</option>
                        <option value="fr">🇫🇷 French</option>
                        <option value="de">🇩🇪 German</option>
                        <option value="ja">🇯🇵 Japanese</option>
                        <option value="zh">🇨🇳 Chinese</option>
                        <option value="it">🇮🇹 Italian</option>
                        <option value="pt">🇵🇹 Portuguese</option>
                        <option value="ru">🇷🇺 Russian</option>
                    </select>
                </div>
            </div>
            
            <div id="status" class="status disconnected">❌ Disconnected</div>
            
            <div class="video-container">
                <div class="video-box">
                    <h3>📷 Input Stream</h3>
                    <video id="inputVideo" autoplay muted playsinline></video>
                    <p><small>Your camera feed</small></p>
                </div>
                <div class="video-box">
                    <h3>🎭 Processed Stream</h3>
                    <video id="outputVideo" autoplay playsinline></video>
                    <p><small>Real-time processed video</small></p>
                </div>
            </div>
            
            <div id="stats" class="stats">
                <h3>📊 Statistics</h3>
                <div id="statsContent">No data yet...</div>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h3>🔧 How it works:</h3>
                <ol>
                    <li><strong>Start Stream:</strong> Establishes WebSocket connection to the server</li>
                    <li><strong>Start Capture:</strong> Begins capturing from your camera</li>
                    <li><strong>Real-time Processing:</strong> Server processes each frame and adds overlays</li>
                    <li><strong>Live Output:</strong> Processed frames are sent back and displayed</li>
                </ol>
                <p><strong>Note:</strong> This is a simplified demo. The full system includes AI-powered transcription, translation, TTS, and lip-sync.</p>
            </div>
        </div>
        
        <script>
            let websocket = null;
            let mediaStream = null;
            let sessionId = null;
            let statsInterval = null;
            
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const captureBtn = document.getElementById('captureBtn');
            const statusDiv = document.getElementById('status');
            const statsDiv = document.getElementById('statsContent');
            const inputVideo = document.getElementById('inputVideo');
            const outputVideo = document.getElementById('outputVideo');
            
            startBtn.onclick = startStream;
            stopBtn.onclick = stopStream;
            captureBtn.onclick = startCapture;
            
            async function startStream() {
                try {
                    sessionId = 'session_' + Date.now();
                    const targetLang = document.getElementById('targetLang').value;
                    
                    updateStatus('🔄 Connecting...', 'connecting');
                    
                    websocket = new WebSocket(`ws://localhost:8000/ws/stream/${sessionId}`);
                    
                    websocket.onopen = function(event) {
                        updateStatus('✅ Connected - Ready for streaming', 'connected');
                        startBtn.disabled = true;
                        stopBtn.disabled = false;
                        captureBtn.disabled = false;
                        
                        // Send configuration
                        websocket.send(JSON.stringify({
                            type: 'config',
                            target_language: targetLang,
                            source_language: 'en',
                            enable_voice_cloning: false,
                            chunk_duration: 1.0,
                            whisper_model: 'tiny'
                        }));
                        
                        // Start requesting stats periodically
                        statsInterval = setInterval(requestStats, 2000);
                    };
                    
                    websocket.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'ready') {
                            updateStatus('🎯 Ready for streaming', 'connected');
                        } else if (data.type === 'processed_frame') {
                            // Display processed frame
                            displayProcessedFrame(data.frame_data);
                        } else if (data.type === 'stats') {
                            displayStats(data);
                        } else if (data.type === 'error') {
                            updateStatus(`❌ Error: ${data.message}`, 'disconnected');
                        }
                    };
                    
                    websocket.onclose = function(event) {
                        updateStatus('🔌 Connection closed', 'disconnected');
                        resetButtons();
                        if (statsInterval) {
                            clearInterval(statsInterval);
                            statsInterval = null;
                        }
                    };
                    
                    websocket.onerror = function(error) {
                        console.error('WebSocket error:', error);
                        updateStatus('💥 Connection error', 'disconnected');
                        resetButtons();
                    };
                    
                } catch (error) {
                    console.error('Error starting stream:', error);
                    updateStatus(`❌ Failed to start: ${error.message}`, 'disconnected');
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
                updateStatus('⏹️ Stream stopped', 'disconnected');
                resetButtons();
                
                if (statsInterval) {
                    clearInterval(statsInterval);
                    statsInterval = null;
                }
            }
            
            async function startCapture() {
                try {
                    updateStatus('📹 Starting camera...', 'connecting');
                    
                    mediaStream = await navigator.mediaDevices.getUserMedia({
                        video: { 
                            width: 640, 
                            height: 480, 
                            frameRate: 30 
                        },
                        audio: false // Disable audio for this demo
                    });
                    
                    inputVideo.srcObject = mediaStream;
                    
                    // Send frames to WebSocket
                    const videoTrack = mediaStream.getVideoTracks()[0];
                    const imageCapture = new ImageCapture(videoTrack);
                    
                    const frameInterval = setInterval(async () => {
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
                        } else {
                            clearInterval(frameInterval);
                        }
                    }, 100); // ~10 FPS for demo
                    
                    updateStatus('🎥 Camera active - Streaming frames', 'connected');
                    
                } catch (error) {
                    console.error('Error starting capture:', error);
                    updateStatus(`❌ Camera error: ${error.message}`, 'disconnected');
                }
            }
            
            function displayProcessedFrame(frameData) {
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
                img.src = `data:image/jpeg;base64,${frameData}`;
            }
            
            function requestStats() {
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({ type: 'get_stats' }));
                }
            }
            
            function displayStats(data) {
                statsDiv.innerHTML = `
                    <div><strong>Session ID:</strong> ${data.session_id || 'N/A'}</div>
                    <div><strong>Frames Processed:</strong> ${data.frames_processed || 0}</div>
                    <div><strong>Processing Time:</strong> ${(data.processing_time || 0).toFixed(2)}s</div>
                    <div><strong>FPS:</strong> ${(data.fps || 0).toFixed(2)}</div>
                    <div><strong>Status:</strong> ${data.status || 'Unknown'}</div>
                `;
            }
            
            function updateStatus(message, type) {
                statusDiv.textContent = message;
                statusDiv.className = `status ${type}`;
            }
            
            function resetButtons() {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                captureBtn.disabled = true;
            }
            
            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {
                if (websocket) {
                    websocket.close();
                }
                if (mediaStream) {
                    mediaStream.getTracks().forEach(track => track.stop());
                }
            });
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
    
    processor = SimpleStreamProcessor(session_id)
    active_sessions[session_id] = processor
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "config":
                # Initialize streaming session
                await websocket.send_json({
                    "type": "ready",
                    "message": "Streaming session initialized successfully"
                })
                logger.info(f"Session {session_id} configured for language: {data.get('target_language', 'unknown')}")
            
            elif data["type"] == "frame":
                # Process video frame
                frame_data = data["frame_data"]
                processed_frame = processor.process_frame(frame_data)
                
                # Send processed frame back
                await websocket.send_json({
                    "type": "processed_frame",
                    "frame_data": processed_frame,
                    "timestamp": time.time()
                })
            
            elif data["type"] == "get_stats":
                # Send processing statistics
                stats = processor.get_stats()
                await websocket.send_json({
                    "type": "stats",
                    **stats
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
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"Cleaned up session: {session_id}")

@app.get("/sessions")
async def list_sessions():
    """List active streaming sessions"""
    return {
        "active_sessions": list(active_sessions.keys()),
        "session_count": len(active_sessions),
        "sessions": {sid: proc.get_stats() for sid, proc in active_sessions.items()}
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "server_time": time.time()
    }

if __name__ == "__main__":
    print("🚀 Starting Simple Streaming Demo Server...")
    print("📡 Server will be available at: http://localhost:8000")
    print("🔌 WebSocket endpoint: ws://localhost:8000/ws/stream/{session_id}")
    print("📊 Health check: http://localhost:8000/health")
    print("📋 Active sessions: http://localhost:8000/sessions")
    print("\n💡 Open your browser and go to http://localhost:8000 to test the streaming demo!")
    
    # Create necessary directories
    import os
    os.makedirs("temp", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "simple_streaming_demo:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
