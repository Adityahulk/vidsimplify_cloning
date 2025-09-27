"""
Text-to-Speech module using Coqui TTS
"""
import torch
import numpy as np
import soundfile as sf
from TTS.api import TTS
from typing import Dict, Optional, List
import asyncio
import tempfile
import os


class TTSEngine:
    """Handles text-to-speech synthesis using Coqui TTS"""
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC", device: str = "auto"):
        """
        Initialize TTS model
        
        Args:
            model_name: TTS model name from Coqui TTS
            device: Device to run on - "auto", "cpu", "cuda"
        """
        self.model_name = model_name
        self.device = self._get_device(device)
        self.tts = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_model(self):
        """Load TTS model"""
        try:
            print(f"Loading TTS model {self.model_name} on {self.device}...")
            self.tts = TTS(model_name=self.model_name).to(self.device)
            print("TTS model loaded successfully!")
        except Exception as e:
            raise Exception(f"Failed to load TTS model: {e}")
    
    async def synthesize_speech(
        self, 
        text: str, 
        output_path: str,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            speaker_wav: Path to reference speaker audio for voice cloning
            language: Language code
            
        Returns:
            Path to generated audio file
        """
        if not text.strip():
            # Generate silence for empty text
            silence = np.zeros(int(16000 * 0.5))  # 0.5 seconds of silence
            sf.write(output_path, silence, 16000)
            return output_path
        
        try:
            if speaker_wav and hasattr(self.tts, 'speaker_wav'):
                # Voice cloning
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    speaker_wav=speaker_wav,
                    language=language
                )
            else:
                # Standard synthesis
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    language=language
                )
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Speech synthesis failed: {e}")
    
    async def synthesize_with_timing(
        self, 
        text: str, 
        target_duration: float,
        output_path: str,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """
        Synthesize speech with target duration matching
        
        Args:
            text: Text to synthesize
            target_duration: Target duration in seconds
            output_path: Path to save audio file
            speaker_wav: Path to reference speaker audio
            language: Language code
            
        Returns:
            Path to generated audio file
        """
        try:
            # First, synthesize normally
            temp_path = output_path.replace('.wav', '_temp.wav')
            await self.synthesize_speech(text, temp_path, speaker_wav, language)
            
            # Load generated audio
            audio, sr = sf.read(temp_path)
            current_duration = len(audio) / sr
            
            if abs(current_duration - target_duration) < 0.1:
                # Duration is close enough, just rename
                os.rename(temp_path, output_path)
            else:
                # Adjust duration by time-stretching or padding
                target_samples = int(target_duration * sr)
                
                if current_duration < target_duration:
                    # Pad with silence
                    padding = target_samples - len(audio)
                    audio = np.pad(audio, (0, padding), mode='constant')
                else:
                    # Truncate or time-stretch
                    if len(audio) > target_samples:
                        audio = audio[:target_samples]
                    else:
                        # Simple time-stretching by repeating samples
                        repeat_factor = target_samples / len(audio)
                        audio = np.repeat(audio, int(repeat_factor))
                        if len(audio) > target_samples:
                            audio = audio[:target_samples]
                
                sf.write(output_path, audio, sr)
                os.remove(temp_path)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Speech synthesis with timing failed: {e}")
    
    async def batch_synthesize(
        self, 
        texts: List[str], 
        output_dir: str,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> List[str]:
        """
        Synthesize multiple texts in batch
        
        Args:
            texts: List of texts to synthesize
            output_dir: Directory to save audio files
            speaker_wav: Path to reference speaker audio
            language: Language code
            
        Returns:
            List of paths to generated audio files
        """
        os.makedirs(output_dir, exist_ok=True)
        
        tasks = []
        output_paths = []
        
        for i, text in enumerate(texts):
            output_path = os.path.join(output_dir, f"tts_{i:04d}.wav")
            output_paths.append(output_path)
            tasks.append(
                self.synthesize_speech(text, output_path, speaker_wav, language)
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"TTS failed for text {i}: {result}")
                # Create silence file
                silence = np.zeros(int(16000 * 0.5))
                sf.write(output_paths[i], silence, 16000)
                processed_paths.append(output_paths[i])
            else:
                processed_paths.append(output_paths[i])
        
        return processed_paths
    
    def get_available_models(self) -> List[str]:
        """Get list of available TTS models"""
        try:
            return TTS.list_models()
        except:
            return [
                "tts_models/en/ljspeech/tacotron2-DDC",
                "tts_models/en/vctk/vits",
                "tts_models/en/ljspeech/fast_pitch",
                "tts_models/multilingual/multi-dataset/your_tts"
            ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']


class VoiceCloner:
    """Handles voice cloning for speaker adaptation"""
    
    def __init__(self, device: str = "auto"):
        self.device = self._get_device(device)
        self.tts = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_model(self):
        """Load voice cloning model"""
        try:
            print(f"Loading voice cloning model on {self.device}...")
            # Use YourTTS for multilingual voice cloning
            self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts").to(self.device)
            print("Voice cloning model loaded successfully!")
        except Exception as e:
            print(f"Failed to load voice cloning model: {e}")
            # Fallback to standard TTS
            self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC").to(self.device)
    
    async def clone_voice(
        self, 
        text: str, 
        speaker_wav: str, 
        output_path: str,
        language: str = "en"
    ) -> str:
        """
        Clone voice from reference audio
        
        Args:
            text: Text to synthesize
            speaker_wav: Path to reference speaker audio
            output_path: Path to save cloned audio
            language: Language code
            
        Returns:
            Path to generated audio file
        """
        try:
            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language
            )
            return output_path
        except Exception as e:
            raise Exception(f"Voice cloning failed: {e}")
