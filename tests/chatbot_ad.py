from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory
from langchain.prompts import PromptTemplate
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.schema import HumanMessage, AIMessage
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration
CONFIG = {
    "model_name": "mistral:latest",
    "memory_window": 5,  # Keep last 5 exchanges
    "history_file": "chat_history.json",
    "max_history_entries": 100,
    "save_history": True
}

def initialize_llm():
    """Initialize the LLM with optimized settings"""
    return OllamaLLM(
        model=CONFIG["model_name"],
        callbacks=[StreamingStdOutCallbackHandler()],
        # Note: top_p, top_k, num_ctx might not be available for all Ollama models
        verbose=True
    )

def create_enhanced_prompt():
    """Create an enhanced prompt template with better conversation flow"""
    template = """You are a friendly, intelligent AI assistant having a natural conversation.

Guidelines:
- Be conversational and engaging, not robotic or formal
- Ask thoughtful follow-up questions when appropriate
- Show genuine curiosity about the user's interests
- Reference relevant parts of our conversation history
- Provide helpful, accurate information
- Admit when you don't know something
- Keep responses concise but informative

Recent conversation history (last {memory_window} exchanges):
{history}

Current exchange:
Human: {input}
AI: """

    return PromptTemplate(
        input_variables=["history", "input", "memory_window"],
        template=template,
        partial_variables={"memory_window": str(CONFIG["memory_window"])}
    )

def setup_memory_system(llm):
    """Setup dual memory system for robust conversation handling"""
    # Primary memory: keeps exact last N exchanges
    window_memory = ConversationBufferWindowMemory(
        k=CONFIG["memory_window"],
        return_messages=True,
        memory_key="history",
        human_prefix="Human",
        ai_prefix="AI"
    )
    
    # Secondary memory: summarizes older conversations
    summary_memory = ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=1500,
        return_messages=True,
        memory_key="summary",
        human_prefix="Human",
        ai_prefix="AI"
    )
    
    return window_memory, summary_memory

def load_previous_history(memory):
    """Load conversation history from file and populate memory"""
    if not CONFIG["save_history"]:
        return 0
        
    history_file = CONFIG["history_file"]  # Get filename from config
    if not os.path.exists(history_file):
        return 0
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # Load the last few exchanges into memory
        recent_exchanges = history_data.get('exchanges', [])[-CONFIG["memory_window"]:]
        
        for exchange in recent_exchanges:
            memory.chat_memory.add_user_message(exchange['human'])
            memory.chat_memory.add_ai_message(exchange['ai'])
        
        logger.info(f"Loaded {len(recent_exchanges)} previous exchanges")
        return len(recent_exchanges)
        
    except Exception as e:
        logger.warning(f"Could not load history: {e}")
        return 0

def save_exchange_to_history(human_input: str, ai_response: str):
    """Save individual exchange to persistent history"""
    if not CONFIG["save_history"]:
        return
    
    exchange = {
        "timestamp": datetime.now().isoformat(),
        "human": human_input,
        "ai": ai_response
    }
    
    try:
        history_file = CONFIG["history_file"]  # Get the filename from config
        
        # Load existing history or create new
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        else:
            history_data = {"exchanges": [], "metadata": {}}
        
        # Add new exchange
        history_data["exchanges"].append(exchange)
        
        # Keep only recent entries to prevent file bloat
        if len(history_data["exchanges"]) > CONFIG["max_history_entries"]:
            history_data["exchanges"] = history_data["exchanges"][-CONFIG["max_history_entries"]:]
        
        # Update metadata
        history_data["metadata"] = {
            "last_updated": datetime.now().isoformat(),
            "total_exchanges": len(history_data["exchanges"]),
            "memory_window": CONFIG["memory_window"]
        }
        
        # Save back to file
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Could not save exchange: {e}")

def get_conversation_stats(memory) -> Dict[str, Any]:
    """Get statistics about the current conversation"""
    messages = memory.chat_memory.messages
    return {
        "exchanges_in_memory": len(messages) // 2,
        "total_tokens_approx": sum(len(msg.content.split()) for msg in messages),
        "memory_window": CONFIG["memory_window"]
    }

def display_conversation_summary(memory, summary_memory):
    """Display a summary of the conversation"""
    stats = get_conversation_stats(memory)
    print(f"\n--- Conversation Summary ---")
    print(f"Exchanges in current memory: {stats['exchanges_in_memory']}")
    print(f"Approximate tokens: {stats['total_tokens_approx']}")
    print(f"Memory window: {stats['memory_window']} exchanges")
    
    # Try to get conversation summary
    try:
        if hasattr(summary_memory, 'predict_new_summary') and memory.chat_memory.messages:
            summary = summary_memory.predict_new_summary(memory.chat_memory.messages, "")
            print(f"Conversation themes: {summary[:200]}...")
    except Exception as e:
        logger.warning(f"Could not generate summary: {e}")
    
    print("--- End Summary ---\n")

