"""
Pexels API Tool for fetching free stock video footage.
API Documentation: https://www.pexels.com/api/documentation/
"""

import os
import requests
from pathlib import Path
from typing import Optional
from video_gen_agent.config import config


def search_pexels_videos(
    query: str,
    count: int = 5,
    orientation: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None
) -> dict:
    """
    Search for videos on Pexels matching the query.
    
    Args:
        query: Search term for videos (e.g., "nature", "city traffic")
        count: Number of videos to return (1-15, default 5)
        orientation: Filter by orientation - 'landscape', 'portrait', or 'square'
        min_duration: Minimum video duration in seconds
        max_duration: Maximum video duration in seconds
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - videos: List of video objects with id, url, duration, thumbnail
            - error_message: Error description if status is 'error'
    """
    api_key = config.pexels_api_key
    
    if not api_key:
        return {
            "status": "error",
            "error_message": "Pexels API key not configured. Set PEXELS_API_KEY in .env"
        }
    
    headers = {
        "Authorization": api_key
    }
    
    params = {
        "query": query,
        "per_page": min(count, 15),  # Pexels max is 15 per page
    }
    
    if orientation:
        params["orientation"] = orientation
    if min_duration:
        params["min_duration"] = min_duration
    if max_duration:
        params["max_duration"] = max_duration
    
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for video in data.get("videos", []):
            # Get the best quality video file
            video_files = video.get("video_files", [])
            hd_file = None
            sd_file = None
            
            for vf in video_files:
                if vf.get("quality") == "hd":
                    hd_file = vf
                elif vf.get("quality") == "sd":
                    sd_file = vf
            
            best_file = hd_file or sd_file or (video_files[0] if video_files else None)
            
            if best_file:
                videos.append({
                    "id": str(video["id"]),
                    "url": best_file.get("link"),
                    "width": best_file.get("width"),
                    "height": best_file.get("height"),
                    "duration": video.get("duration"),
                    "thumbnail": video.get("image"),
                    "photographer": video.get("user", {}).get("name", "Unknown"),
                    "source": "pexels"
                })
        
        return {
            "status": "success",
            "videos": videos,
            "total_results": data.get("total_results", len(videos))
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Pexels API request failed: {str(e)}"
        }


def download_pexels_video(
    video_url: str,
    video_id: str,
    output_dir: Optional[str] = None
) -> dict:
    """
    Download a video from Pexels given its URL.
    
    Args:
        video_url: Direct URL to the video file
        video_id: Pexels video ID (used for filename)
        output_dir: Directory to save the video (defaults to cache dir)
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - file_path: Local path to downloaded video
            - error_message: Error description if status is 'error'
    """
    if output_dir:
        save_dir = Path(output_dir)
    else:
        save_dir = config.cache_dir / "videos" / "pexels"
    
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension from URL
    ext = ".mp4"
    if "?" in video_url:
        url_path = video_url.split("?")[0]
    else:
        url_path = video_url
    
    if url_path.endswith(".mp4"):
        ext = ".mp4"
    elif url_path.endswith(".mov"):
        ext = ".mov"
    
    file_path = save_dir / f"pexels_{video_id}{ext}"
    
    # Check if already downloaded
    if file_path.exists():
        return {
            "status": "success",
            "file_path": str(file_path),
            "cached": True
        }
    
    try:
        response = requests.get(video_url, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return {
            "status": "success",
            "file_path": str(file_path),
            "cached": False
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Failed to download video: {str(e)}"
        }
