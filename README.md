# Video Generation Agent

An autonomous AI agent that generates YouTube videos/reels from topics or scripts using Google ADK.

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the agent
python -m video_gen_agent.main --topic "Your Topic Here"
```

## Features

- 🎬 Generate videos from topics or scripts
- 🎥 Free stock footage from Pexels & Pixabay
- 🎙️ AI voiceover using Google Gemini TTS
- 🧠 Learning system that improves from ratings
- 📐 Support for vertical (9:16) and horizontal (16:9) formats

## API Keys Required

- **Google Gemini**: [Get API Key](https://aistudio.google.com/apikey)
- **Pexels**: [Get API Key](https://www.pexels.com/api/)
- **Pixabay**: [Get API Key](https://pixabay.com/api/docs/)

## License

MIT
