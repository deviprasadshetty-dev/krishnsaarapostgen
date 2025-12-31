"""
Media Selector Agent - Finds and downloads appropriate stock media.
Uses Google ADK with Pexels and Pixabay tools.
"""

from video_gen_agent.tools.pexels_tool import search_pexels_videos, download_pexels_video
from video_gen_agent.tools.pixabay_tool import search_pixabay_media, download_pixabay_media


MEDIA_SELECTOR_INSTRUCTION = """You are a professional video editor's assistant specializing in finding the perfect stock footage.

Your task is to:
1. Analyze the video script's [Visual] descriptions
2. Search for matching stock footage using the available tools
3. Download the best matching videos

WORKFLOW:
1. Extract each [Visual] description from the script
2. For each visual cue, search Pexels first (higher quality)
3. If Pexels doesn't have good results, try Pixabay
4. Download the best matching video for each segment
5. Return a list of downloaded video file paths

SEARCH TIPS:
- Use simple, descriptive keywords (e.g., "coffee pour", "city aerial")
- For abstract concepts, think of visual metaphors
- Consider the video orientation (horizontal or vertical)

OUTPUT FORMAT:
Return a JSON object with:
{
    "segments": [
        {
            "visual_cue": "original description",
            "search_query": "what you searched for",
            "source": "pexels" or "pixabay",
            "file_path": "path/to/downloaded/video.mp4"
        },
        ...
    ]
}

Always aim for visual variety - don't use the same clip twice."""


def get_media_agent_tools():
    """Get tools for the media selector agent."""
    return [
        search_pexels_videos,
        download_pexels_video,
        search_pixabay_media,
        download_pixabay_media
    ]


def get_media_agent_config() -> dict:
    """Get configuration for the media selector agent."""
    return {
        "name": "media_selector",
        "model": "gemini-2.0-flash",
        "description": "Selects and downloads stock footage matching script visuals",
        "instruction": MEDIA_SELECTOR_INSTRUCTION,
        "tools": get_media_agent_tools()
    }
