"""
Real-time Video Dubbing and Lip-Sync System
Main application entry point
"""
import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

from dubbing_pipeline import DubbingPipeline


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('dubbing.log')
        ]
    )


async def process_video_file(args):
    """Process a single video file"""
    pipeline = DubbingPipeline(
        chunk_duration=args.chunk_duration,
        whisper_model=args.whisper_model,
        translation_model=args.translation_model,
        tts_model=args.tts_model,
        device=args.device,
        enable_voice_cloning=args.enable_voice_cloning
    )
    
    result = await pipeline.process_video(
        input_video_path=args.input,
        target_language=args.target_language,
        output_video_path=args.output,
        source_language=args.source_language,
        speaker_reference=args.speaker_reference
    )
    
    if result['success']:
        print(f"\n✅ Processing completed successfully!")
        print(f"📁 Output video: {result['output_video']}")
        print(f"⏱️  Total time: {result['processing_time']:.2f} seconds")
        print(f"📊 Chunks processed: {result['chunks_processed']}")
        print(f"⚡ Avg time per chunk: {result['avg_time_per_chunk']:.2f} seconds")
        print(f"🗣️  Source language: {result['source_language']}")
        print(f"🌍 Target language: {result['target_language']}")
    else:
        print(f"\n❌ Processing failed: {result['error']}")
        sys.exit(1)


async def process_live_stream(args):
    """Process live webcam stream"""
    pipeline = DubbingPipeline(
        chunk_duration=args.chunk_duration,
        whisper_model=args.whisper_model,
        translation_model=args.translation_model,
        tts_model=args.tts_model,
        device=args.device,
        enable_voice_cloning=args.enable_voice_cloning
    )
    
    print(f"🎥 Starting live stream processing...")
    print(f"🌍 Target language: {args.target_language}")
    print(f"📹 Webcam source: {args.webcam_source}")
    print(f"Press 'q' to quit")
    
    await pipeline.process_live_stream(
        target_language=args.target_language,
        source_language=args.source_language,
        speaker_reference=args.speaker_reference,
        webcam_source=args.webcam_source
    )


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Real-time Video Dubbing and Lip-Sync System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a video file
  python main.py --input video.mp4 --output dubbed_video.mp4 --target-language es
  
  # Process with voice cloning
  python main.py --input video.mp4 --output dubbed_video.mp4 --target-language fr \\
                 --speaker-reference reference_voice.wav --enable-voice-cloning
  
  # Live webcam processing
  python main.py --live --target-language de --webcam-source 0
  
  # High quality processing
  python main.py --input video.mp4 --output dubbed_video.mp4 --target-language ja \\
                 --whisper-model medium --translation-model facebook/nllb-200-distilled-600M
        """
    )
    
    # Input/Output
    parser.add_argument('--input', '-i', help='Input video file path')
    parser.add_argument('--output', '-o', help='Output video file path')
    parser.add_argument('--live', action='store_true', help='Process live webcam stream')
    
    # Language settings
    parser.add_argument('--target-language', '-t', required=True,
                       help='Target language code (e.g., es, fr, de, ja, zh)')
    parser.add_argument('--source-language', '-s',
                       help='Source language code (auto-detect if not specified)')
    
    # Model settings
    parser.add_argument('--whisper-model', default='tiny',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')
    parser.add_argument('--translation-model', default='facebook/m2m100_418M',
                       help='Translation model name')
    parser.add_argument('--tts-model', default='tts_models/en/ljspeech/tacotron2-DDC',
                       help='TTS model name')
    
    # Processing settings
    parser.add_argument('--chunk-duration', type=float, default=2.0,
                       help='Video chunk duration in seconds')
    parser.add_argument('--device', default='auto',
                       choices=['auto', 'cpu', 'cuda'],
                       help='Device to run models on')
    
    # Voice cloning
    parser.add_argument('--enable-voice-cloning', action='store_true',
                       help='Enable voice cloning (requires speaker reference)')
    parser.add_argument('--speaker-reference',
                       help='Path to reference speaker audio for voice cloning')
    
    # Live stream settings
    parser.add_argument('--webcam-source', type=int, default=0,
                       help='Webcam source index for live processing')
    
    # Utility commands
    parser.add_argument('--list-languages', action='store_true',
                       help='List supported languages')
    parser.add_argument('--list-models', action='store_true',
                       help='List available models')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Handle utility commands
    if args.list_languages:
        pipeline = DubbingPipeline()
        languages = pipeline.get_supported_languages()
        print("Supported Languages:")
        for component, langs in languages.items():
            print(f"  {component}: {', '.join(langs[:10])}{'...' if len(langs) > 10 else ''}")
        return
    
    if args.list_models:
        pipeline = DubbingPipeline()
        models = pipeline.get_available_models()
        print("Available Models:")
        for component, model_list in models.items():
            print(f"  {component}: {', '.join(model_list[:5])}{'...' if len(model_list) > 5 else ''}")
        return
    
    # Validate arguments
    if not args.live and not args.input:
        parser.error("Either --input or --live must be specified")
    
    if not args.live and not args.output:
        parser.error("--output is required when processing video files")
    
    if args.enable_voice_cloning and not args.speaker_reference:
        parser.error("--speaker-reference is required when voice cloning is enabled")
    
    # Check if input file exists
    if args.input and not os.path.exists(args.input):
        parser.error(f"Input file does not exist: {args.input}")
    
    # Create output directory if needed
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    
    # Run the appropriate processing function
    try:
        if args.live:
            asyncio.run(process_live_stream(args))
        else:
            asyncio.run(process_video_file(args))
    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logging.exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
