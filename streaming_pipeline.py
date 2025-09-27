"""
Optimized streaming pipeline for real-time video dubbing with lip-sync
Designed for low latency and high throughput
"""
import asyncio
import time
import numpy as np
import cv2
import torch
import librosa
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
import threading
import queue
import logging

from transcription import WhisperTranscriber
from translation import TranslationEngine
from tts_engine import TTSEngine
from lipsync import Wav2LipProcessor


logger = logging.getLogger(__name__)


class StreamingAudioProcessor:
    """Optimized audio processing for streaming"""
    
    def __init__(self, sample_rate: int = 16000, chunk_duration: float = 1.0):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        
        # Audio buffer for continuous processing
        self.audio_buffer = deque(maxlen=int(sample_rate * 5))  # 5 second buffer
        self.overlap_size = int(sample_rate * 0.5)  # 0.5 second overlap
        
        # Processing components
        self.transcriber = None
        self.translator = None
        self.tts_engine = None
        
        # Results queue
        self.processed_audio_queue = queue.Queue(maxsize=10)
        self.transcription_queue = queue.Queue(maxsize=10)
        
        # State
        self.is_processing = False
        self.last_transcription_time = 0
        self.min_transcription_interval = 1.0  # Minimum 1 second between transcriptions
        
    async def initialize(self, whisper_model: str = "tiny", 
                        translation_model: str = "facebook/m2m100_418M",
                        tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC",
                        device: str = "auto"):
        """Initialize audio processing components"""
        try:
            self.transcriber = WhisperTranscriber(whisper_model, device)
            self.translator = TranslationEngine(translation_model, device)
            self.tts_engine = TTSEngine(tts_model, device)
            
            logger.info("Streaming audio processor initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio processor: {e}")
            return False
    
    def add_audio_chunk(self, audio_data: np.ndarray):
        """Add audio chunk to buffer"""
        if len(audio_data) > 0:
            self.audio_buffer.extend(audio_data)
    
    async def process_audio_stream(self, target_language: str, source_language: Optional[str] = None):
        """Process audio stream continuously"""
        self.is_processing = True
        
        while self.is_processing:
            try:
                # Check if we have enough audio for processing
                if len(self.audio_buffer) >= self.chunk_size:
                    current_time = time.time()
                    
                    # Only transcribe if enough time has passed
                    if current_time - self.last_transcription_time >= self.min_transcription_interval:
                        await self._process_audio_chunk(target_language, source_language)
                        self.last_transcription_time = current_time
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Audio stream processing error: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_audio_chunk(self, target_language: str, source_language: Optional[str]):
        """Process a single audio chunk"""
        try:
            # Extract audio chunk
            audio_chunk = np.array(list(self.audio_buffer)[:self.chunk_size])
            
            if len(audio_chunk) < self.chunk_size:
                return
            
            # Transcribe
            transcription_result = await self.transcriber.transcribe_audio_array(audio_chunk)
            transcribed_text = transcription_result.get('text', '').strip()
            
            if not transcribed_text:
                return
            
            # Translate
            detected_language = transcription_result.get('language', source_language or 'en')
            translated_text = await self.translator.translate_text(
                transcribed_text, detected_language, target_language
            )
            
            # Generate TTS
            # For streaming, we need to generate audio that matches the original timing
            original_duration = len(audio_chunk) / self.sample_rate
            temp_audio_path = f"temp/tts_temp_{int(time.time() * 1000)}.wav"
            
            await self.tts_engine.synthesize_with_timing(
                translated_text, original_duration, temp_audio_path, None, target_language
            )
            
            # Load generated audio
            generated_audio, _ = librosa.load(temp_audio_path, sr=self.sample_rate)
            
            # Add to processed audio queue
            try:
                self.processed_audio_queue.put_nowait({
                    'audio': generated_audio,
                    'timestamp': time.time(),
                    'original_text': transcribed_text,
                    'translated_text': translated_text
                })
            except queue.Full:
                # Remove oldest if queue is full
                try:
                    self.processed_audio_queue.get_nowait()
                    self.processed_audio_queue.put_nowait({
                        'audio': generated_audio,
                        'timestamp': time.time(),
                        'original_text': transcribed_text,
                        'translated_text': translated_text
                    })
                except:
                    pass
            
            # Add transcription to queue for debugging
            try:
                self.transcription_queue.put_nowait({
                    'original': transcribed_text,
                    'translated': translated_text,
                    'timestamp': time.time()
                })
            except queue.Full:
                pass
            
            # Remove processed audio from buffer (keep overlap)
            for _ in range(self.chunk_size - self.overlap_size):
                if self.audio_buffer:
                    self.audio_buffer.popleft()
            
        except Exception as e:
            logger.error(f"Audio chunk processing error: {e}")
    
    def get_processed_audio(self) -> Optional[Dict]:
        """Get processed audio chunk"""
        try:
            return self.processed_audio_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_transcription(self) -> Optional[Dict]:
        """Get latest transcription"""
        try:
            return self.transcription_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop_processing(self):
        """Stop audio processing"""
        self.is_processing = False


