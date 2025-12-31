"""
Google Gemini Text-to-Speech Tool for generating voiceovers.
Uses Gemini's audio generation capabilities.
"""

import os
import wave
import struct
from pathlib import Path
from typing import Optional
from video_gen_agent.config import config

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def generate_voiceover(
    text: str,
    output_name: Optional[str] = None,
    voice_style: str = "neutral",
    speaking_rate: float = 1.0
) -> dict:
    """
    Generate audio voiceover from text using Google Gemini TTS.
    
    Args:
        text: The script/text to convert to speech
        output_name: Name for the output file (without extension)
        voice_style: Style hint - 'neutral', 'energetic', 'calm', 'professional'
        speaking_rate: Speed multiplier (0.5 to 2.0, default 1.0)
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - file_path: Path to generated audio file
            - duration: Estimated duration in seconds
            - error_message: Error description if status is 'error'
    """
    if not GENAI_AVAILABLE:
        return {
            "status": "error",
            "error_message": "google-genai package not installed. Run: pip install google-genai"
        }
    
    api_key = config.google_api_key
    if not api_key:
        return {
            "status": "error",
            "error_message": "Google API key not configured. Set GOOGLE_API_KEY in .env"
        }
    
    # Setup output directory
    audio_dir = config.cache_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        output_path = audio_dir / f"{output_name}.wav"
    else:
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_path = audio_dir / f"voiceover_{text_hash}.wav"
    
    # Check if already generated
    if output_path.exists():
        # Estimate duration from file
        try:
            with wave.open(str(output_path), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
            return {
                "status": "success",
                "file_path": str(output_path),
                "duration": duration,
                "cached": True
            }
        except Exception:
            pass  # File might be corrupted, regenerate
    
    try:
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Build prompt with style instruction
        style_instructions = {
            "neutral": "Speak in a clear, neutral tone.",
            "energetic": "Speak with energy and enthusiasm, perfect for engaging content.",
            "calm": "Speak in a calm, relaxed, and soothing manner.",
            "professional": "Speak in a professional, authoritative tone."
        }
        
        style_prompt = style_instructions.get(voice_style, style_instructions["neutral"])
        full_prompt = f"{style_prompt}\n\nText to speak:\n{text}"
        
        # Generate audio using Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # Default voice
                        )
                    )
                )
            )
        )
        
        # Extract audio data
        audio_data = None
        sample_rate = 24000  # Default sample rate
        
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    audio_data = part.inline_data.data
                    if hasattr(part.inline_data, 'mime_type'):
                        # Parse sample rate from mime type if available
                        mime = part.inline_data.mime_type
                        if 'rate=' in mime:
                            try:
                                sample_rate = int(mime.split('rate=')[1].split(';')[0])
                            except (ValueError, IndexError):
                                pass
                    break
        
        if not audio_data:
            return {
                "status": "error",
                "error_message": "No audio data in Gemini response"
            }
        
        # Save as WAV file
        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        
        # Calculate duration
        duration = len(audio_data) / (sample_rate * 2)  # 2 bytes per sample
        
        return {
            "status": "success",
            "file_path": str(output_path),
            "duration": duration,
            "sample_rate": sample_rate,
            "cached": False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"TTS generation failed: {str(e)}"
        }


def estimate_speech_duration(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate speech duration for a given text.
    
    Args:
        text: The text to estimate
        words_per_minute: Average speaking rate (default 150 WPM)
    
    Returns:
        Estimated duration in seconds
    """
    words = len(text.split())
    minutes = words / words_per_minute
    return minutes * 60
