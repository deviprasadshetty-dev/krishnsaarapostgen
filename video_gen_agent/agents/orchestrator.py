"""
Main Orchestrator Agent - Coordinates the video generation pipeline.
Uses Google ADK FULLY - with native MemoryService, callbacks, state, and tools.

This implementation uses ADK's built-in features:
- MemoryService for cross-session memory
- PreloadMemoryTool to inject past learnings into agent context
- after_agent_callback to auto-save sessions to memory
- session.state for tracking generation progress
- output_key to save agent outputs to state
"""

import asyncio
import re
import json
from typing import Optional
from pathlib import Path

from google.adk.agents import Agent, SequentialAgent, LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.tools import load_memory
from google.genai.types import Content, Part

from video_gen_agent.config import config


# =============================================================================
# ADK CALLBACKS - Using ADK's native callback system
# =============================================================================

async def before_agent_callback(callback_context):
    """
    Before agent callback - Inject learned preferences into context.
    Uses ADK's callback system to modify behavior before agent runs.
    """
    # Access session state to check for learned preferences
    state = callback_context.state
    
    # Log the generation start
    print(f"🚀 Agent starting: {callback_context.agent_name}")
    
    # If we have learned preferences from past sessions, they'll be in memory
    # and injected via PreloadMemoryTool or load_memory tool
    
    # Track generation step in state
    state["generation_step"] = "starting"
    
    return None  # Continue with normal agent execution


async def after_agent_callback(callback_context):
    """
    After agent callback - Auto-save session to memory for learning.
    Uses ADK's callback system to persist data after agent completes.
    """
    # Access the memory service from invocation context
    invocation_context = callback_context._invocation_context
    
    if invocation_context.memory_service:
        # Auto-save this session to memory for future learning
        try:
            await invocation_context.memory_service.add_session_to_memory(
                invocation_context.session
            )
            print("💾 Session saved to memory for learning")
        except Exception as e:
            print(f"⚠️ Could not save to memory: {e}")
    
    # Update state to mark completion
    callback_context.state["generation_step"] = "completed"
    
    return None  # Use the agent's response as-is


async def after_tool_callback(callback_context, tool_name: str, tool_result: dict):
    """
    After tool callback - Track tool usage in state.
    Uses ADK's callback system to observe tool executions.
    """
    # Track which tools were used in this session
    state = callback_context.state
    
    if "tools_used" not in state:
        state["tools_used"] = []
    
    state["tools_used"].append({
        "tool": tool_name,
        "success": tool_result.get("status") == "success" if isinstance(tool_result, dict) else True
    })
    
    return None  # Use tool result as-is


# =============================================================================
# TOOL DEFINITIONS (with proper ADK docstrings)
# =============================================================================

def search_pexels_videos(query: str, count: int = 5, orientation: str = "landscape") -> dict:
    """
    Search for stock videos on Pexels matching a search query.
    
    Args:
        query: Search term for finding videos (e.g., "coffee pour", "city aerial").
        count: Number of videos to return, between 1 and 15.
        orientation: Video orientation - 'landscape', 'portrait', or 'square'.
    
    Returns:
        A dictionary with 'status', 'videos' list with id, url, duration, thumbnail.
    """
    from video_gen_agent.tools.pexels_tool import search_pexels_videos as _search
    return _search(query=query, count=count, orientation=orientation)


def download_pexels_video(video_url: str, video_id: str) -> dict:
    """
    Download a video from Pexels to local storage.
    
    Args:
        video_url: The direct URL to the video file from Pexels.
        video_id: The Pexels video ID for naming the file.
    
    Returns:
        A dictionary with 'status' and 'file_path' to the downloaded video.
    """
    from video_gen_agent.tools.pexels_tool import download_pexels_video as _download
    return _download(video_url=video_url, video_id=video_id)


def search_pixabay_media(query: str, media_type: str = "video", count: int = 5) -> dict:
    """
    Search for videos or images on Pixabay.
    
    Args:
        query: Search term for finding media (e.g., "nature", "technology").
        media_type: Type of media - 'video' or 'image'.
        count: Number of results to return, between 1 and 20.
    
    Returns:
        A dictionary with 'status', 'media' list containing id, url, dimensions.
    """
    from video_gen_agent.tools.pixabay_tool import search_pixabay_media as _search
    return _search(query=query, media_type=media_type, count=count)


def download_pixabay_media(media_url: str, media_id: str, media_type: str = "video") -> dict:
    """
    Download media from Pixabay to local storage.
    
    Args:
        media_url: The direct URL to the media file.
        media_id: The Pixabay media ID for naming the file.
        media_type: Type of media - 'video' or 'image'.
    
    Returns:
        A dictionary with 'status' and 'file_path' to the downloaded file.
    """
    from video_gen_agent.tools.pixabay_tool import download_pixabay_media as _download
    return _download(media_url=media_url, media_id=media_id, media_type=media_type)


