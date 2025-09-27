# Real-Time Video Dubbing + Lip-Sync System

A Python system that takes a video (or live stream) and outputs a dubbed version in a target language with realistic lip-sync. The system works in near real-time (~1–2s latency) using state-of-the-art AI models.

## 🚀 Features

- **Real-time Processing**: ~1-2 second latency per chunk
- **Multi-language Support**: 100+ languages supported
- **Voice Cloning**: Clone original speaker's voice in target language
- **High-Quality Lip-Sync**: Using Wav2Lip for realistic lip movements
- **Live Streaming**: Support for webcam input (experimental)
- **GPU Acceleration**: Optimized for CUDA-enabled systems
- **Modular Design**: Easy to swap models and components

## 📋 Requirements

- Python 3.10+
- CUDA-capable GPU (recommended)
- FFmpeg installed on system
- 8GB+ RAM (16GB+ recommended for large models)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd vidsimplify_cloning
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg python3-dev
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download FFmpeg from https://ffmpeg.org/download.html and add to PATH.

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Wav2Lip (Required for Lip-Sync)

```bash
# Clone Wav2Lip repository
git clone https://github.com/Rudrabha/Wav2Lip.git
cd Wav2Lip

# Install Wav2Lip dependencies
pip install -r requirements.txt

# Download the model
wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth -O models/wav2lip_gan.pth

# Copy inference script to main directory
cp inference.py ../
cd ..
```

### 5. Verify Installation
```bash
python main.py --list-languages
python main.py --list-models
```

## 🎯 Quick Start

### Basic Video Dubbing
```bash
# Dub a video to Spanish
python main.py --input sample_video.mp4 --output dubbed_spanish.mp4 --target-language es

# Dub with voice cloning
python main.py --input sample_video.mp4 --output dubbed_french.mp4 --target-language fr \
               --speaker-reference reference_voice.wav --enable-voice-cloning
```

### Live Webcam Processing
```bash
# Process live webcam stream to German
python main.py --live --target-language de --webcam-source 0
```

### High-Quality Processing
```bash
# Use larger models for better quality
python main.py --input sample_video.mp4 --output dubbed_japanese.mp4 --target-language ja \
               --whisper-model medium --translation-model facebook/nllb-200-distilled-600M
```

## 📖 Detailed Usage

### Command Line Arguments

```bash
python main.py [OPTIONS]

Input/Output:
  --input, -i PATH          Input video file path
  --output, -o PATH         Output video file path
  --live                    Process live webcam stream

Language Settings:
  --target-language, -t     Target language code (required)
  --source-language, -s     Source language code (auto-detect if not specified)

Model Settings:
  --whisper-model           Whisper model size [tiny|base|small|medium|large]
  --translation-model       Translation model name
  --tts-model              TTS model name

Processing Settings:
  --chunk-duration         Video chunk duration in seconds (default: 2.0)
  --device                 Device [auto|cpu|cuda] (default: auto)

Voice Cloning:
  --enable-voice-cloning   Enable voice cloning
  --speaker-reference      Path to reference speaker audio

Live Stream:
  --webcam-source          Webcam source index (default: 0)

Utilities:
  --list-languages         List supported languages
  --list-models           List available models
```

### Supported Languages

The system supports 100+ languages including:
- **European**: English (en), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt), Russian (ru)
- **Asian**: Japanese (ja), Korean (ko), Chinese (zh), Hindi (hi), Thai (th)
- **Others**: Arabic (ar), Hebrew (he), Turkish (tr), Polish (pl), Dutch (nl)

Run `python main.py --list-languages` to see the complete list.

## 🏗️ Architecture

The system uses a modular pipeline architecture:

```
Input Video → Chunking → Transcription → Translation → TTS → Lip-Sync → Output
     ↓           ↓           ↓            ↓         ↓        ↓
  Video File  2s Chunks   Whisper    M2M100/NLLB  Coqui    Wav2Lip
```

### Components

