"""
ADK Web Entry Point

ADK web looks for 'root_agent' in this file.
Run from project root: adk web video_gen_agent --port 8000
"""

from google.adk.agents import Agent
from google.adk.tools import load_memory  # ADK built-in for learning
from video_gen_agent.config import config


# Simple agent with tools - no complex imports to avoid circular issues
def search_pexels_videos(query: str, count: int = 5) -> dict:
    """Search Pexels for stock videos."""
    from video_gen_agent.tools.pexels_tool import search_pexels_videos as _search
    return _search(query=query, count=count)


def download_pexels_video(video_url: str, video_id: str) -> dict:
    """Download a Pexels video."""
    from video_gen_agent.tools.pexels_tool import download_pexels_video as _download
    return _download(video_url=video_url, video_id=video_id)


def search_pixabay_media(query: str, media_type: str = "video", count: int = 5) -> dict:
    """Search Pixabay for videos or images."""
    from video_gen_agent.tools.pixabay_tool import search_pixabay_media as _search
    return _search(query=query, media_type=media_type, count=count)


def download_pixabay_media(media_url: str, media_id: str, media_type: str = "video") -> dict:
    """Download Pixabay media."""
    from video_gen_agent.tools.pixabay_tool import download_pixabay_media as _download
    return _download(media_url=media_url, media_id=media_id, media_type=media_type)


def generate_voiceover(text: str, voice_style: str = "neutral") -> dict:
    """Generate voiceover from text using AI TTS."""
    from video_gen_agent.tools.tts_tool import generate_voiceover as _generate
    return _generate(text=text, voice_style=voice_style)


async def compose_video(
    video_clips: list[str],
    audio_path: str,
    output_name: str,
    video_format: str = "horizontal",
    transitions: str = "crossfade",
    tool_context = None
) -> dict:
    """
    Compose final video from clips and audio.
    
    Args:
        video_clips: List of paths to video clips to concatenate.
        audio_path: Path to the audio file for voiceover.
        output_name: Name for the output video file (without extension).
        video_format: Format - 'horizontal' (16:9) or 'vertical' (9:16).
        transitions: Transition type - 'none', 'crossfade', or 'fade'.
        tool_context: ADK tool context (injected automatically).
    
    Returns:
        A dictionary with 'status', 'file_path' to the final video, and 'duration'.
    """
    from video_gen_agent.tools.video_editor_tool import compose_video as _compose
    
    result = _compose(
        video_clips=video_clips,
        audio_path=audio_path,
        output_name=output_name,
        video_format=video_format,
        transitions=transitions
    )
    
    # Save video as ADK artifact for UI display
    if result.get("status") == "success" and tool_context:
        try:
            import os
            from google.genai import types
            
            file_path = result.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    video_bytes = f.read()
                
                video_artifact = types.Part.from_bytes(
                    data=video_bytes,
                    mime_type="video/mp4"
                )
                
                artifact_name = f"{output_name}.mp4"
                await tool_context.save_artifact(artifact_name, video_artifact)
                result["artifact_saved"] = True
                result["artifact_name"] = artifact_name
        except Exception as e:
            result["artifact_error"] = str(e)
    
    return result


def save_generation_rating(
    generation_topic: str,
    overall_score: int,
    script_score: int = 3,
    visuals_score: int = 3,
    audio_score: int = 3,
    pacing_score: int = 3,
    feedback: str = ""
) -> dict:
    """
    Save a rating for a video generation to help improve future videos.
    Call this after showing the completed video to record user feedback.
    
    Args:
        generation_topic: The topic/subject of the generated video.
        overall_score: Overall rating from 1 (poor) to 5 (excellent).
        script_score: Script/content quality rating 1-5.
        visuals_score: Visual selection and quality rating 1-5.
        audio_score: Audio/voiceover quality rating 1-5.
        pacing_score: Pacing/timing quality rating 1-5.
        feedback: Optional text feedback about what to improve or what was great.
    
    Returns:
        A dictionary confirming the rating was saved with details.
    """
    # Store in database for persistent learning
    try:
        from video_gen_agent.memory.database import GenerationDatabase
        db = GenerationDatabase()
        
        # Find the latest generation for this topic
        generations = db.get_generation_history(limit=10)
        gen_id = None
        for gen in generations:
            if generation_topic.lower() in gen.get('topic', '').lower():
                gen_id = gen.get('id')
                break
        
        if gen_id:
            rating_id = db.save_rating(
                generation_id=gen_id,
                overall_score=overall_score,
                script_score=script_score,
                visuals_score=visuals_score,
                audio_score=audio_score,
                pacing_score=pacing_score,
                feedback=feedback
            )
            saved_to_db = True
        else:
            saved_to_db = False
            rating_id = None
    except Exception as e:
        saved_to_db = False
        rating_id = None
    
    return {
        "status": "success",
        "message": f"Rating saved for '{generation_topic}': {overall_score}/5",
        "rating_details": {
            "topic": generation_topic,
            "overall": overall_score,
            "script": script_score,
            "visuals": visuals_score,
            "audio": audio_score,
            "pacing": pacing_score,
            "feedback": feedback
        },
        "saved_to_database": saved_to_db,
        "rating_id": rating_id,
        "learning_note": "This rating will be used to improve future video generations!"
    }


