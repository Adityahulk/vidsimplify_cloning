"""
Speech transcription module using OpenAI Whisper
"""
import whisper
import torch
import librosa
import numpy as np
from typing import List, Optional, Dict
import asyncio


class WhisperTranscriber:
    """Handles speech-to-text transcription using Whisper"""
    
    def __init__(self, model_size: str = "tiny", device: str = "auto"):
        """
        Initialize Whisper model
        
        Args:
            model_size: Model size - "tiny", "base", "small", "medium", "large"
            device: Device to run on - "auto", "cpu", "cuda"
        """
        self.model_size = model_size
        self.device = self._get_device(device)
        self.model = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_model(self):
        """Load Whisper model"""
        try:
            print(f"Loading Whisper {self.model_size} model on {self.device}...")
            self.model = whisper.load_model(self.model_size, device=self.device)
            print("Whisper model loaded successfully!")
        except Exception as e:
            raise Exception(f"Failed to load Whisper model: {e}")
    
    async def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detection
            
        Returns:
            Dict with transcription results
        """
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # Transcribe
            result = self.model.transcribe(
                audio,
                language=language,
                fp16=self.device == "cuda",
                verbose=False
            )
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result.get("segments", []))
            }
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
    
    async def transcribe_audio_array(self, audio_array: np.ndarray, sample_rate: int = 16000) -> Dict:
        """
        Transcribe audio array directly
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            Dict with transcription results
        """
        try:
            # Ensure audio is at 16kHz
            if sample_rate != 16000:
                audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
            
            # Transcribe
            result = self.model.transcribe(
                audio_array,
                fp16=self.device == "cuda",
                verbose=False
            )
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result.get("segments", []))
            }
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
    
    def _calculate_confidence(self, segments: List[Dict]) -> float:
        """Calculate average confidence from segments"""
        if not segments:
            return 0.0
        
        confidences = []
        for segment in segments:
            if "avg_logprob" in segment:
                # Convert log probability to confidence
                conf = min(1.0, max(0.0, np.exp(segment["avg_logprob"])))
                confidences.append(conf)
        
        return np.mean(confidences) if confidences else 0.0
    
    async def batch_transcribe(self, audio_paths: List[str], language: Optional[str] = None) -> List[Dict]:
        """
        Transcribe multiple audio files in batch
        
        Args:
            audio_paths: List of audio file paths
            language: Language code or None for auto-detection
            
        Returns:
            List of transcription results
        """
        tasks = [self.transcribe_audio(path, language) for path in audio_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Transcription failed for {audio_paths[i]}: {result}")
                processed_results.append({
                    "text": "",
                    "language": "unknown",
                    "segments": [],
                    "confidence": 0.0,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return list(whisper.tokenizer.LANGUAGES.keys())
