"""
Search services for YouTube and Google
"""
import os
from typing import Optional
from serpapi import GoogleSearch
from config.settings import settings


def youtube_search(query: str) -> str:
    """
    Enhanced YouTube search that returns structured data for frontend embedding
    
    Args:
        query: Search query
        
    Returns:
        Formatted YouTube results with embed URLs
    """
    if not settings.SERPAPI_API_KEY:
        return "❌ YouTube search unavailable: SERPAPI_API_KEY not configured"
    
    try:
        print(f"🎬 Searching YouTube for: '{query}'")
        
        params = {
            "engine": "youtube",
            "search_query": query,
            "api_key": settings.SERPAPI_API_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        video_results = results.get("video_results", [])
        
        if not video_results:
            print("❌ No videos found")
            return f"No YouTube videos found for '{query}'"
        
        print(f"✅ Found {len(video_results)} videos, returning top 3")
        
        # Collect structured video data
        videos_data = []
        for video in video_results[:3]:
            video_url = video.get('link', '')
            video_id = ''
            
            # Extract video ID
            if 'youtube.com/watch?v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
            
            embed_url = f"https://www.youtube.com/embed/{video_id}" if video_id else ""
            
            videos_data.append({
                "id": video_id,
                "title": video.get('title', 'No title'),
                "channel": video.get('channel', {}).get('name', 'Unknown channel'),
                "embed_url": embed_url
            })
        
        # Build clean streaming text for frontend
        intro_text = f"Here are {len(videos_data)} videos about {query} that you might find helpful:"
        
        video_blocks = []
        for i, v in enumerate(videos_data, 1):
            video_block = (
                f"Video {i}: {v['title']}\n"
                f"Channel: {v['channel']}\n"
                f"[VIDEO_EMBED]{v['embed_url']}[/VIDEO_EMBED]"
            )
            video_blocks.append(video_block)
        
        # Combine with proper formatting
        result_text = intro_text + "\n\n" + "\n\n".join(video_blocks) + "\n\nEnjoy watching!"
        
        return result_text
    
    except Exception as e:
        print(f"❌ YouTube search failed: {e}")
        return f"❌ YouTube search error: {str(e)}"


def google_search(query: str) -> str:
    """
    Google search wrapper with formatted results
    
    Args:
        query: Search query
        
    Returns:
        Formatted Google search results
    """
    if not settings.SERPAPI_API_KEY:
        return "❌ Google search unavailable: SERPAPI_API_KEY not configured"
    
    try:
        print(f"🔍 Searching Google for: '{query}'")
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.SERPAPI_API_KEY,
            "num": 5
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])
        
        if not organic_results:
            print("❌ No results found")
            return f"No Google results found for '{query}'"
        
        print(f"✅ Found {len(organic_results)} results")
        
        # Format top 3 results
        formatted_results = []
        for i, result in enumerate(organic_results[:3], 1):
            title = result.get('title', 'No title')
            link = result.get('link', '#')
            snippet = result.get('snippet', 'No description available')
            
            result_info = (
                f"🔗 **Result {i}:** {title}\n"
                f"**URL:** {link}\n"
                f"**Description:** {snippet}"
            )
            
            formatted_results.append(result_info)
        
        final_result = (
            "🔍 **Google Search Results:**\n" + 
            "=" * 50 + "\n\n" + 
            "\n\n".join(formatted_results)
        )
        
        print("✅ Google search completed")
        return final_result
    
    except Exception as e:
        print(f"❌ Google search failed: {e}")
        return f"❌ Google search error: {str(e)}"