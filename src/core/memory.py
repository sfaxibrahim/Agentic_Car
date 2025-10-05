"""
Conversation memory management
"""
from langchain.memory import ConversationBufferWindowMemory
from config.settings import settings
from services.api_service import fetch_conversation_history


def setup_memory() -> ConversationBufferWindowMemory:
    """
    Setup conversation memory to keep last N exchanges
    
    Returns:
        ConversationBufferWindowMemory configured with settings
    """
    return ConversationBufferWindowMemory(
        k=settings.MEMORY_WINDOW,
        return_messages=True,
        memory_key="chat_history",
        output_key="output"
    )


def load_previous_history(memory: ConversationBufferWindowMemory, 
                         conv_id: str, 
                         access_token: str) -> None:
    """
    Load previous conversation history from Spring Boot API
    
    Args:
        memory: The conversation memory instance
        conv_id: Conversation ID
        access_token: Authorization token
    """
    messages = fetch_conversation_history(conv_id, access_token)
    
    if not messages:
        return
    
    for msg in messages:
        if msg['role'] == 'USER':
            memory.chat_memory.add_user_message(msg['content'])
        else:
            memory.chat_memory.add_ai_message(msg['content'])
    
    print(f"✅ Loaded {len(messages)} previous messages")