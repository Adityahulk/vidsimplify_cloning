"""
Main dubbing pipeline orchestrator
"""
import asyncio
import os
import tempfile
import time
from typing import List, Dict, Optional, Tuple
import logging

from video_processor import VideoChunker
from transcription import WhisperTranscriber
from translation import TranslationEngine, LanguageDetector
from tts_engine import TTSEngine, VoiceCloner
from lipsync import Wav2LipProcessor


class DubbingPipeline:
    """Main pipeline for real-time video dubbing with lip-sync"""
    
    def __init__(
        self,
        chunk_duration: float = 2.0,
        whisper_model: str = "tiny",
        translation_model: str = "facebook/m2m100_418M",
        tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC",
        device: str = "auto",
        enable_voice_cloning: bool = True
    ):
        """
        Initialize dubbing pipeline
        
        Args:
            chunk_duration: Duration of video chunks in seconds
            whisper_model: Whisper model size
            translation_model: Translation model name
            tts_model: TTS model name
            device: Device to run on
            enable_voice_cloning: Whether to enable voice cloning
        """
        self.chunk_duration = chunk_duration
        self.device = device
        self.enable_voice_cloning = enable_voice_cloning
        
        # Initialize components
        self.video_chunker = VideoChunker(chunk_duration)
        self.transcriber = WhisperTranscriber(whisper_model, device)
        self.translator = TranslationEngine(translation_model, device)
        self.tts_engine = TTSEngine(tts_model, device)
        self.lipsync_processor = Wav2LipProcessor(device=device)
        
        if enable_voice_cloning:
            self.voice_cloner = VoiceCloner(device)
        
        self.logger = logging.getLogger(__name__)
    
    async def process_video(
        self,
        input_video_path: str,
        target_language: str,
        output_video_path: str,
        source_language: Optional[str] = None,
        speaker_reference: Optional[str] = None
    ) -> Dict:
        """
        Process complete video through dubbing pipeline
        
        Args:
            input_video_path: Path to input video
            target_language: Target language code
            output_video_path: Path to save output video
            source_language: Source language code (auto-detect if None)
            speaker_reference: Path to reference speaker audio for voice cloning
            
        Returns:
            Dict with processing results and metadata
        """
        start_time = time.time()
        temp_dir = tempfile.mkdtemp()
        
        try:
            self.logger.info(f"Starting dubbing pipeline for {input_video_path}")
            
            # Step 1: Chunk video
            self.logger.info("Step 1: Chunking video...")
            chunks = await self.video_chunker.chunk_video(input_video_path, temp_dir)
            self.logger.info(f"Created {len(chunks)} chunks")
            
            # Step 2: Process chunks in parallel
            self.logger.info("Step 2: Processing chunks...")
            processed_chunks = await self._process_chunks_parallel(
                chunks, target_language, source_language, speaker_reference, temp_dir
            )
            
            # Step 3: Merge processed chunks
            self.logger.info("Step 3: Merging chunks...")
            chunk_paths = [chunk['output_path'] for chunk in processed_chunks]
            await self.video_chunker.merge_video_chunks(chunk_paths, output_video_path)
            
            # Calculate processing time
            total_time = time.time() - start_time
            
            result = {
                "success": True,
                "input_video": input_video_path,
                "output_video": output_video_path,
                "target_language": target_language,
                "source_language": processed_chunks[0].get('detected_language', source_language),
                "chunks_processed": len(processed_chunks),
                "processing_time": total_time,
                "avg_time_per_chunk": total_time / len(chunks),
                "chunks": processed_chunks
            }
            
            self.logger.info(f"Pipeline completed in {total_time:.2f} seconds")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_dir)
    
    async def _process_chunks_parallel(
        self,
        chunks: List[Tuple[str, str, float]],
        target_language: str,
        source_language: Optional[str],
        speaker_reference: Optional[str],
        temp_dir: str
    ) -> List[Dict]:
        """Process chunks in parallel for better performance"""
        
        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(4)  # Process 4 chunks at a time
        
        async def process_single_chunk(chunk_data):
            async with semaphore:
                return await self._process_single_chunk(
                    chunk_data, target_language, source_language, speaker_reference, temp_dir
                )
        
        tasks = [process_single_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Chunk {i} failed: {result}")
                # Create fallback chunk (original video)
                video_path, audio_path, start_time = chunks[i]
                output_path = os.path.join(temp_dir, f"processed_{i:04d}.mp4")
                os.rename(video_path, output_path)
                
                processed_results.append({
                    "chunk_index": i,
                    "start_time": start_time,
                    "output_path": output_path,
                    "error": str(result),
                    "transcription": "",
                    "translation": "",
                    "detected_language": "unknown"
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_chunk(
        self,
        chunk_data: Tuple[str, str, float],
        target_language: str,
        source_language: Optional[str],
        speaker_reference: Optional[str],
        temp_dir: str
    ) -> Dict:
        """Process a single video chunk through the pipeline"""
        
        video_path, audio_path, start_time = chunk_data
        chunk_index = int(start_time)
        
        try:
            # Step 1: Transcribe audio
            transcription_result = await self.transcriber.transcribe_audio(audio_path, source_language)
            detected_language = transcription_result.get('language', source_language)
            transcribed_text = transcription_result.get('text', '')
            
            if not transcribed_text.strip():
                # No speech detected, return original chunk
                output_path = os.path.join(temp_dir, f"processed_{chunk_index:04d}.mp4")
                os.rename(video_path, output_path)
                
                return {
                    "chunk_index": chunk_index,
                    "start_time": start_time,
                    "output_path": output_path,
                    "transcription": "",
                    "translation": "",
                    "detected_language": detected_language
                }
            
            # Step 2: Translate text
            translated_text = await self.translator.translate_text(
                transcribed_text, detected_language, target_language
            )
            
            # Step 3: Generate TTS audio
            tts_audio_path = os.path.join(temp_dir, f"tts_{chunk_index:04d}.wav")
            
            if self.enable_voice_cloning and speaker_reference:
                await self.voice_cloner.clone_voice(
                    translated_text, speaker_reference, tts_audio_path, target_language
                )
            else:
                await self.tts_engine.synthesize_speech(
                    translated_text, tts_audio_path, None, target_language
                )
            
            # Step 4: Apply lip-sync
            output_path = os.path.join(temp_dir, f"processed_{chunk_index:04d}.mp4")
            await self.lipsync_processor.process_chunk(
                video_path, tts_audio_path, output_path
            )
            
            return {
                "chunk_index": chunk_index,
                "start_time": start_time,
                "output_path": output_path,
                "transcription": transcribed_text,
                "translation": translated_text,
                "detected_language": detected_language,
                "tts_audio_path": tts_audio_path
            }
            
        except Exception as e:
            # Return original chunk on error
            output_path = os.path.join(temp_dir, f"processed_{chunk_index:04d}.mp4")
            os.rename(video_path, output_path)
            
            return {
                "chunk_index": chunk_index,
                "start_time": start_time,
                "output_path": output_path,
                "error": str(e),
                "transcription": "",
                "translation": "",
                "detected_language": "unknown"
            }
    
    async def process_live_stream(
        self,
        target_language: str,
        source_language: Optional[str] = None,
        speaker_reference: Optional[str] = None,
        webcam_source: int = 0
    ):
        """
        Process live webcam stream (experimental)
        
        Args:
            target_language: Target language code
            source_language: Source language code
            speaker_reference: Path to reference speaker audio
            webcam_source: Webcam source index
        """
        from video_processor import LiveStreamProcessor
        import cv2
        
        stream_processor = LiveStreamProcessor(self.chunk_duration)
        
        try:
            await stream_processor.start_stream(webcam_source)
            self.logger.info("Started live stream processing...")
            
            while True:
                # Get chunk from stream
                video_chunk, audio_chunk = await stream_processor.get_chunk()
                
                if video_chunk is None:
                    break
                
                # Process chunk (simplified version)
                # Note: This is a basic implementation
                # In practice, you'd need more sophisticated audio capture
                
                # Save chunk temporarily
                temp_video_path = os.path.join(tempfile.mkdtemp(), "chunk.mp4")
                temp_audio_path = os.path.join(tempfile.mkdtemp(), "chunk.wav")
                
                # Process through pipeline (simplified)
                # ... processing logic here ...
                
                # Display result (you'd implement proper streaming here)
                cv2.imshow('Processed Stream', video_chunk[0])
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("Live stream processing stopped by user")
        except Exception as e:
            self.logger.error(f"Live stream processing failed: {e}")
        finally:
            stream_processor.stop_stream()
            cv2.destroyAllWindows()
    
    def _cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp files: {e}")
    
    def get_supported_languages(self) -> Dict[str, List[str]]:
        """Get supported languages for each component"""
        return {
            "transcription": self.transcriber.get_supported_languages(),
            "translation": self.translator.get_supported_languages(),
            "tts": self.tts_engine.get_supported_languages()
        }
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models for each component"""
        return {
            "whisper": ["tiny", "base", "small", "medium", "large"],
            "translation": ["facebook/m2m100_418M", "facebook/nllb-200-distilled-600M"],
            "tts": self.tts_engine.get_available_models()
        }