def get_learned_preferences() -> dict:
    """
    Get learned preferences from past video generation ratings.
    Use this at the start of generation to apply what the user loved/disliked.
    
    Returns:
        A dictionary with learned preferences and improvement suggestions.
    """
    try:
        from video_gen_agent.memory.learning import LearningSystem
        learning = LearningSystem()
        
        analysis = learning.analyze_ratings()
        improvements = learning.get_improvement_suggestions()
        
        return {
            "status": "success",
            "has_history": analysis.get("total_ratings", 0) > 0,
            "total_ratings": analysis.get("total_ratings", 0),
            "category_averages": analysis.get("category_averages", {}),
            "patterns": analysis.get("patterns", []),
            "improvements": improvements,
            "apply_note": "Apply these learnings to make better videos!"
        }
    except Exception as e:
        return {
            "status": "no_history",
            "message": "No previous ratings found. Generate videos and rate them to enable learning!",
            "error": str(e)
        }


# Enhanced instruction with learning and rating guidance
INSTRUCTION = """You are a LEARNING video production agent that improves based on user feedback.

📐 USER OPTIONS - Parse these from the user's request:
1. ASPECT RATIO:
   - "horizontal", "landscape", "16:9", "YouTube" → video_format="horizontal" (default)
   - "vertical", "portrait", "9:16", "TikTok", "Reels", "Shorts" → video_format="vertical"
   
2. DURATION:
   - "30 seconds", "30s", "short" → 4-5 script segments
   - "60 seconds", "1 minute", "medium" → 6-8 script segments  
   - "90 seconds", "long" → 8-10 script segments
   - Default: 30-45 seconds (4-6 segments)

3. VOICE STYLE:
   - "energetic", "excited" → voice_style="energetic"
   - "calm", "relaxing" → voice_style="calm"
   - "professional", "formal" → voice_style="professional"
   - Default: voice_style="neutral"

If the user doesn't specify, ASK them:
"What format would you like?
📱 Vertical (TikTok/Reels/Shorts) or 🖥️ Horizontal (YouTube)?
⏱️ How long? (30s, 60s, or 90s)"

🧠 LEARNING FIRST:
Before starting ANY video generation, ALWAYS call get_learned_preferences() to check what the user 
has loved or disliked in past videos. Apply these learnings!

For example:
- If past ratings show low "pacing" scores → use slower transitions, longer clips
- If past ratings show low "visuals" scores → search with more specific terms
- If past ratings show low "audio" scores → use different voice styles
- If feedback mentioned specific improvements → apply them!

YOUR WORKFLOW:
1. LEARN: Call get_learned_preferences() first
2. PARSE: Extract aspect ratio, duration, voice style from user request
3. SCRIPT: Create video script with appropriate number of segments
4. MEDIA: Search and download stock footage for each [Visual]
5. AUDIO: Generate voiceover from combined [Narration] text  
6. COMPOSE: Assemble final video with clips and audio (use correct video_format!)
7. RATE: Ask the user to rate the video!

STEP-BY-STEP:
1. Always start with get_learned_preferences() to check past feedback

2. Parse user preferences from their request (or ask if not specified)

3. Create script with appropriate segments based on duration:
   [Visual: description for stock footage]
   [Narration: what voiceover says]

4. For each [Visual]:
   - Search Pexels (use search_pexels_videos)
   - Download best match (use download_pexels_video)

5. Combine narration text and call generate_voiceover with appropriate voice_style

6. Call compose_video with:
   - video_clips: list of downloaded video paths
   - audio_path: the voiceover file
   - output_name: descriptive name
   - video_format: "horizontal" or "vertical" based on user preference
   - transitions: "crossfade" (default) or "fade"

7. IMPORTANT: After showing the video, ASK the user to rate it!
   Say: "Please rate this video from 1-5! You can also tell me what you liked or want improved."
   When they give feedback, use save_generation_rating to record it.

RATING PROMPT (always ask after video):
"🎬 Video complete! How would you rate it?
- Overall score (1-5)?
- What did you love?
- What could be improved?

Your feedback helps me create better videos for you!"

Return the final video file path when complete, then prompt for rating."""


# This is what ADK web discovers
root_agent = Agent(
    name="video_generator",
    model="gemini-2.0-flash",
    description="Creates videos from topics using stock footage and AI voiceover. Learns from your feedback!",
    instruction=INSTRUCTION,
    tools=[
        load_memory,  # ADK built-in for cross-session memory
        get_learned_preferences,  # Custom learning retrieval
        search_pexels_videos,
        download_pexels_video,
        search_pixabay_media,
        download_pixabay_media,
        generate_voiceover,
        compose_video,
        save_generation_rating,  # For recording user feedback
    ],
)
