"""
Pixabay API Tool for fetching free stock videos and images.
API Documentation: https://pixabay.com/api/docs/
"""

import requests
from pathlib import Path
from typing import Optional, Literal
from video_gen_agent.config import config


def search_pixabay_media(
    query: str,
    media_type: Literal["video", "image"] = "video",
    count: int = 5,
    orientation: Optional[str] = None,
    category: Optional[str] = None
) -> dict:
    """
    Search for videos or images on Pixabay.
    
    Args:
        query: Search term (e.g., "ocean waves", "business meeting")
        media_type: 'video' or 'image'
        count: Number of results to return (1-20, default 5)
        orientation: Filter - 'horizontal', 'vertical', or 'all'
        category: Filter by category (e.g., 'nature', 'business', 'technology')
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - media: List of media objects with id, url, dimensions, etc.
            - error_message: Error description if status is 'error'
    """
    api_key = config.pixabay_api_key
    
    if not api_key:
        return {
            "status": "error",
            "error_message": "Pixabay API key not configured. Set PIXABAY_API_KEY in .env"
        }
    
    # Determine API endpoint based on media type
    if media_type == "video":
        base_url = "https://pixabay.com/api/videos/"
    else:
        base_url = "https://pixabay.com/api/"
    
    params = {
        "key": api_key,
        "q": query,
        "per_page": min(count, 20),  # Pixabay max is 200, but we limit to 20
        "safesearch": "true"
    }
    
    if orientation and orientation != "all":
        params["orientation"] = orientation
    if category:
        params["category"] = category
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        media_list = []
        hits = data.get("hits", [])
        
        for item in hits:
            if media_type == "video":
                # Get video files
                videos = item.get("videos", {})
                # Prefer medium quality for balance of size/quality
                video_file = videos.get("medium", videos.get("small", videos.get("tiny", {})))
                
                media_list.append({
                    "id": str(item["id"]),
                    "url": video_file.get("url"),
                    "width": video_file.get("width"),
                    "height": video_file.get("height"),
                    "duration": item.get("duration"),
                    "thumbnail": item.get("picture_id"),
                    "tags": item.get("tags", ""),
                    "user": item.get("user", "Unknown"),
                    "source": "pixabay",
                    "type": "video"
                })
            else:
                # Image
                media_list.append({
                    "id": str(item["id"]),
                    "url": item.get("largeImageURL", item.get("webformatURL")),
                    "width": item.get("imageWidth"),
                    "height": item.get("imageHeight"),
                    "thumbnail": item.get("previewURL"),
                    "tags": item.get("tags", ""),
                    "user": item.get("user", "Unknown"),
                    "source": "pixabay",
                    "type": "image"
                })
        
        return {
            "status": "success",
            "media": media_list,
            "total_results": data.get("totalHits", len(media_list))
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Pixabay API request failed: {str(e)}"
        }


def download_pixabay_media(
    media_url: str,
    media_id: str,
    media_type: Literal["video", "image"] = "video",
    output_dir: Optional[str] = None
) -> dict:
    """
    Download media (video or image) from Pixabay.
    
    Args:
        media_url: Direct URL to the media file
        media_id: Pixabay media ID (used for filename)
        media_type: 'video' or 'image'
        output_dir: Directory to save the file (defaults to cache dir)
    
    Returns:
        dict with:
            - status: 'success' or 'error'
            - file_path: Local path to downloaded file
            - error_message: Error description if status is 'error'
    """
    if output_dir:
        save_dir = Path(output_dir)
    else:
        subdir = "videos" if media_type == "video" else "images"
        save_dir = config.cache_dir / subdir / "pixabay"
    
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine extension
    ext = ".mp4" if media_type == "video" else ".jpg"
    if media_url:
        url_path = media_url.split("?")[0]
        for possible_ext in [".mp4", ".mov", ".jpg", ".png", ".webp"]:
            if url_path.endswith(possible_ext):
                ext = possible_ext
                break
    
    file_path = save_dir / f"pixabay_{media_id}{ext}"
    
    # Check if already downloaded
    if file_path.exists():
        return {
            "status": "success",
            "file_path": str(file_path),
            "cached": True
        }
    
    try:
        response = requests.get(media_url, stream=True, timeout=120)
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
            "error_message": f"Failed to download media: {str(e)}"
        }
