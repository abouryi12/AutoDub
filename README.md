# AutoDub 🎙️🔗

An automated video dubbing pipeline that transcribes, translates, and dubs YouTube videos using AI/ML technologies.

## 🎯 Overview

YouTube Auto Dub is a comprehensive Python pipeline that automatically:
1. **Downloads** YouTube videos and audio
2. **Transcribes** speech using Whisper AI
3. **Translates** text to target languages via Google Translate
4. **Synthesizes** speech using Edge TTS with natural voices
5. **Synchronizes** audio timing with original video
6. **Renders** final dubbed video with perfect lip-sync

## ✨ Features

### 🤖 AI-Powered Processing
- **Whisper ASR**: State-of-the-art speech transcription with high accuracy
- **Google Translate**: Reliable translation supporting 100+ languages
- **Edge TTS**: High-quality neural voices with natural prosody
- **Smart Chunking**: Intelligent audio segmentation for optimal TTS

### 🎬 Video Processing
- **Format Support**: MP4, WebM, AVI and more via yt-dlp
- **Quality Preservation**: Original video quality maintained
- **Audio Sync**: Precise timing alignment with original video
- **Gap Filling**: Automatic silence generation for seamless audio

### 🌍 Language Support
- **100+ Languages**: Comprehensive language coverage via Google Translate
- **Voice Selection**: Male/female voice options for most languages
- **Automatic Detection**: Smart language detection and voice mapping
- **Custom Voices**: Configurable voice preferences per language

