from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain.callbacks import StreamingStdOutCallbackHandler
import json
import os
from datetime import datetime

# Configuration
CONFIG = {
    "model_name": "mistral:latest",
    "memory_window": 5,  
    "history_file": "chat_history.json",
    "temperature": 0.7,
    "save_history": True
}

def initialize_llm():
    """Initialize the LLM with streaming"""
    return OllamaLLM(
        model=CONFIG["model_name"],
        callbacks=[StreamingStdOutCallbackHandler()],
        temperature=CONFIG["temperature"]
    )

def create_prompt():
    """Create conversation prompt template"""
    template = """You are a friendly, intelligent AI assistant having a natural conversation.

Guidelines:
- Be conversational and engaging, not robotic or formal
- Ask thoughtful follow-up questions when appropriate
- Show genuine curiosity about the user's interests
- Reference relevant parts of our conversation history
- Provide helpful, accurate information
- Admit when you don't know something
- Keep responses concise but informative

Recent conversation (last {memory_window} exchanges):
{history}

Current exchange:
Human: {input}
AI: """

    return PromptTemplate(
        input_variables=["history", "input","memory_window"],
        template=template,
        partial_variables={"memory_window": str(CONFIG["memory_window"])}
    )

def setup_memory():
    """Setup memory to keep last 5 exchanges"""
    return ConversationBufferWindowMemory(
        k=CONFIG["memory_window"],
        return_messages=True,
        memory_key="history"
    )

def load_previous_history(memory):
    """Load last 5 exchanges from previous sessions"""
    if not CONFIG["save_history"] or not os.path.exists(CONFIG["history_file"]):
        return
    
    try:
        with open(CONFIG["history_file"], 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # Load the last 5 exchanges into memory
        recent_exchanges = history_data.get('exchanges', [])[-CONFIG["memory_window"]:]
        
        for exchange in recent_exchanges:
            memory.chat_memory.add_user_message(exchange['human'])
            memory.chat_memory.add_ai_message(exchange['ai'])
        
        if recent_exchanges:
            print(f"📚 Loaded {len(recent_exchanges)} previous exchanges")
            
    except Exception as e:
        print(f"⚠️ Could not load history: {e}")

def save_exchange(human_input, ai_response):
    """Save exchange to history file"""
    if not CONFIG["save_history"]:
        return
    
    exchange = {
        "timestamp": datetime.now().isoformat(),
        "human": human_input,
        "ai": ai_response
    }
    
    try:
        history_file = CONFIG["history_file"]
        
        # Load existing or create new
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        else:
            history_data = {"exchanges": []}
        
        # Add new exchange
        history_data["exchanges"].append(exchange)
        
        # Keep only last 100 exchanges to prevent file bloat
        if len(history_data["exchanges"]) > 100:
            history_data["exchanges"] = history_data["exchanges"][-100:]
        
        # Save back
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"⚠️ Could not save exchange: {e}")

def main():
    """Main chatbot function"""
    print("🤖 Starting Enhanced Chatbot with 5-Message Memory")
    print("Type 'exit', 'quit', or 'bye' to end the conversation\n")
    
    # Initialize components
    llm = initialize_llm()
    prompt = create_prompt()
    memory = setup_memory()
    
    # Load previous conversation
    load_previous_history(memory)
    
    # Create chatbot
    chatbot = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt,
        verbose=False  # No debug messages
    )
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            # Check for exit
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n Goodbye!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Generate response with streaming
            print("\n🤖 AI: ", end="", flush=True)
            response = chatbot.predict(input=user_input)
            print()  # New line after response
            
            # Save exchange
            save_exchange(user_input, response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Conversation ended!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again...")
            continue

if __name__ == "__main__":
    main()