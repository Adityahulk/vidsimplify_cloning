"""
Example usage of the Video Dubbing and Lip-Sync System
"""
import asyncio
import os
from dubbing_pipeline import DubbingPipeline


async def example_basic_dubbing():
    """Basic video dubbing example"""
    print("🎬 Basic Video Dubbing Example")
    print("=" * 50)
    
    # Initialize pipeline
    pipeline = DubbingPipeline(
        chunk_duration=2.0,
        whisper_model="tiny",  # Fast processing
        translation_model="facebook/m2m100_418M",
        device="auto"
    )
    
    # Example video file (you'll need to provide your own)
    input_video = "sample_video.mp4"
    output_video = "output/dubbed_spanish.mp4"
    
    if not os.path.exists(input_video):
        print(f"❌ Sample video not found: {input_video}")
        print("Please provide a sample video file to test the system.")
        return
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    try:
        # Process video
        result = await pipeline.process_video(
            input_video_path=input_video,
            target_language="es",  # Spanish
            output_video_path=output_video
        )
        
        if result['success']:
            print(f"✅ Successfully dubbed video to Spanish!")
            print(f"📁 Output: {result['output_video']}")
            print(f"⏱️  Processing time: {result['processing_time']:.2f} seconds")
            print(f"🗣️  Detected language: {result['source_language']}")
        else:
            print(f"❌ Dubbing failed: {result['error']}")
            
    except Exception as e:
        print(f"💥 Error: {e}")


async def example_voice_cloning():
    """Voice cloning example"""
    print("\n🎤 Voice Cloning Example")
    print("=" * 50)
    
    # Initialize pipeline with voice cloning
    pipeline = DubbingPipeline(
        chunk_duration=2.0,
        whisper_model="base",  # Better quality for voice cloning
        translation_model="facebook/m2m100_418M",
        device="auto",
        enable_voice_cloning=True
    )
    
    input_video = "sample_video.mp4"
    speaker_reference = "reference_voice.wav"  # Reference speaker audio
    output_video = "output/dubbed_french_cloned.mp4"
    
    if not os.path.exists(input_video):
        print(f"❌ Sample video not found: {input_video}")
        return
    
    if not os.path.exists(speaker_reference):
        print(f"❌ Speaker reference not found: {speaker_reference}")
        print("Please provide a reference audio file for voice cloning.")
        return
    
    try:
        # Process with voice cloning
        result = await pipeline.process_video(
            input_video_path=input_video,
            target_language="fr",  # French
            output_video_path=output_video,
            speaker_reference=speaker_reference
        )
        
        if result['success']:
            print(f"✅ Successfully dubbed with voice cloning!")
            print(f"📁 Output: {result['output_video']}")
            print(f"⏱️  Processing time: {result['processing_time']:.2f} seconds")
        else:
            print(f"❌ Voice cloning failed: {result['error']}")
            
    except Exception as e:
        print(f"💥 Error: {e}")


async def example_high_quality():
    """High quality processing example"""
    print("\n🌟 High Quality Processing Example")
    print("=" * 50)
    
    # Initialize pipeline with high-quality models
    pipeline = DubbingPipeline(
        chunk_duration=2.0,
        whisper_model="medium",  # High quality transcription
        translation_model="facebook/nllb-200-distilled-600M",  # Better translation
        device="auto"
    )
    
    input_video = "sample_video.mp4"
    output_video = "output/dubbed_japanese_hq.mp4"
    
    if not os.path.exists(input_video):
        print(f"❌ Sample video not found: {input_video}")
        return
    
    try:
        # Process with high quality settings
        result = await pipeline.process_video(
            input_video_path=input_video,
            target_language="ja",  # Japanese
            output_video_path=output_video
        )
        
        if result['success']:
            print(f"✅ High quality dubbing completed!")
            print(f"📁 Output: {result['output_video']}")
            print(f"⏱️  Processing time: {result['processing_time']:.2f} seconds")
        else:
            print(f"❌ High quality processing failed: {result['error']}")
            
    except Exception as e:
        print(f"💥 Error: {e}")


def show_supported_languages():
    """Show supported languages"""
    print("\n🌍 Supported Languages")
    print("=" * 50)
    
    pipeline = DubbingPipeline()
    languages = pipeline.get_supported_languages()
    
    for component, langs in languages.items():
        print(f"\n{component.upper()}:")
        # Show first 20 languages
        display_langs = langs[:20]
        for i in range(0, len(display_langs), 5):
            print("  " + "  ".join(f"{lang:>3}" for lang in display_langs[i:i+5]))
        if len(langs) > 20:
            print(f"  ... and {len(langs) - 20} more")


def show_available_models():
    """Show available models"""
    print("\n🤖 Available Models")
    print("=" * 50)
    
    pipeline = DubbingPipeline()
    models = pipeline.get_available_models()
    
    for component, model_list in models.items():
        print(f"\n{component.upper()}:")
        for model in model_list:
            print(f"  • {model}")


async def main():
    """Run all examples"""
    print("🎬 Video Dubbing and Lip-Sync System - Examples")
    print("=" * 60)
    
    # Show system info
    show_supported_languages()
    show_available_models()
    
    # Run examples (uncomment the ones you want to test)
    
    # Basic dubbing
    # await example_basic_dubbing()
    
    # Voice cloning
    # await example_voice_cloning()
    
    # High quality processing
    # await example_high_quality()
    
    print("\n💡 To run examples:")
    print("1. Provide a sample video file named 'sample_video.mp4'")
    print("2. For voice cloning, provide 'reference_voice.wav'")
    print("3. Uncomment the example functions you want to run")
    print("4. Run: python example.py")


if __name__ == "__main__":
    asyncio.run(main())