class StreamingVideoProcessor:
    """Optimized video processing for streaming"""
    
    def __init__(self, fps: int = 30, resolution: Tuple[int, int] = (640, 480)):
        self.fps = fps
        self.resolution = resolution
        self.frame_interval = 1.0 / fps
        
        # Frame buffers
        self.frame_queue = queue.Queue(maxsize=30)
        self.processed_frame_queue = queue.Queue(maxsize=30)
        
        # Lip-sync processor
        self.lipsync_processor = None
        
        # State
        self.is_processing = False
        self.last_frame_time = 0
        
    async def initialize(self, device: str = "auto"):
        """Initialize video processing components"""
        try:
            self.lipsync_processor = Wav2LipProcessor(device=device)
            logger.info("Streaming video processor initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize video processor: {e}")
            return False
    
    def add_frame(self, frame: np.ndarray, timestamp: float):
        """Add frame to processing queue"""
        try:
            # Resize frame if needed
            if frame.shape[:2] != self.resolution[::-1]:
                frame = cv2.resize(frame, self.resolution)
            
            self.frame_queue.put_nowait((frame, timestamp))
        except queue.Full:
            # Remove oldest frame
            try:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait((frame, timestamp))
            except:
                pass
    
    async def process_video_stream(self, audio_processor: StreamingAudioProcessor):
        """Process video stream with lip-sync"""
        self.is_processing = True
        
        while self.is_processing:
            try:
                # Get frame from queue
                try:
                    frame, timestamp = self.frame_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                # Check timing
                current_time = time.time()
                if current_time - self.last_frame_time >= self.frame_interval:
                    self.last_frame_time = current_time
                    
                    # Check for processed audio
                    audio_data = audio_processor.get_processed_audio()
                    
                    if audio_data:
                        # Apply lip-sync with processed audio
                        processed_frame = await self._apply_lipsync(frame, audio_data['audio'])
                    else:
                        # No audio available, just pass frame through
                        processed_frame = frame
                    
                    # Add to output queue
                    try:
                        self.processed_frame_queue.put_nowait((processed_frame, timestamp))
                    except queue.Full:
                        try:
                            self.processed_frame_queue.get_nowait()
                            self.processed_frame_queue.put_nowait((processed_frame, timestamp))
                        except:
                            pass
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Video stream processing error: {e}")
                await asyncio.sleep(0.01)
    
    async def _apply_lipsync(self, frame: np.ndarray, audio: np.ndarray) -> np.ndarray:
        """Apply lip-sync to frame"""
        try:
            # This is a simplified version - in practice you'd need more sophisticated lip-sync
            # For now, just return the original frame
            # In a full implementation, you'd use Wav2Lip or similar
            
            # Save temporary files
            temp_video_path = f"temp/frame_temp_{int(time.time() * 1000)}.mp4"
            temp_audio_path = f"temp/audio_temp_{int(time.time() * 1000)}.wav"
            temp_output_path = f"temp/output_temp_{int(time.time() * 1000)}.mp4"
            
            # Create video from frame
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, self.fps, self.resolution)
            out.write(frame)
            out.release()
            
            # Save audio
            import soundfile as sf
            sf.write(temp_audio_path, audio, 16000)
            
            # Apply lip-sync
            await self.lipsync_processor.process_chunk(
                temp_video_path, temp_audio_path, temp_output_path
            )
            
            # Read processed frame
            cap = cv2.VideoCapture(temp_output_path)
            ret, processed_frame = cap.read()
            cap.release()
            
            if ret:
                return processed_frame
            else:
                return frame
            
        except Exception as e:
            logger.error(f"Lip-sync error: {e}")
            return frame
    
    def get_processed_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """Get processed frame"""
        try:
            return self.processed_frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop_processing(self):
        """Stop video processing"""
        self.is_processing = False