def handle_special_commands(user_input: str, memory, summary_memory) -> bool:
    """Handle special commands like /help, /stats, /clear, etc."""
    user_input = user_input.strip().lower()
    
    if user_input in ['/help', '/h']:
        print("""
Available commands:
/help, /h          - Show this help
/stats, /s         - Show conversation statistics
/summary           - Show conversation summary
/clear             - Clear conversation memory
/history           - Show recent exchange history
/config            - Show current configuration
/exit, /quit, /bye - Exit the chat
        """)
        return True
    
    elif user_input in ['/stats', '/s']:
        stats = get_conversation_stats(memory)
        print(f"\nConversation Statistics:")
        print(f"- Exchanges in memory: {stats['exchanges_in_memory']}")
        print(f"- Approximate tokens: {stats['total_tokens_approx']}")
        print(f"- Memory window: {stats['memory_window']}")
        return True
    
    elif user_input == '/summary':
        display_conversation_summary(memory, summary_memory)
        return True
    
    elif user_input == '/clear':
        memory.clear()
        print("Conversation memory cleared!")
        return True
    
    elif user_input == '/history':
        messages = memory.chat_memory.messages
        print(f"\nRecent conversation history ({len(messages)//2} exchanges):")
        for i in range(0, len(messages), 2):
            if i+1 < len(messages):
                print(f"Human: {messages[i].content}")
                print(f"AI: {messages[i+1].content[:100]}...")
                print("-" * 40)
        return True
    
    elif user_input == '/config':
        print(f"\nCurrent Configuration:")
        for key, value in CONFIG.items():
            print(f"- {key}: {value}")
        return True
    
    return False

def validate_input(user_input: str) -> tuple[bool, str]:
    """Validate and clean user input"""
    if not user_input or user_input.isspace():
        return False, "Please enter a valid message."
    
    # Clean input
    cleaned_input = user_input.strip()
    
    # Check for extremely long input
    if len(cleaned_input) > 2000:
        return False, "Message too long. Please keep it under 2000 characters."
    
    return True, cleaned_input

def create_robust_chatbot():
    """Create and return a fully configured chatbot with enhanced features"""
    print("🤖 Initializing Enhanced Conversational AI Pipeline...")
    
    # Initialize components
    llm = initialize_llm()
    prompt = create_enhanced_prompt()
    window_memory, summary_memory = setup_memory_system(llm)
    
    # Load previous history
    loaded_exchanges = load_previous_history(window_memory)
    if loaded_exchanges > 0:
        print(f"📚 Loaded {loaded_exchanges} previous exchanges from history")
    
    # Create conversation chain
    chatbot = ConversationChain(
        llm=llm,
        memory=window_memory,
        prompt=prompt,
        verbose=False  # Set to False to hide "Finished chain" messages
    )
    
    return chatbot, window_memory, summary_memory

def run_conversation_loop():
    """Main conversation loop with enhanced error handling and features"""
    print("🚀 Starting Enhanced Conversational AI")
    print("Type '/help' for commands or '/exit' to quit\n")
    
    # Initialize chatbot
    chatbot, memory, summary_memory = create_robust_chatbot()
    
    conversation_count = 0
    
    try:
        while True:
            try:
                # Get user input
                user_input = input("\n🧑 You: ").strip()
                
                # Handle exit conditions
                if user_input.lower() in ['exit', 'quit', 'bye', '/exit', '/quit', '/bye']:
                    print("\n👋 Thanks for chatting! Goodbye!")
                    display_conversation_summary(memory, summary_memory)
                    break
                
                # Handle special commands
                if handle_special_commands(user_input, memory, summary_memory):
                    continue
                
                # Validate input
                is_valid, processed_input = validate_input(user_input)
                if not is_valid:
                    print(f"⚠️  {processed_input}")
                    continue
                
                # Generate response
                print("\n🤖 AI: ", end="", flush=True)
                try:
                    response = chatbot.predict(input=processed_input)
                    print()  # New line after streaming response
                    
                    # Save to persistent history
                    save_exchange_to_history(processed_input, response)
                    
                    # Update conversation stats
                    conversation_count += 1
                    
                except Exception as e:
                    logger.error(f"Error generating response: {e}")
                    print(f"\n❌ Sorry, I encountered an error: {e}")
                    print("Please try rephrasing your message.")
                    continue
                
            except KeyboardInterrupt:
                print("\n\n⏸️  Conversation paused. Type '/exit' to quit or continue chatting.")
                continue
            
            except Exception as e:
                logger.error(f"Unexpected error in conversation loop: {e}")
                print(f"\n❌ An unexpected error occurred: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Fatal error in conversation loop: {e}")
        print(f"\n💥 Fatal error: {e}")
    
    finally:
        print(f"\n📊 Session ended. Total exchanges: {conversation_count}")

def main():
    """Main entry point"""
    try:
        run_conversation_loop()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        print(f"💥 Fatal error: {e}")

if __name__ == "__main__":
    main()