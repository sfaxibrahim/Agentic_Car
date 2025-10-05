
import requests
from typing import List, Dict, Optional
from config.settings import settings


def api_headers(access_token: str) -> Dict[str, str]:
    """
    Generate authorization headers
    
    Args:
        access_token: JWT access token
        
    Returns:
        Dictionary with authorization headers
    """
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def fetch_conversation_history(conv_id: str, access_token: str) -> List[Dict]:
    """
    Fetch conversation history from Spring Boot API
    
    Args:
        conv_id: Conversation ID
        access_token: Authorization token
        
    Returns:
        List of message dictionaries
    """
    url = f"{settings.SPRING_API_URL}/api/conversations/{conv_id}/messages"
    
    try:
        resp = requests.get(url, headers=api_headers(access_token), timeout=5)
        
        if resp.status_code != 200:
            print(f"⚠️ Failed to fetch history: {resp.status_code}")
            return []
        
        return resp.json()
    
    except requests.RequestException as e:
        print(f"⚠️ Error fetching conversation history: {e}")
        return []


def save_message(conv_id: str, role: str, content: str, access_token: str) -> bool:
    """
    Save a message to Spring Boot API
    
    Args:
        conv_id: Conversation ID
        role: Message role (USER or ASSISTANT)
        content: Message content
        access_token: Authorization token
        
    Returns:
        True if successful, False otherwise
    """
    url = f"{settings.SPRING_API_URL}/api/conversations/{conv_id}/messages"
    
    try:
        resp = requests.post(
            url,
            json={"role": role, "content": content},
            headers=api_headers(access_token),
            timeout=5
        )
        
        if resp.status_code >= 400:
            print(f"⚠️ Failed to save message: {resp.status_code} - {resp.text}")
            return False
        
        return True
    
    except requests.RequestException as e:
        print(f"❌ Error saving message: {e}")
        return False


def save_exchange(conv_id: str, 
                 human_input: str, 
                 ai_response: str, 
                 access_token: str) -> None:
    """
    Save a complete exchange (user + assistant messages)
    
    Args:
        conv_id: Conversation ID
        human_input: User's message
        ai_response: Assistant's response
        access_token: Authorization token
    """
    # Save user message
    save_message(conv_id, "USER", human_input, access_token)
    
    # Save AI response
    save_message(conv_id, "ASSISTANT", ai_response, access_token)