### ⚡ Performance
- **GPU Acceleration**: CUDA support for faster Whisper processing
- **Caching System**: Intelligent caching to avoid re-downloads
- **Parallel Processing**: Optimized pipeline for faster execution
- **Memory Management**: Automatic cleanup and resource optimization

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **FFmpeg** installed and added to PATH
   - Windows: [Download FFmpeg](https://ffmpeg.org/download.html)
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

3. **Optional: CUDA** for GPU acceleration
   - Install [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
   - Install CUDA PyTorch: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

### Installation

```bash
# Clone the repository
git clone https://github.com/abouryi12/AutoDub.git
cd youtube-auto-dub

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python main.py --help
```

### 🌐 Web Application (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the web server
uvicorn backend.app:app --reload

# Open http://localhost:8000 in your browser
```

The web UI provides a professional interface with real-time progress tracking, dark/light mode, and one-click video download.

### Basic CLI Usage

```bash
# Basic dubbing to Spanish
python main.py "https://youtube.com/watch?v=VIDEO_ID" --lang es

# With female voice and GPU acceleration
python main.py "https://youtube.com/watch?v=VIDEO_ID" --lang fr --gender female --gpu

# Using browser authentication for private videos
python main.py "https://youtube.com/watch?v=VIDEO_ID" --lang ja --browser chrome

# Using cookies file
python main.py "https://youtube.com/watch?v=VIDEO_ID" --lang de --cookies cookies.txt
```

## 📖 Usage Guide

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `url` | YouTube video URL (required) | `"https://youtube.com/watch?v=VIDEO_ID"` |
| `--lang, -l` | Target language code | `--lang es` (Spanish) |
| `--gender, -g` | Voice gender | `--gender female` |
| `--browser, -b` | Browser for cookies | `--browser chrome` |
| `--cookies, -c` | Cookies file path | `--cookies cookies.txt` |
| `--gpu` | Use GPU acceleration | `--gpu` |

### Supported Languages

Popular language codes:
- `es` - Spanish
- `fr` - French  
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese
- `ar` - Arabic
- `hi` - Hindi
- `ru` - Russian
- `vi` - Vietnamese
- `th` - Thai
- And many more...

### Authentication Methods

For private or age-restricted videos:

#### Method 1: Browser Cookies (Recommended)
```bash
# Close browser first, then:
python main.py "URL" --lang es --browser chrome
```

#### Method 2: Cookies File
```bash
# Export cookies using browser extension, then:
python main.py "URL" --lang es --cookies cookies.txt
```

## 🏗️ Architecture

### Pipeline Stages

```
YouTube URL → Download → Transcribe → Chunk → Translate → TTS → Sync → Render → Output
```

### Core Components

- **`main.py`**: CLI interface and pipeline orchestration
- **`src/engines.py`**: AI/ML engines (Whisper, Translator, TTS)
- **`src/youtube.py`**: YouTube content downloading
- **`src/media.py`**: Audio/video processing with FFmpeg
- **`src/audio_separation.py`**: Demucs audio source separation
- **`src/speaker_diarization.py`**: Pyannote speaker identification
- **`src/googlev4.py`**: Google Translate integration
- **`src/core_utils.py`**: Shared utilities and exceptions

### AI Models Used

- **Whisper**: OpenAI's speech recognition model
- **Google Translate**: Web scraping for translation
- **Edge TTS**: Microsoft's neural text-to-speech
- **Demucs**: Meta's audio source separation
- **Pyannote.audio**: Speaker diarization

## 🛠️ Configuration

### Language Configuration

Edit `language_map.json` to customize voice mappings:

```json
{
  "es": {
    "name": "Spanish",
    "voices": {
      "female": "es-ES-ElviraNeural",
      "male": "es-ES-JorgeNeural"
    }
  }
}
```

### Audio Settings

Modify `src/engines.py` for audio parameters:

```python
SAMPLE_RATE = 24000      # Audio sample rate (Hz)
AUDIO_CHANNELS = 1       # Mono audio
ASR_MODEL = "base"       # Whisper model size
```

## 🐛 Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found
```
[!] CRITICAL: Missing dependencies: ffmpeg, ffprobe
```
**Solution**: Install FFmpeg and add to system PATH

#### 2. CUDA Errors
```
[!] ERROR: CUDA out of memory
```
**Solution**: Use CPU mode or reduce batch size
```bash
python main.py "URL" --lang es  # CPU mode
```

#### 3. Authentication Failed
```
[!] YouTube authentication failed
```
**Solution**: 
- Close browser completely before using `--browser`
- Export fresh cookies.txt file
- Check if video is public/accessible

#### 4. TTS Voice Not Available
```
[!] WARNING: TTS output file is very small
```
**Solution**: 
- Check language code is correct
- Try different gender option
- Some voices may be region-restricted

#### 5. Download Failures
```
[!] ERROR: yt-dlp extraction failed
```
**Solution**:
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check video URL is valid
- Use authentication for private videos

### Performance Optimization

#### For Faster Processing
```bash
# Use GPU acceleration
python main.py "URL" --lang es --gpu

# Use smaller Whisper model (faster but less accurate)
# Edit src/config.py: ASR_MODEL = "tiny"
```

#### For Better Quality
```bash
# Use larger Whisper model (slower but more accurate)
# Edit src/config.py: ASR_MODEL = "large"

# Higher quality audio (larger files)
# Edit src/config.py: SAMPLE_RATE = 44100
```

## 📁 Project Structure

```
youtube-auto-dub/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── language_map.json       # Language-to-voice mappings
├── README.md               # This file
├── backend/                # FastAPI web backend
│   ├── __init__.py
│   └── app.py              # API routes & SSE progress
├── frontend/               # Web UI
│   └── index.html          # Single-page application
├── styles/                 # CSS design system
│   └── main.css            # Dark/light themes & animations
├── scripts/                # Frontend JavaScript
│   └── app.js              # API client & UI logic
├── assets/                 # Branding & static assets
├── src/                    # Core pipeline source code
│   ├── engines.py          # AI/ML engines
│   ├── youtube.py          # YouTube downloader
│   ├── media.py            # Audio/video processing
│   ├── audio_separation.py # Demucs audio separation
│   ├── speaker_diarization.py # Pyannote speaker diarization
│   ├── googlev4.py         # Google Translate scraper
│   └── core_utils.py       # Shared utilities
├── .cache/                 # Downloaded YouTube content
├── output/                 # Final dubbed videos
└── temp/                   # Temporary processing files
```

## 🧪 Development

### Code Style

The project follows Google Style docstrings and includes:
- Comprehensive function documentation
- Type hints for all functions
- Error handling with descriptive messages
- TODO and NOTE comments for future improvements

### Future Roadmap

- [ ] Local LLM translation support
- [ ] 4K rendering profiles
- [ ] Voice cloning integration
- [ ] Batch processing capabilities
- [x] Web interface for easier usage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Dependencies License

Most dependencies are open-source:
- **PyTorch**: BSD/Apache 2.0
- **faster-whisper**: MIT
- **yt-dlp**: Unlicense
- **Edge TTS**: MIT (uses Microsoft service)
- **librosa**: ISC
- **demucs**: MIT
- **pyannote.audio**: MIT

## 🤝 Acknowledgments

- **OpenAI** for Whisper speech recognition
- **Microsoft** for Edge TTS neural voices
- **yt-dlp** team for YouTube downloading
- **Google** for Translate service
- **FFmpeg** team for media processing

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/abouryi12/AutoDub/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/abouryi12/AutoDub/discussions)

## 🔄 Changelog

### Version 1.0.0
- 🎉 Complete refactoring and consolidation
- 📝 Google Style docstrings throughout
- 🧹 Comprehensive code cleanup and optimization
- 💾 Enhanced memory management and GPU optimization
- 🌍 Improved language support and voice mapping
- 🎬 Advanced audio separation and speaker diarization
- � Subtitle generation and rendering support
- 🛠️ Unified logging system with clear prefixes
- 📖 Comprehensive documentation and troubleshooting

---

**Made with ❤️ for the AI Community**