def generate_voiceover(text: str, voice_style: str = "neutral") -> dict:
    """
    Generate audio voiceover from text using AI text-to-speech.
    
    Args:
        text: The complete narration text to convert to speech.
        voice_style: Speaking style - 'neutral', 'energetic', 'calm', or 'professional'.
    
    Returns:
        A dictionary with 'status', 'file_path' to the audio, and 'duration' in seconds.
    """
    from video_gen_agent.tools.tts_tool import generate_voiceover as _generate
    return _generate(text=text, voice_style=voice_style)


def compose_video(
    video_clips: list[str],
    audio_path: str,
    output_name: str,
    video_format: str = "horizontal",
    transitions: str = "crossfade"
) -> dict:
    """
    Compose a final video from multiple video clips and an audio track.
    
    Args:
        video_clips: List of file paths to video clips to concatenate.
        audio_path: Path to the audio file for the voiceover.
        output_name: Name for the output video file (without extension).
        video_format: Format - 'horizontal' (16:9) or 'vertical' (9:16).
        transitions: Transition type - 'none', 'crossfade', or 'fade'.
    
    Returns:
        A dictionary with 'status', 'file_path' to the final video, and 'duration'.
    """
    from video_gen_agent.tools.video_editor_tool import compose_video as _compose
    config.video.format = video_format
    return _compose(
        video_clips=video_clips,
        audio_path=audio_path,
        output_name=output_name,
        video_format=video_format,
        transitions=transitions
    )


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
    The agent can call this to record user feedback for learning.
    
    Args:
        generation_topic: The topic/subject of the generated video.
        overall_score: Overall rating from 1 (poor) to 5 (excellent).
        script_score: Script quality rating 1-5.
        visuals_score: Visual selection quality rating 1-5.
        audio_score: Audio/voiceover quality rating 1-5.
        pacing_score: Pacing/timing quality rating 1-5.
        feedback: Optional text feedback about what to improve.
    
    Returns:
        A dictionary with 'status' and 'message' confirming the rating was saved.
    """
    # This will be automatically saved to memory via the callback system
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
        }
    }


# =============================================================================
# AGENT INSTRUCTION - References memory for learned preferences
# =============================================================================

ORCHESTRATOR_INSTRUCTION = """You are a video production agent that creates engaging short-form videos.

IMPORTANT: Before starting, check if there's any relevant memory from past sessions.
If the load_memory tool returns past feedback or preferences, APPLY THEM to improve this video.

For example, if past feedback said "pacing was too fast", use longer transitions.
If past feedback said "visuals didn't match", search with more specific terms.

YOUR WORKFLOW:
1. SCRIPT: Create a video script with [Visual] and [Narration] markers
2. MEDIA: Search and download stock footage for each [Visual]
3. AUDIO: Generate voiceover from combined [Narration] text  
4. COMPOSE: Assemble final video with clips and audio

STEP-BY-STEP:
1. Create script with segments formatted as:
   [Visual: description for stock footage search]
   [Narration: what the voiceover says]

2. For each [Visual]:
   - Search Pexels first (use search_pexels_videos)
   - Download the best match (use download_pexels_video)
   - If no results, try Pixabay

3. Combine all [Narration] text and call generate_voiceover

4. Call compose_video with all downloaded video paths and the audio

ALWAYS return the final video file path when complete.

