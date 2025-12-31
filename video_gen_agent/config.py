"""
Configuration management for the Video Generation Agent.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class VideoSettings:
    """Video output settings."""
    format: str = "horizontal"  # horizontal (16:9) or vertical (9:16)
    resolution: str = "1080p"
    fps: int = 30
    
    @property
    def dimensions(self) -> tuple[int, int]:
        """Get width, height based on format and resolution."""
        res_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "4k": (3840, 2160)
        }
        width, height = res_map.get(self.resolution, (1920, 1080))
        
        if self.format == "vertical":
            return (height, width)  # Swap for 9:16
        return (width, height)


@dataclass
class TTSSettings:
    """Text-to-Speech settings."""
    voice: str = "default"
    speed: float = 1.0
    language: str = "en-US"


@dataclass
class Config:
    """Main configuration class."""
    # API Keys
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))
    pixabay_api_key: str = field(default_factory=lambda: os.getenv("PIXABAY_API_KEY", ""))
    
    # Directories
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("CACHE_DIR", "cache")))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    
    # Settings
    video: VideoSettings = field(default_factory=VideoSettings)
    tts: TTSSettings = field(default_factory=TTSSettings)
    
    def __post_init__(self):
        """Create directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load video settings from env
        self.video.format = os.getenv("DEFAULT_VIDEO_FORMAT", "horizontal")
        self.video.resolution = os.getenv("DEFAULT_VIDEO_RESOLUTION", "1080p")
        self.video.fps = int(os.getenv("DEFAULT_FPS", "30"))
        
        # Load TTS settings from env
        self.tts.voice = os.getenv("TTS_VOICE", "default")
        self.tts.speed = float(os.getenv("TTS_SPEED", "1.0"))
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.google_api_key:
            errors.append("GOOGLE_API_KEY is required")
        if not self.pexels_api_key:
            errors.append("PEXELS_API_KEY is required")
        if not self.pixabay_api_key:
            errors.append("PIXABAY_API_KEY is required")
            
        return errors


# Global config instance
config = Config()
