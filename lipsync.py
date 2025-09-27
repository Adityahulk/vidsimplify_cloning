"""
Lip-sync module using Wav2Lip
"""
import torch
import cv2
import numpy as np
import os
import subprocess
import tempfile
from typing import Tuple, Optional
import asyncio
import shutil


class Wav2LipProcessor:
    """Handles lip-sync processing using Wav2Lip model"""
    
    def __init__(self, model_path: str = None, device: str = "auto"):
        """
        Initialize Wav2Lip processor
        
        Args:
            model_path: Path to Wav2Lip model file
            device: Device to run on - "auto", "cpu", "cuda"
        """
        self.device = self._get_device(device)
        self.model_path = model_path or self._download_model()
        self.model = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _download_model(self) -> str:
        """Download Wav2Lip model if not present"""
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "wav2lip_gan.pth")
        
        if not os.path.exists(model_path):
            print("Downloading Wav2Lip model...")
            try:
                # Download model from Wav2Lip repository
                import requests
                url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print("Wav2Lip model downloaded successfully!")
            except Exception as e:
                print(f"Failed to download Wav2Lip model: {e}")
                print("Please manually download the model from:")
                print("https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth")
                print(f"and place it at: {model_path}")
        
        return model_path
    
    def _load_model(self):
        """Load Wav2Lip model"""
        try:
            print(f"Loading Wav2Lip model on {self.device}...")
            
            # Import Wav2Lip modules (you'll need to clone the repo)
            try:
                from models.wav2lip import Wav2Lip
            except ImportError:
                print("Wav2Lip modules not found. Please clone the repository:")
                print("git clone https://github.com/Rudrabha/Wav2Lip.git")
                print("and install the requirements.")
                raise ImportError("Wav2Lip modules not available")
            
            self.model = Wav2Lip()
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['state_dict'])
            self.model.eval()
            self.model = self.model.to(self.device)
            
            print("Wav2Lip model loaded successfully!")
            
        except Exception as e:
            raise Exception(f"Failed to load Wav2Lip model: {e}")
    
    async def process_chunk(
        self, 
        video_path: str, 
        audio_path: str, 
        output_path: str,
        face_detect: bool = True
    ) -> str:
        """
        Process a single video chunk with lip-sync
        
        Args:
            video_path: Path to input video chunk
            audio_path: Path to input audio chunk
            output_path: Path to save lip-synced video
            face_detect: Whether to detect faces automatically
            
        Returns:
            Path to processed video
        """
        try:
            # Use Wav2Lip inference
            cmd = [
                "python", "inference.py",
                "--checkpoint_path", self.model_path,
                "--face", video_path,
                "--audio", audio_path,
                "--outfile", output_path,
                "--static", str(not face_detect),
                "--fps", "25",
                "--pads", "0", "10", "0", "0"
            ]
            
            if self.device == "cuda":
                cmd.extend(["--resize_factor", "1"])
            
            # Run Wav2Lip inference
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Wav2Lip inference failed: {result.stderr}")
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Lip-sync processing failed: {e}")
    
    async def batch_process(
        self, 
        video_audio_pairs: list, 
        output_dir: str,
        face_detect: bool = True
    ) -> list:
        """
        Process multiple video chunks with lip-sync
        
        Args:
            video_audio_pairs: List of (video_path, audio_path) tuples
            output_dir: Directory to save processed videos
            face_detect: Whether to detect faces automatically
            
        Returns:
            List of paths to processed videos
        """
        os.makedirs(output_dir, exist_ok=True)
        
        tasks = []
        output_paths = []
        
        for i, (video_path, audio_path) in enumerate(video_audio_pairs):
            output_path = os.path.join(output_dir, f"lipsync_{i:04d}.mp4")
            output_paths.append(output_path)
            tasks.append(
                self.process_chunk(video_path, audio_path, output_path, face_detect)
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Lip-sync failed for chunk {i}: {result}")
                # Copy original video as fallback
                shutil.copy2(video_audio_pairs[i][0], output_paths[i])
                processed_paths.append(output_paths[i])
            else:
                processed_paths.append(output_paths[i])
        
        return processed_paths


class FaceDetector:
    """Face detection utilities for Wav2Lip"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def detect_faces(self, image: np.ndarray) -> list:
        """
        Detect faces in image
        
        Args:
            image: Input image
            
        Returns:
            List of face rectangles (x, y, w, h)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        return faces.tolist()
    
    def crop_largest_face(self, image: np.ndarray) -> np.ndarray:
        """
        Crop the largest face from image
        
        Args:
            image: Input image
            
        Returns:
            Cropped face image
        """
        faces = self.detect_faces(image)
        
        if not faces:
            return image
        
        # Get largest face
        largest_face = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = largest_face
        
        # Add padding
        padding = 50
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)
        
        return image[y:y+h, x:x+w]


class VideoPreprocessor:
    """Video preprocessing utilities for lip-sync"""
    
    @staticmethod
    def extract_frames(video_path: str, output_dir: str) -> list:
        """
        Extract frames from video
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save frames
            
        Returns:
            List of frame file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        frame_paths = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_path = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            frame_count += 1
        
        cap.release()
        return frame_paths
    
    @staticmethod
    def frames_to_video(frame_paths: list, output_path: str, fps: int = 25) -> str:
        """
        Convert frames to video
        
        Args:
            frame_paths: List of frame file paths
            output_path: Path to save video
            fps: Frames per second
            
        Returns:
            Path to generated video
        """
        if not frame_paths:
            raise Exception("No frames provided")
        
        # Read first frame to get dimensions
        first_frame = cv2.imread(frame_paths[0])
        height, width, _ = first_frame.shape
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame_path in frame_paths:
            frame = cv2.imread(frame_path)
            out.write(frame)
        
        out.release()
        return output_path
