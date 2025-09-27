"""
Test script to verify the Video Dubbing and Lip-Sync System installation
"""
import sys
import os
import asyncio


def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
        
        import torchaudio
        print(f"✅ TorchAudio {torchaudio.__version__}")
        
        import transformers
        print(f"✅ Transformers {transformers.__version__}")
        
        import whisper
        print("✅ Whisper")
        
        import cv2
        print(f"✅ OpenCV {cv2.__version__}")
        
        import librosa
        print(f"✅ Librosa {librosa.__version__}")
        
        import numpy as np
        print(f"✅ NumPy {np.__version__}")
        
        import ffmpeg
        print("✅ FFmpeg-Python")
        
        import TTS
        print(f"✅ Coqui TTS {TTS.__version__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_cuda():
    """Test CUDA availability"""
    print("\n🔧 Testing CUDA...")
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA available - {torch.cuda.get_device_name(0)}")
            print(f"   Device count: {torch.cuda.device_count()}")
            print(f"   Current device: {torch.cuda.current_device()}")
            return True
        else:
            print("⚠️  CUDA not available - will use CPU (slower)")
            return False
    except Exception as e:
        print(f"❌ CUDA test failed: {e}")
        return False


def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\n🎬 Testing FFmpeg...")
    
    try:
        import ffmpeg
        # Test basic ffmpeg functionality
        probe = ffmpeg.probe('README.md')  # This should fail gracefully
        print("❌ FFmpeg test failed - should not be able to probe text file")
        return False
    except ffmpeg.Error:
        print("✅ FFmpeg is working (correctly rejected non-media file)")
        return True
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False


def test_wav2lip():
    """Test Wav2Lip setup"""
    print("\n🎭 Testing Wav2Lip setup...")
    
    # Check if Wav2Lip directory exists
    if not os.path.exists("Wav2Lip"):
        print("❌ Wav2Lip directory not found")
        return False
    
    # Check if model file exists
    model_paths = [
        "models/wav2lip_gan.pth",
        "Wav2Lip/checkpoints/wav2lip_gan.pth"
    ]
    
    model_found = False
    for path in model_paths:
        if os.path.exists(path):
            print(f"✅ Wav2Lip model found at: {path}")
            model_found = True
            break
    
    if not model_found:
        print("❌ Wav2Lip model not found")
        print("   Please download the model from:")
        print("   https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth")
        return False
    
    # Check if inference script exists
    inference_paths = [
        "inference.py",
        "Wav2Lip/inference.py"
    ]
    
    inference_found = False
    for path in inference_paths:
        if os.path.exists(path):
            print(f"✅ Wav2Lip inference script found at: {path}")
            inference_found = True
            break
    
    if not inference_found:
        print("❌ Wav2Lip inference script not found")
        print("   Please copy inference.py from Wav2Lip directory")
        return False
    
    return True


def test_pipeline_components():
    """Test pipeline component initialization"""
    print("\n🔧 Testing pipeline components...")
    
    try:
        from video_processor import VideoChunker
        chunker = VideoChunker(2.0)
        print("✅ VideoChunker initialized")
        
        from transcription import WhisperTranscriber
        transcriber = WhisperTranscriber("tiny")
        print("✅ WhisperTranscriber initialized")
        
        from translation import TranslationEngine
        translator = TranslationEngine("facebook/m2m100_418M")
        print("✅ TranslationEngine initialized")
        
        from tts_engine import TTSEngine
        tts = TTSEngine("tts_models/en/ljspeech/tacotron2-DDC")
        print("✅ TTSEngine initialized")
        
        from lipsync import Wav2LipProcessor
        lipsync = Wav2LipProcessor()
        print("✅ Wav2LipProcessor initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline component test failed: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality without full processing"""
    print("\n⚡ Testing basic functionality...")
    
    try:
        from dubbing_pipeline import DubbingPipeline
        
        # Initialize pipeline
        pipeline = DubbingPipeline(
            chunk_duration=2.0,
            whisper_model="tiny",
            device="auto"
        )
        print("✅ DubbingPipeline initialized")
        
        # Test supported languages
        languages = pipeline.get_supported_languages()
        print(f"✅ Supported languages retrieved: {len(languages)} components")
        
        # Test available models
        models = pipeline.get_available_models()
        print(f"✅ Available models retrieved: {len(models)} components")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Video Dubbing and Lip-Sync System - System Test")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("CUDA Test", test_cuda),
        ("FFmpeg Test", test_ffmpeg),
        ("Wav2Lip Test", test_wav2lip),
        ("Pipeline Components Test", test_pipeline_components),
        ("Basic Functionality Test", lambda: asyncio.run(test_basic_functionality()))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\n🚀 Quick start:")
        print("  python main.py --list-languages")
        print("  python main.py --list-models")
        print("  python example.py")
    else:
        print("⚠️  Some tests failed. Please check the installation.")
        print("\n🔧 Common fixes:")
        print("  1. Install missing dependencies: pip install -r requirements.txt")
        print("  2. Setup Wav2Lip: python setup.py")
        print("  3. Check CUDA installation for GPU acceleration")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