1. **Video Processor**: Handles video chunking and audio extraction
2. **Transcription**: OpenAI Whisper for speech-to-text
3. **Translation**: M2M100 or NLLB for text translation
4. **TTS Engine**: Coqui TTS for text-to-speech synthesis
5. **Lip-Sync**: Wav2Lip for realistic lip synchronization
6. **Pipeline Orchestrator**: Manages the complete workflow

## 🔧 Configuration

### Model Selection

**Whisper Models** (Transcription):
- `tiny`: Fastest, lowest accuracy (~39 MB)
- `base`: Balanced speed/accuracy (~74 MB)
- `small`: Better accuracy (~244 MB)
- `medium`: High accuracy (~769 MB)
- `large`: Best accuracy (~1550 MB)

**Translation Models**:
- `facebook/m2m100_418M`: Good balance, 418M parameters
- `facebook/nllb-200-distilled-600M`: Better quality, 600M parameters

**TTS Models**:
- `tts_models/en/ljspeech/tacotron2-DDC`: Standard English
- `tts_models/multilingual/multi-dataset/your_tts`: Multilingual with voice cloning

### Performance Optimization

1. **GPU Acceleration**: Ensure CUDA is available
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Chunk Duration**: Smaller chunks = lower latency, higher overhead
   - Real-time: 1-2 seconds
   - Batch processing: 3-5 seconds

3. **Model Selection**: Balance quality vs speed
   - Fast: tiny + m2m100_418M
   - Balanced: base + m2m100_418M
   - High Quality: medium + nllb-200

## 📁 Project Structure

```
vidsimplify_cloning/
├── main.py                 # Main application entry point
├── example.py              # Example usage scripts
├── dubbing_pipeline.py     # Main pipeline orchestrator
├── video_processor.py      # Video chunking and processing
├── transcription.py        # Whisper transcription module
├── translation.py          # Translation engine
├── tts_engine.py           # Text-to-speech synthesis
├── lipsync.py              # Wav2Lip integration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🐛 Troubleshooting

### Common Issues

1. **CUDA Out of Memory**:
   - Reduce chunk duration: `--chunk-duration 1.0`
   - Use smaller models: `--whisper-model tiny`
   - Process fewer chunks in parallel

2. **Wav2Lip Not Found**:
   - Ensure Wav2Lip is cloned and `inference.py` is in the main directory
   - Check that the model file exists: `models/wav2lip_gan.pth`

3. **FFmpeg Not Found**:
   - Install FFmpeg system-wide
   - Add to PATH environment variable

4. **Slow Processing**:
   - Ensure GPU is being used: `--device cuda`
   - Use smaller models for faster processing
   - Reduce video resolution

### Performance Tips

1. **For Real-time Processing**:
   - Use `tiny` Whisper model
   - Set chunk duration to 1-2 seconds
   - Ensure GPU acceleration

2. **For High Quality**:
   - Use `medium` or `large` Whisper model
   - Use NLLB translation model
   - Increase chunk duration to 3-5 seconds

3. **For Voice Cloning**:
   - Provide high-quality reference audio (16kHz, mono)
   - Use longer reference samples (5+ seconds)
   - Ensure reference speaker matches target language

## 📊 Performance Benchmarks

| Model Size | Chunk Duration | Processing Time | Quality |
|------------|----------------|-----------------|---------|
| tiny       | 2.0s           | ~0.5s/chunk     | Good    |
| base       | 2.0s           | ~1.0s/chunk     | Better  |
| medium     | 2.0s           | ~2.5s/chunk     | High    |
| large      | 2.0s           | ~4.0s/chunk     | Best    |

*Benchmarks on RTX 3080 GPU with 1080p video*

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Facebook M2M100](https://github.com/pytorch/fairseq) for translation
- [Coqui TTS](https://github.com/coqui-ai/TTS) for text-to-speech
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) for lip-sync
- [Transformers](https://github.com/huggingface/transformers) for model loading