"""
Video Editor Tool using MoviePy 2.x for composing final videos.
Handles video composition, transitions, and audio overlay.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from video_gen_agent.config import config

try:
    # MoviePy 2.x imports
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
    MOVIEPY_VERSION = 2
except ImportError:
    try:
        # Fallback to MoviePy 1.x imports
        from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
        MOVIEPY_AVAILABLE = True
        MOVIEPY_VERSION = 1
    except ImportError:
        MOVIEPY_AVAILABLE = False
        MOVIEPY_VERSION = 0


def _resize_clip(clip, new_size):
    """Resize clip with version compatibility."""
    if MOVIEPY_VERSION == 2:
        return clip.resized(new_size)
    else:
        return clip.resize(newsize=new_size)


def _crop_clip(clip, x1, y1, x2, y2):
    """Crop clip with version compatibility."""
    if MOVIEPY_VERSION == 2:
        return clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    else:
        return clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)


def _subclip(clip, start, end):
    """Get subclip with version compatibility."""
    if MOVIEPY_VERSION == 2:
        return clip.subclipped(start, end)
    else:
        return clip.subclip(start, end)


def _loop_clip(clip, duration):
    """Loop clip with version compatibility."""
    if MOVIEPY_VERSION == 2:
        # MoviePy 2.x uses with_effects or just repeat the clip
        loops_needed = int(duration / clip.duration) + 1
        clips = [clip] * loops_needed
        looped = concatenate_videoclips(clips)
        return _subclip(looped, 0, duration)
    else:
        return clip.loop(duration=duration)


def _set_audio(clip, audio):
    """Set audio on clip with version compatibility."""
    if MOVIEPY_VERSION == 2:
        return clip.with_audio(audio)
    else:
        return clip.set_audio(audio)


def _fadein(clip, duration):
    """Apply fadein with version compatibility."""
    if MOVIEPY_VERSION == 2:
        try:
            from moviepy.video.fx import CrossFadeIn
            return clip.with_effects([CrossFadeIn(duration)])
        except ImportError:
            return clip  # Skip if not available
    else:
        return clip.fadein(duration)


def _fadeout(clip, duration):
    """Apply fadeout with version compatibility."""
    if MOVIEPY_VERSION == 2:
        try:
            from moviepy.video.fx import CrossFadeOut
            return clip.with_effects([CrossFadeOut(duration)])
        except ImportError:
            return clip
    else:
        return clip.fadeout(duration)


def compose_video(
    video_clips: list[str],
    audio_path: Optional[str] = None,
    output_name: str = "output",
    video_format: Optional[str] = None,
    transitions: Literal["none", "crossfade", "fade"] = "none",
    transition_duration: float = 0.5
) -> dict:
    """
    Compose a final video from multiple clips with audio overlay.
    
    Args:
        video_clips: List of paths to video files to concatenate
        audio_path: Path to audio file for voiceover (optional)
        output_name: Name for output file (without extension)
        video_format: 'horizontal' (16:9) or 'vertical' (9:16)
        transitions: Transition type between clips
        transition_duration: Duration of transitions in seconds
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - file_path: Path to final video
            - duration: Final video duration in seconds
    """
    if not MOVIEPY_AVAILABLE:
        return {
            "status": "error",
            "error_message": "moviepy not installed. Run: pip install moviepy"
        }
    
    if not video_clips:
        return {
            "status": "error",
            "error_message": "No video clips provided"
        }
    
    # Determine target dimensions
    fmt = video_format or config.video.format
    target_width, target_height = config.video.dimensions
    if fmt == "vertical":
        target_width, target_height = target_height, target_width
    
    fps = config.video.fps
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{output_name}.mp4"
    
    clips = []
    temp_clips = []
    
    try:
        # Load and process each clip
        for clip_path in video_clips:
            if not os.path.exists(clip_path):
                continue
                
            clip = VideoFileClip(clip_path)
            temp_clips.append(clip)
            
            # Resize to target dimensions
            clip = resize_clip_to_fill(clip, target_width, target_height)
            clips.append(clip)
        
        if not clips:
            return {
                "status": "error",
                "error_message": "No valid video clips could be loaded"
            }
        
        # Load audio if provided
        audio_duration = None
        audio_clip = None
        
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            temp_clips.append(audio_clip)
        
        # Adjust clip durations to match audio
        if audio_duration:
            clips = adjust_clips_to_duration(clips, audio_duration)
        
        # Concatenate clips
        if transitions == "fade" and len(clips) > 1:
            clips = [_fadein(c, transition_duration) if i > 0 else c 
                     for i, c in enumerate(clips)]
            clips = [_fadeout(c, transition_duration) if i < len(clips)-1 else c 
                     for i, c in enumerate(clips)]
        
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Add audio
        if audio_clip:
            # Trim video to match audio duration
            if final_video.duration > audio_duration:
                final_video = _subclip(final_video, 0, audio_duration)
            elif final_video.duration < audio_duration:
                final_video = _loop_clip(final_video, audio_duration)
            
            final_video = _set_audio(final_video, audio_clip)
        
        # Write output
        final_video.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None
        )
        
        duration = final_video.duration
        
        # Cleanup
        final_video.close()
        for clip in temp_clips:
            clip.close()
        
        return {
            "status": "success",
            "file_path": str(output_path),
            "duration": duration,
            "resolution": f"{target_width}x{target_height}"
        }
        
    except Exception as e:
        for clip in temp_clips:
            try:
                clip.close()
            except Exception:
                pass
        
        return {
            "status": "error",
            "error_message": f"Video composition failed: {str(e)}"
        }


def resize_clip_to_fill(clip, target_width: int, target_height: int):
    """Resize clip to fill target dimensions (crop if needed)."""
    clip_aspect = clip.w / clip.h
    target_aspect = target_width / target_height
    
    if clip_aspect > target_aspect:
        new_height = target_height
        new_width = int(clip_aspect * target_height)
    else:
        new_width = target_width
        new_height = int(target_width / clip_aspect)
    
    resized = _resize_clip(clip, (new_width, new_height))
    
    # Center crop to target
    x1 = (new_width - target_width) // 2
    y1 = (new_height - target_height) // 2
    x2 = x1 + target_width
    y2 = y1 + target_height
    
    return _crop_clip(resized, x1, y1, x2, y2)


def adjust_clips_to_duration(clips: list, total_duration: float) -> list:
    """Adjust clip durations to fit within total duration."""
    if not clips:
        return clips
    
    duration_per_clip = total_duration / len(clips)
    
    adjusted = []
    for clip in clips:
        if clip.duration > duration_per_clip:
            adjusted.append(_subclip(clip, 0, duration_per_clip))
        elif clip.duration < duration_per_clip:
            adjusted.append(_loop_clip(clip, duration_per_clip))
        else:
            adjusted.append(clip)
    
    return adjusted


def trim_video(
    video_path: str,
    start_time: float,
    end_time: float,
    output_name: Optional[str] = None
) -> dict:
    """Trim a video to specified duration."""
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "error_message": "moviepy not installed"}
    
    if not os.path.exists(video_path):
        return {"status": "error", "error_message": f"Video not found: {video_path}"}
    
    try:
        clip = VideoFileClip(video_path)
        trimmed = _subclip(clip, start_time, min(end_time, clip.duration))
        
        if output_name:
            output_path = config.cache_dir / "trimmed" / f"{output_name}.mp4"
        else:
            output_path = config.cache_dir / "trimmed" / f"trimmed_{Path(video_path).stem}.mp4"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        trimmed.write_videofile(str(output_path), codec="libx264", audio_codec="aac", logger=None)
        
        duration = trimmed.duration
        clip.close()
        trimmed.close()
        
        return {"status": "success", "file_path": str(output_path), "duration": duration}
        
    except Exception as e:
        return {"status": "error", "error_message": f"Trim failed: {str(e)}"}
