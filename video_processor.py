"""
Video processing module for chunking and handling video/audio streams
"""
import cv2
import librosa
import numpy as np
import ffmpeg
import asyncio
from typing import List, Tuple, Optional
import tempfile
import os


class VideoChunker:
    """Handles video chunking and audio/video extraction"""
    
    def __init__(self, chunk_duration: float = 2.0):
        self.chunk_duration = chunk_duration
    
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio from video file"""
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            return output_path
        except Exception as e:
            raise Exception(f"Audio extraction failed: {e}")
    
    async def chunk_video(self, video_path: str, output_dir: str) -> List[Tuple[str, str, float]]:
        """
        Chunk video into segments and extract corresponding audio
        Returns list of (video_chunk_path, audio_chunk_path, start_time)
        """
        # Get video info
        probe = ffmpeg.probe(video_path)
        video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = float(probe['format']['duration'])
        fps = eval(video_stream['r_frame_rate'])
        
        chunks = []
        start_time = 0.0
        
        while start_time < duration:
            end_time = min(start_time + self.chunk_duration, duration)
            
            # Create chunk filenames
            video_chunk = os.path.join(output_dir, f"chunk_{int(start_time):04d}.mp4")
            audio_chunk = os.path.join(output_dir, f"chunk_{int(start_time):04d}.wav")
            
            # Extract video chunk
            (
                ffmpeg
                .input(video_path, ss=start_time, t=end_time - start_time)
                .output(video_chunk, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Extract audio chunk
            (
                ffmpeg
                .input(video_path, ss=start_time, t=end_time - start_time)
                .output(audio_chunk, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            
            chunks.append((video_chunk, audio_chunk, start_time))
            start_time = end_time
        
        return chunks
    
    async def merge_video_chunks(self, chunk_paths: List[str], output_path: str) -> str:
        """Merge video chunks into final output"""
        try:
            # Create concat file for ffmpeg
            concat_file = os.path.join(os.path.dirname(output_path), "concat.txt")
            with open(concat_file, 'w') as f:
                for chunk_path in chunk_paths:
                    f.write(f"file '{os.path.abspath(chunk_path)}'\n")
            
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            os.remove(concat_file)
            return output_path
        except Exception as e:
            raise Exception(f"Video merging failed: {e}")


class LiveStreamProcessor:
    """Handles live stream processing for webcam input"""
    
    def __init__(self, chunk_duration: float = 2.0):
        self.chunk_duration = chunk_duration
        self.cap = None
    
    async def start_stream(self, source: int = 0):
        """Start webcam stream"""
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise Exception("Could not open webcam")
        
        # Set resolution and fps
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
    
    async def get_chunk(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get next chunk of frames and audio"""
        frames = []
        frame_count = int(self.cap.get(cv2.CAP_PROP_FPS) * self.chunk_duration)
        
        for _ in range(frame_count):
            ret, frame = self.cap.read()
            if not ret:
                break
            frames.append(frame)
        
        if not frames:
            return None, None
        
        # Convert frames to video chunk
        video_chunk = np.stack(frames)
        
        # For live stream, we'll need to extract audio separately
        # This is a simplified version - in practice you'd capture audio from microphone
        audio_chunk = np.zeros((int(16000 * self.chunk_duration),))  # Placeholder
        
        return video_chunk, audio_chunk
    
    def stop_stream(self):
        """Stop webcam stream"""
        if self.cap:
            self.cap.release()