LEARNING: After generation, if the user provides feedback, use save_generation_rating
to record it. This helps improve future videos."""


# =============================================================================
# MAIN VIDEO GENERATION AGENT CLASS - Using ADK fully
# =============================================================================

class VideoGenerationAgent:
    """
    Video generation agent using Google ADK's FULL potential:
    - MemoryService for cross-session learning
    - Callbacks for automatic memory persistence
    - State for tracking generation progress
    - load_memory tool for retrieving past learnings
    """
    
    def __init__(self, mode: str = "single"):
        """
        Initialize the video generation agent with ADK services.
        
        Args:
            mode: 'single' (one orchestrator) or 'sequential' (multi-agent pipeline)
        """
        self.mode = mode
        self.app_name = "video_generator"
        
        # ADK Session Service - manages conversation sessions
        self.session_service = InMemorySessionService()
        
        # ADK Memory Service - stores cross-session knowledge for learning
        self.memory_service = InMemoryMemoryService()
        
        if mode == "sequential":
            self.agent = self._create_sequential_workflow()
        else:
            self.agent = self._create_single_agent()
        
        # Runner with BOTH session and memory services
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service  # ADK manages memory!
        )
    
    def _create_single_agent(self) -> Agent:
        """Create single orchestrator agent with ADK features."""
        return Agent(
            name="video_orchestrator",
            model="gemini-2.0-flash",
            description="Creates videos from topics using stock footage and AI voiceover",
            instruction=ORCHESTRATOR_INSTRUCTION,
            # All tools including ADK's load_memory for retrieving learnings
            tools=[
                load_memory,  # ADK built-in: retrieves relevant memories
                search_pexels_videos,
                download_pexels_video,
                search_pixabay_media,
                download_pixabay_media,
                generate_voiceover,
                compose_video,
                save_generation_rating,
            ],
            # output_key saves agent final response to session state
            output_key="last_generation_result",
            # ADK Callbacks for automatic behavior
            before_agent_callback=before_agent_callback,
            after_agent_callback=after_agent_callback,
        )
    
    def _create_sequential_workflow(self) -> SequentialAgent:
        """Create multi-agent pipeline with ADK SequentialAgent."""
        
        script_agent = LlmAgent(
            name="script_writer",
            model="gemini-2.0-flash",
            instruction="""Write a 30-60 second video script.
            Format: [Visual: description] followed by [Narration: text]
            Include 4-8 segments. Start with hook, end with CTA.""",
            output_key="generated_script",  # Saved to state automatically
        )
        
        media_agent = LlmAgent(
            name="media_selector",
            model="gemini-2.0-flash",
            instruction="""Find stock footage for each [Visual] in the script.
            Search Pexels first, then Pixabay. Download best matches.
            Return list of downloaded file paths.""",
            tools=[
                search_pexels_videos,
                download_pexels_video,
                search_pixabay_media,
                download_pixabay_media,
            ],
            output_key="downloaded_media",
        )
        
        assembler_agent = LlmAgent(
            name="video_assembler",
            model="gemini-2.0-flash",
            instruction="""Generate voiceover from script narration.
            Compose final video with clips and audio.
            Return the final video path.""",
            tools=[
                generate_voiceover,
                compose_video,
            ],
            output_key="final_video_path",
            after_agent_callback=after_agent_callback,  # Save to memory at end
        )
        
        return SequentialAgent(
            name="video_pipeline",
            sub_agents=[script_agent, media_agent, assembler_agent],
            description="Multi-stage video generation pipeline",
        )
    
    async def generate(
        self,
        topic_or_script: str,
        output_name: str = "generated_video",
        video_format: str = "horizontal",
        user_id: str = "default_user"
    ) -> dict:
        """
        Generate a video using ADK's full capabilities.
        
        Args:
            topic_or_script: Video topic or complete script
            output_name: Name for the output video file
            video_format: 'horizontal' (16:9) or 'vertical' (9:16)
            user_id: User identifier for session/memory tracking
        
        Returns:
            dict with generation results including video path
        """
        config.video.format = video_format
        
        session_id = f"gen_{output_name}"
        
        # Create session with initial state
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            state={
                "topic": topic_or_script,
                "output_name": output_name,
                "video_format": video_format,
                "generation_step": "initialized",
            }
        )
        
        prompt = f"""Create a video about: {topic_or_script}

Settings:
- Format: {video_format} ({'9:16' if video_format == 'vertical' else '16:9'})
- Output: {output_name}

First, use load_memory to check for any relevant past feedback or preferences.
Then complete all generation steps and return the final video path."""
        
        user_content = Content(
            parts=[Part(text=prompt)],
            role="user"
        )
        
        result = {
            "status": "processing",
            "topic": topic_or_script,
            "output_name": output_name,
            "video_format": video_format,
            "messages": [],
            "final_video_path": None,
            "session_state": {},
            "error": None
        }
        
        try:
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result["messages"].append(part.text)
                            
                            if ".mp4" in part.text.lower():
                                path_match = re.search(r'[\w/\\:\-\.]+\.mp4', part.text)
                                if path_match:
                                    result["final_video_path"] = path_match.group()
                
                if event.is_final_response():
                    result["status"] = "completed"
                    break
            
            # Get final session state (ADK managed)
            final_session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
            if final_session:
                result["session_state"] = dict(final_session.state)
                    
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    async def submit_rating(
        self,
        user_id: str,
        topic: str,
        overall: int,
        script: int = 3,
        visuals: int = 3,
        audio: int = 3,
        pacing: int = 3,
        feedback: str = ""
    ):
        """
        Submit a rating that gets saved to ADK's MemoryService.
        This rating will be retrieved in future sessions via load_memory.
        """
        session_id = f"rating_{topic[:20].replace(' ', '_')}"
        
        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            state={
                "rating_topic": topic,
                "rating_overall": overall,
                "rating_script": script,
                "rating_visuals": visuals,
                "rating_audio": audio,
                "rating_pacing": pacing,
                "rating_feedback": feedback,
            }
        )
        
        # Get session and add to memory
        session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if session:
            await self.memory_service.add_session_to_memory(session)
            return {"status": "success", "message": "Rating saved to memory"}
        
        return {"status": "error", "message": "Could not save rating"}


async def run_video_generation(
    topic: str,
    output_name: str = "generated_video",
    video_format: str = "horizontal",
    mode: str = "single"
) -> dict:
    """Convenience function to run video generation."""
    agent = VideoGenerationAgent(mode=mode)
    return await agent.generate(
        topic_or_script=topic,
        output_name=output_name,
        video_format=video_format
    )
