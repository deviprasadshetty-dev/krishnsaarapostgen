# Tools Module
"""
Custom tools for the Video Generation Agent.
- Pexels API for video footage
- Pixabay API for videos/images
- Gemini TTS for voiceover
- Video editor for composition
"""

from video_gen_agent.tools.pexels_tool import search_pexels_videos, download_pexels_video
from video_gen_agent.tools.pixabay_tool import search_pixabay_media, download_pixabay_media
from video_gen_agent.tools.tts_tool import generate_voiceover
from video_gen_agent.tools.video_editor_tool import compose_video, trim_video

__all__ = [
    "search_pexels_videos",
    "download_pexels_video",
    "search_pixabay_media",
    "download_pixabay_media",
    "generate_voiceover",
    "compose_video",
    "trim_video",
]
