"""
Video Assembler Agent - Composes final video from clips and audio.
Uses TTS and video editor tools.
"""

from video_gen_agent.tools.tts_tool import generate_voiceover
from video_gen_agent.tools.video_editor_tool import compose_video, trim_video


ASSEMBLER_INSTRUCTION = """You are a professional video editor who assembles final videos.

Your task is to:
1. Extract the narration text from the script
2. Generate voiceover audio using the TTS tool
3. Compose the final video using the provided clips

WORKFLOW:
1. Extract all [Narration] lines from the script and combine them
2. Call generate_voiceover with the combined narration text
3. Use compose_video with the video clips and audio

VIDEO COMPOSITION GUIDELINES:
- Use crossfade transitions for smooth flow
- Match video duration to audio duration
- Maintain visual variety

OUTPUT FORMAT:
Return a JSON object with:
{
    "voiceover_path": "path/to/audio.wav",
    "voiceover_duration": 45.5,
    "final_video_path": "path/to/output.mp4",
    "final_duration": 45.5,
    "status": "success" or "error",
    "message": "description of what was done"
}"""


def get_assembler_agent_tools():
    """Get tools for the video assembler agent."""
    return [
        generate_voiceover,
        compose_video,
        trim_video
    ]


def get_assembler_agent_config() -> dict:
    """Get configuration for the video assembler agent."""
    return {
        "name": "video_assembler",
        "model": "gemini-2.0-flash",
        "description": "Assembles final video with voiceover and transitions",
        "instruction": ASSEMBLER_INSTRUCTION,
        "tools": get_assembler_agent_tools()
    }
