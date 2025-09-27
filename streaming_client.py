"""
Python client for the real-time streaming video dubbing API
"""
import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import time
from typing import Optional, Callable, Dict, Any
import logging
import argparse


logger = logging.getLogger(__name__)


class StreamingDubbingClient:
    """Client for real-time video dubbing streaming"""
    
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.server_url = server_url
        self.websocket = None
        self.session_id = None
        self.is_connected = False
        self.is_streaming = False
        
        # Callbacks
        self.on_frame_received: Optional[Callable] = None
        self.on_transcription_received: Optional[Callable] = None
        self.on_stats_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'audio_chunks_sent': 0,
            'connection_time': 0,
            'fps': 0
        }
        
        self.start_time = 0
    
    async def connect(self, session_id: Optional[str] = None) -> bool:
        """Connect to the streaming server"""
        try:
            if session_id is None:
                session_id = f"client_{int(time.time() * 1000)}"
            
            self.session_id = session_id
            url = f"{self.server_url}/ws/stream/{session_id}"
            
            logger.info(f"Connecting to {url}")
            self.websocket = await websockets.connect(url)
            self.is_connected = True
            self.start_time = time.time()
            
            # Start message handling
            asyncio.create_task(self._handle_messages())
            
            logger.info(f"Connected to streaming server with session ID: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the streaming server"""
        self.is_connected = False
        self.is_streaming = False
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        logger.info("Disconnected from streaming server")
    
    async def configure(self, config: Dict[str, Any]):
        """Send configuration to the server"""
        if not self.is_connected or not self.websocket:
            raise Exception("Not connected to server")
        
        message = {
            "type": "config",
            **config
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info("Configuration sent to server")
    
    async def send_frame(self, frame: np.ndarray):
        """Send a video frame to the server"""
        if not self.is_connected or not self.websocket:
            return
        
        try:
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            message = {
                "type": "frame",
                "frame_data": frame_data,
                "timestamp": time.time()
            }
            
            await self.websocket.send(json.dumps(message))
            self.stats['frames_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
            if self.on_error:
                self.on_error(f"Frame send error: {e}")
    
    async def send_audio(self, audio_data: np.ndarray):
        """Send audio data to the server"""
        if not self.is_connected or not self.websocket:
            return
        
        try:
            # Convert audio to base64
            audio_bytes = audio_data.astype(np.float32).tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            message = {
                "type": "audio",
                "audio_data": audio_b64,
                "timestamp": time.time()
            }
            
            await self.websocket.send(json.dumps(message))
            self.stats['audio_chunks_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            if self.on_error:
                self.on_error(f"Audio send error: {e}")
    
    async def request_stats(self):
        """Request processing statistics from server"""
        if not self.is_connected or not self.websocket:
            return
        
        message = {"type": "get_stats"}
        await self.websocket.send(json.dumps(message))
    
    async def _handle_messages(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data["type"] == "ready":
                    logger.info("Server ready for streaming")
                    self.is_streaming = True
                
                elif data["type"] == "processed_frame":
                    # Handle processed frame
                    frame_data = base64.b64decode(data["frame_data"])
                    frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    
                    if frame is not None and self.on_frame_received:
                        self.on_frame_received(frame, data.get("timestamp", 0))
                    
                    self.stats['frames_received'] += 1
                
                elif data["type"] == "transcription":
                    # Handle transcription result
                    if self.on_transcription_received:
                        self.on_transcription_received(data)
                
                elif data["type"] == "stats":
                    # Handle statistics
                    if self.on_stats_received:
                        self.on_stats_received(data)
                
                elif data["type"] == "error":
                    # Handle error
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"Server error: {error_msg}")
                    if self.on_error:
                        self.on_error(error_msg)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self.is_connected = False
            self.is_streaming = False
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            if self.on_error:
                self.on_error(f"Message handling error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time > 0 else 1
        
        self.stats['connection_time'] = elapsed_time
        self.stats['fps'] = self.stats['frames_received'] / elapsed_time
        
        return self.stats.copy()


class WebcamStreamer:
    """Webcam streaming utility"""
    
    def __init__(self, camera_index: int = 0, fps: int = 30):
        self.camera_index = camera_index
        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.cap = None
        self.is_streaming = False
        self.last_frame_time = 0
    
    def start_camera(self) -> bool:
        """Start webcam capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.is_streaming = True
            logger.info(f"Camera started (index: {self.camera_index})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get next frame from camera"""
        if not self.is_streaming or not self.cap:
            return None
        
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_interval:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.last_frame_time = current_time
            return frame
        
        return None
    
    def stop_camera(self):
        """Stop webcam capture"""
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Camera stopped")


class MicrophoneStreamer:
    """Microphone audio streaming utility"""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_streaming = False
        
        # Audio capture
        try:
            import pyaudio
            self.pyaudio = pyaudio
            self.audio_available = True
        except ImportError:
            logger.warning("PyAudio not available - audio streaming disabled")
            self.audio_available = False
            self.pyaudio = None
    
    def start_audio(self) -> bool:
        """Start microphone capture"""
        if not self.audio_available:
            return False
        
        try:
            self.audio = self.pyaudio.PyAudio()
            
            self.stream = self.audio.open(
                format=self.pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_streaming = True
            logger.info("Microphone started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start microphone: {e}")
            return False
    
    def get_audio_chunk(self) -> Optional[np.ndarray]:
        """Get next audio chunk from microphone"""
        if not self.is_streaming or not self.audio_available:
            return None
        
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.float32)
            return audio_array
        except Exception as e:
            logger.error(f"Error reading audio: {e}")
            return None
    
    def stop_audio(self):
        """Stop microphone capture"""
        self.is_streaming = False
        if self.audio_available and hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
        logger.info("Microphone stopped")


async def main():
    """Example usage of the streaming client"""
    parser = argparse.ArgumentParser(description="Real-time Video Dubbing Client")
    parser.add_argument("--server", default="ws://localhost:8000", help="Server WebSocket URL")
    parser.add_argument("--target-language", default="es", help="Target language code")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--fps", type=int, default=30, help="Video FPS")
    parser.add_argument("--enable-audio", action="store_true", help="Enable audio streaming")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create client
    client = StreamingDubbingClient(args.server)
    
    # Setup callbacks
    def on_frame_received(frame, timestamp):
        cv2.imshow('Processed Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            asyncio.create_task(client.disconnect())
    
    def on_transcription_received(data):
        print(f"Transcription: {data.get('original', '')} -> {data.get('translated', '')}")
    
    def on_stats_received(data):
        print(f"Server Stats: FPS={data.get('fps', 0):.2f}, "
              f"Frames={data.get('frames_processed', 0)}, "
              f"Audio={data.get('audio_chunks_processed', 0)}")
    
    def on_error(error):
        print(f"Error: {error}")
    
    client.on_frame_received = on_frame_received
    client.on_transcription_received = on_transcription_received
    client.on_stats_received = on_stats_received
    client.on_error = on_error
    
    try:
        # Connect to server
        if not await client.connect():
            print("Failed to connect to server")
            return
        
        # Configure streaming
        await client.configure({
            "target_language": args.target_language,
            "source_language": None,
            "enable_voice_cloning": False,
            "chunk_duration": 1.0,
            "whisper_model": "tiny"
        })
        
        # Start webcam
        webcam = WebcamStreamer(args.camera, args.fps)
        if not webcam.start_camera():
            print("Failed to start camera")
            return
        
        # Start microphone if enabled
        microphone = None
        if args.enable_audio:
            microphone = MicrophoneStreamer()
            microphone.start_audio()
        
        print("Streaming started. Press 'q' to quit.")
        
        # Main streaming loop
        while client.is_connected:
            # Send video frame
            frame = webcam.get_frame()
            if frame is not None:
                await client.send_frame(frame)
            
            # Send audio chunk
            if microphone:
                audio_chunk = microphone.get_audio_chunk()
                if audio_chunk is not None:
                    await client.send_audio(audio_chunk)
            
            # Request stats periodically
            if int(time.time()) % 5 == 0:  # Every 5 seconds
                await client.request_stats()
            
            await asyncio.sleep(0.01)  # Small delay
    
    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if microphone:
            microphone.stop_audio()
        webcam.stop_camera()
        await client.disconnect()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
