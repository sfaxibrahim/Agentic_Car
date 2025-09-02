from langchain.agents import initialize_agent, Tool, AgentType
from langchain_ollama import OllamaLLM
from langchain_community.utilities import SerpAPIWrapper
from langchain.memory import ConversationBufferMemory
import os

from serpapi import GoogleSearch

# API Key - replace with your actual key
os.environ["SERPAPI_API_KEY"] = "4fa4884cf498f97235632e8773157f9454d5e02072f1ec0eef4deb1c0d915ad3" 

# Initialize SerpAPI instances
google_search = SerpAPIWrapper()

def youtube_search_serpapi(query):
    """YouTube search using SerpAPI with proper implementation"""
    try:
        
        params = {
            "engine": "youtube",
            "search_query": query,
            "api_key": os.environ["SERPAPI_API_KEY"]
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract video results
        video_results = results.get("video_results", [])
        
        if not video_results:
            return f"No YouTube videos found for '{query}'"
        
        # Format the top 3 results
        formatted_results = []
        for i, video in enumerate(video_results[:3], 1):
            title = video.get('title', 'No title')
            channel = video.get('channel', {}).get('name', 'Unknown channel')
            link = video.get('link', '#')
            formatted_results.append(f"{i}. {title} - {channel} ({link})")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching YouTube: {str(e)}"

def google_search_wrapper(query):
    """Google search with consistent formatting"""
    try:
        result = google_search.run(query)
        return result
    except Exception as e:
        return f"Error with Google search: {str(e)}"

# Define Tools with better descriptions
tools = [
    Tool(
        name="Google_Search",
        func=google_search_wrapper,
        description="Use for factual information: prices, specifications, news, comparisons, technical data"
    ),
    Tool(
        name="YouTube_Search", 
        func=youtube_search_serpapi,
        description="Use when user asks for videos, reviews, visual content, demonstrations, or says 'show me', 'watch', 'video'"
    )
]

# Setup LLM
llm = OllamaLLM(model="mistral:latest")
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create agent with better configuration
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    max_iterations=3,
    handle_parsing_errors=True,
    early_stopping_method="generate"
)

def chat():
    """Main chat function"""
    print("🚗 Automotive Assistant Ready!")
    print("💡 Examples:")
    print("   'BMW X5 price' → Google Search")  
    print("   'Show me BMW X5 videos' → YouTube Search")
    print("   'Tesla Model 3 reviews' → Could use either tool")
    print("\nType 'quit' to exit\n")
    
    while True:
        user_input = input("🚗 You: ").strip()
        
        if not user_input:
            continue
            
        if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
            print("👋 Goodbye!")
            break
        
        print("-" * 50)
        try:
            response = agent.invoke({"input": user_input})
            print(f"\n🤖 Bot: {response['output']}\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try a different query or check your API key.\n")

if __name__ == "__main__":
    # Test tools first to ensure they work

    # Start chat
    chat()