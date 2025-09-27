"""
Setup script for the Video Dubbing and Lip-Sync System
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is 3.10+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def check_cuda():
    """Check if CUDA is available"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA available - {torch.cuda.get_device_name(0)}")
            return True
        else:
            print("⚠️  CUDA not available - will use CPU (slower)")
            return False
    except ImportError:
        print("⚠️  PyTorch not installed - cannot check CUDA")
        return False


def install_system_dependencies():
    """Install system dependencies based on OS"""
    system = platform.system().lower()
    
    if system == "linux":
        print("🐧 Detected Linux system")
        commands = [
            ("sudo apt update", "Updating package list"),
            ("sudo apt install -y ffmpeg python3-dev", "Installing FFmpeg and Python dev tools")
        ]
    elif system == "darwin":
        print("🍎 Detected macOS system")
        commands = [
            ("brew update", "Updating Homebrew"),
            ("brew install ffmpeg", "Installing FFmpeg")
        ]
    elif system == "windows":
        print("🪟 Detected Windows system")
        print("⚠️  Please manually install FFmpeg from https://ffmpeg.org/download.html")
        print("   Add FFmpeg to your PATH environment variable")
        return True
    else:
        print(f"⚠️  Unsupported system: {system}")
        return False
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True


def install_python_dependencies():
    """Install Python dependencies"""
    return run_command("pip install -r requirements.txt", "Installing Python dependencies")


def setup_wav2lip():
    """Setup Wav2Lip for lip-sync"""
    print("🎭 Setting up Wav2Lip...")
    
    # Check if Wav2Lip already exists
    if os.path.exists("Wav2Lip"):
        print("✅ Wav2Lip directory already exists")
    else:
        if not run_command("git clone https://github.com/Rudrabha/Wav2Lip.git", "Cloning Wav2Lip repository"):
            return False
    
    # Create models directory
    os.makedirs("models", exist_ok=True)
    
    # Download model if not exists
    model_path = "models/wav2lip_gan.pth"
    if not os.path.exists(model_path):
        if not run_command(
            f"wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth -O {model_path}",
            "Downloading Wav2Lip model"
        ):
            return False
    else:
        print("✅ Wav2Lip model already exists")
    
    # Copy inference script
    if os.path.exists("Wav2Lip/inference.py"):
        if not os.path.exists("inference.py"):
            run_command("cp Wav2Lip/inference.py ./", "Copying Wav2Lip inference script")
        else:
            print("✅ Wav2Lip inference script already exists")
    else:
        print("⚠️  Wav2Lip inference.py not found - you may need to copy it manually")
    
    return True


def create_sample_files():
    """Create sample files and directories"""
    print("📁 Creating sample files and directories...")
    
    # Create directories
    directories = ["output", "models", "temp"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Create sample video placeholder
    sample_video = "sample_video.mp4"
    if not os.path.exists(sample_video):
        print(f"⚠️  Please add your sample video file as: {sample_video}")
    
    # Create .gitignore
    gitignore_content = """
# Output files
output/
temp/
*.mp4
*.wav
*.avi
*.mov

# Model files
models/*.pth
models/*.pkl
models/*.bin

# Logs
*.log
dubbing.log

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content.strip())
    print("✅ Created .gitignore file")
    
    return True


def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    # Test Python imports
    try:
        import torch
        import transformers
        import whisper
        import cv2
        import librosa
        print("✅ Core dependencies imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test CUDA
    check_cuda()
    
    # Test main script
    if not run_command("python main.py --list-languages", "Testing main script"):
        return False
    
    return True


def main():
    """Main setup function"""
    print("🚀 Video Dubbing and Lip-Sync System Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install system dependencies
    if not install_system_dependencies():
        print("❌ System dependency installation failed")
        sys.exit(1)
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("❌ Python dependency installation failed")
        sys.exit(1)
    
    # Setup Wav2Lip
    if not setup_wav2lip():
        print("❌ Wav2Lip setup failed")
        sys.exit(1)
    
    # Create sample files
    if not create_sample_files():
        print("❌ Sample file creation failed")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("❌ Installation test failed")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📖 Next steps:")
    print("1. Add a sample video file named 'sample_video.mp4'")
    print("2. For voice cloning, add 'reference_voice.wav'")
    print("3. Run: python main.py --input sample_video.mp4 --output output/dubbed.mp4 --target-language es")
    print("4. Or try: python example.py")
    
    print("\n🔧 Quick test commands:")
    print("  python main.py --list-languages")
    print("  python main.py --list-models")
    print("  python example.py")


if __name__ == "__main__":
    main()