class StreamingDubbingPipeline:
    """Main streaming pipeline orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Processors
        self.audio_processor = StreamingAudioProcessor(
            sample_rate=config.get('audio_sample_rate', 16000),
            chunk_duration=config.get('chunk_duration', 1.0)
        )
        
        self.video_processor = StreamingVideoProcessor(
            fps=config.get('fps', 30),
            resolution=config.get('resolution', (640, 480))
        )
        
        # Processing tasks
        self.audio_task = None
        self.video_task = None
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'audio_chunks_processed': 0,
            'processing_time': 0,
            'fps': 0,
            'latency': 0
        }
        
        self.start_time = 0
    
    async def initialize(self):
        """Initialize the streaming pipeline"""
        try:
            # Initialize processors
            audio_success = await self.audio_processor.initialize(
                whisper_model=self.config.get('whisper_model', 'tiny'),
                translation_model=self.config.get('translation_model', 'facebook/m2m100_418M'),
                tts_model=self.config.get('tts_model', 'tts_models/en/ljspeech/tacotron2-DDC'),
                device=self.config.get('device', 'auto')
            )
            
            video_success = await self.video_processor.initialize(
                device=self.config.get('device', 'auto')
            )
            
            if not (audio_success and video_success):
                return False
            
            logger.info("Streaming dubbing pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize streaming pipeline: {e}")
            return False
    
    async def start_processing(self, target_language: str, source_language: Optional[str] = None):
        """Start the processing pipeline"""
        self.start_time = time.time()
        
        # Start audio processing
        self.audio_task = asyncio.create_task(
            self.audio_processor.process_audio_stream(target_language, source_language)
        )
        
        # Start video processing
        self.video_task = asyncio.create_task(
            self.video_processor.process_video_stream(self.audio_processor)
        )
        
        logger.info("Streaming pipeline processing started")
    
    async def stop_processing(self):
        """Stop the processing pipeline"""
        # Stop processors
        self.audio_processor.stop_processing()
        self.video_processor.stop_processing()
        
        # Cancel tasks
        if self.audio_task:
            self.audio_task.cancel()
        if self.video_task:
            self.video_task.cancel()
        
        logger.info("Streaming pipeline processing stopped")
    
    def add_frame(self, frame: np.ndarray, timestamp: float):
        """Add frame to processing pipeline"""
        self.video_processor.add_frame(frame, timestamp)
    
    def add_audio(self, audio_data: np.ndarray):
        """Add audio data to processing pipeline"""
        self.audio_processor.add_audio_chunk(audio_data)
    
    def get_processed_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """Get processed frame from pipeline"""
        return self.video_processor.get_processed_frame()
    
    def get_transcription(self) -> Optional[Dict]:
        """Get latest transcription"""
        return self.audio_processor.get_transcription()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time > 0 else 1
        
        self.stats['fps'] = self.stats['frames_processed'] / elapsed_time
        self.stats['latency'] = elapsed_time
        
        return self.stats.copy()
    
    def update_stats(self, frames: int = 0, audio_chunks: int = 0):
        """Update processing statistics"""
        self.stats['frames_processed'] += frames
        self.stats['audio_chunks_processed'] += audio_chunks
