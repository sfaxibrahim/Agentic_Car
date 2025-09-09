from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.conversational_chat.base import ConversationalChatAgent
from langchain.agents import Tool
from langchain_community.utilities import SerpAPIWrapper
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS 
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from serpapi import GoogleSearch
from langchain_community.chat_models import ChatOllama 
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.prompts import PromptTemplate
from langchain import hub
import os
import glob
import json 
from datetime import datetime
import sys

Base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(Base_dir, '..', 'data', 'PDF')
DATA_DIR = os.path.abspath(DATA_DIR)

CONFIG = {
    "model_name": "mistral:latest",
    "memory_window": 5,
    "history_file": "chat_history.json",
    "save_history": True
}

# API Key - Make sure to set this
os.environ["SERPAPI_API_KEY"] = "4fa4884cf498f97235632e8773157f9454d5e02072f1ec0eef4deb1c0d915ad3" 

# Global variables
vector_store = None
bm25_retriever = None
pdf_texts = {}

def setup_memory():
    """Setup memory to keep last 5 exchanges"""
    return ConversationBufferWindowMemory(
        k=CONFIG["memory_window"],
        return_messages=True,
        memory_key="chat_history",
        output_key="output"
    )

def load_previous_history(memory):
    """Load last 5 exchanges from previous sessions"""
    if not CONFIG["save_history"] or not os.path.exists(CONFIG["history_file"]):
        return
    
    try:
        with open(CONFIG["history_file"], 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        recent_exchanges = history_data.get('exchanges', [])[-CONFIG["memory_window"]:]
        
        for exchange in recent_exchanges:
            memory.chat_memory.add_user_message(exchange['human'])
            memory.chat_memory.add_ai_message(exchange['ai'])
        
        if recent_exchanges:
            print(f"✅ Loaded {len(recent_exchanges)} previous exchanges")
            
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
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        else:
            history_data = {"exchanges": []}
        
        history_data["exchanges"].append(exchange)
        
        if len(history_data["exchanges"]) > 100:
            history_data["exchanges"] = history_data["exchanges"][-100:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"⚠️ Could not save exchange: {e}")

def setup_fast_rag():
    """Ultra-fast RAG setup - loads once, stores in memory"""
    global vector_store, bm25_retriever, pdf_texts
    
    if not os.path.exists(DATA_DIR):
        print(f"⚠️ PDF directory not found: {DATA_DIR}")
        print("Creating directory...")
        os.makedirs(DATA_DIR, exist_ok=True)
        print("Please add PDF files to this directory and restart.")
        return False
    
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    if not pdf_files:
        print(f"⚠️ No PDF files found in {DATA_DIR}")
        print("Please add PDF files to this directory for knowledge base functionality.")
        return False
    
    print(f"📚 Loading {len(pdf_files)} PDF files into memory...")
    all_docs = []
    
    for pdf_file in pdf_files:
        try:
            print(f"  📄 Loading: {os.path.basename(pdf_file)}")
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()
            
            full_text = " ".join([doc.page_content for doc in docs])
            pdf_texts[pdf_file] = full_text
            
            all_docs.extend(docs)
        except Exception as e:
            print(f"⚠️ Error loading {pdf_file}: {e}")
            continue
    
    if not all_docs:
        print("⚠️ No documents could be loaded")
        return False
    
    try:
        print("🔄 Processing documents...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(all_docs)
        
        print("🔄 Creating embeddings...")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        print("🔄 Setting up BM25 retriever...")
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 15
        
        print(f"✅ RAG system ready! Loaded {len(chunks)} chunks from {len(pdf_files)} PDFs")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up RAG system: {e}")
        return False

def fast_rag_search(query):
    """Hybrid RAG search with semantic + keyword results"""
    global vector_store, bm25_retriever
    
    print(f"🔍 Searching PDF knowledge base for: '{query}'")
    
    if vector_store is None or bm25_retriever is None:
        return "❌ RAG system not initialized. Please check if PDF files are loaded correctly."
    
    try:
        faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 15})
        ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[0.4, 0.6]
        )
        
        docs = ensemble.get_relevant_documents(query)
        if not docs:
            print("❌ No relevant information found in PDFs")
            return "The PDF documents do not contain specific information about this topic."
        
        print(f"✅ Found {len(docs)} relevant chunks, selecting top 3")
        
        final_docs = docs[:3]
        snippets = []
        for i, doc in enumerate(final_docs, 1):
            source = os.path.basename(doc.metadata.get('source', 'unknown.pdf'))
            page = doc.metadata.get('page', 'N/A')
            content = doc.page_content.strip()
            snippets.append(f"📄 [{source} - page {page}]\n{content}")
        
        return "\n\n".join(snippets)
        
    except Exception as e:
        return f"❌ Error searching documents: {str(e)}"

def youtube_search_fast(query):
    """Enhanced YouTube search with better formatting and real-time feedback"""
    if not os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY") == "your_serpapi_key_here":
        return "❌ YouTube search unavailable: SERPAPI_API_KEY not configured"
    
    try:
        print(f"🎬 Searching YouTube for: '{query}'")
        params = {
            "engine": "youtube",
            "search_query": query,
            "api_key": os.environ["SERPAPI_API_KEY"]
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        video_results = results.get("video_results", [])
        
        if not video_results:
            print("❌ No videos found")
            return f"No YouTube videos found for '{query}'"
        
        print(f"✅ Found {len(video_results)} videos, showing top 3")
        
        formatted_results = []
        for i, video in enumerate(video_results[:3], 1):
            title = video.get('title', 'No title')
            link = video.get('link', '#')
            duration = video.get('duration', 'Duration not available')
            channel = video.get('channel', {}).get('name', 'Unknown channel')
            views = video.get('views', 'Views not available')
            
            video_info = f"""🎥 **Video {i}:** {title}
👤 **Channel:** {channel}
⏱️ **Duration:** {duration}
👀 **Views:** {views}
🔗 **Link:** {link}"""
            
            formatted_results.append(video_info)
        
        result = "\n🎬 **YouTube Search Results:**\n" + "="*50 + "\n\n" + "\n\n".join(formatted_results)
        return result
        
    except Exception as e:
        print(f"❌ YouTube search failed: {e}")
        return f"❌ YouTube search error: {str(e)}"

def google_search_wrapper(query):
    """Google search wrapper with real-time feedback"""
    if not os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY") == "your_serpapi_key_here":
        return "❌ Google search unavailable: SERPAPI_API_KEY not configured"
    
    try:
        print(f"🌐 Searching Google for: '{query}'")
        google_search = SerpAPIWrapper()
        result = google_search.run(query)
        print("✅ Google search completed")
        return result
    except Exception as e:
        print(f"❌ Google search failed: {e}")
        return f"❌ Google search error: {str(e)}"

# Enhanced Tools with better descriptions
tools = [
    Tool(
        name="PDF_Knowledge_Base",
        func=fast_rag_search,
        description="""Search the automotive PDF knowledge base. Use this FIRST for:
        - Car maintenance, repair procedures, troubleshooting
        - Buying guides, vehicle recommendations
        - Technical specifications, features, comparisons  
        - General automotive knowledge and how things work
        - Safety tips, best practices
        Input should be a clear question about automotive topics."""
    ),
    Tool(
        name="YouTube_Search",
        func=youtube_search_fast,
        description="""Search YouTube for automotive videos. Use when user asks for:
        - Videos, visual demonstrations, tutorials
        - "Show me how to", "I want to see", "video"
        - Step-by-step visual guides
        Input should be search terms for automotive videos."""
    ),
    Tool(
        name="Google_Search", 
        func=google_search_wrapper,
        description="""Search Google for current information. Use for:
        - Current prices, dealership info, inventory
        - Latest news, recalls, new models
        - Real-time data, local services
        Input should be specific search terms."""
    )
]

def create_conversational_agent(memory):
    """Create a conversational ReAct agent with proper prompt template"""
    try:
        print("🧪 Testing Ollama connection...")
        
        # Create LLM with streaming
        llm = ChatOllama(
            model=CONFIG["model_name"], 
            temperature=0.1,
            verbose=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        
        
        # Try to get the standard ReAct prompt from hub
        try:
            prompt = hub.pull("hwchase17/react-chat")
            print("✅ Using standard ReAct prompt from hub")
        except:
            # Fallback: Create custom prompt template
            print("⚠️ Hub unavailable, using custom prompt")
            template = """You are an expert automotive assistant. Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT: 
- ALWAYS use PDF_Knowledge_Base FIRST for any automotive question
- Use YouTube_Search when user asks for videos or visual demonstrations
- Use Google_Search for current prices, news, or local information

Previous conversation:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

            prompt = PromptTemplate(
                input_variables=["tools", "tool_names", "chat_history", "input", "agent_scratchpad"],
                template=template
            )
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=4,
            return_intermediate_steps=True
        )
        
        return agent_executor
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        print("Please ensure:")
        print("1. Ollama is running: ollama serve")
        print(f"2. Model is pulled: ollama pull {CONFIG['model_name']}")
        raise

def get_bot_response(user_input: str) -> str:
    """API-friendly chatbot response generator"""
    memory = setup_memory()
    load_previous_history(memory)
    agent_executor = create_conversational_agent(memory)

    try:
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": memory.chat_memory.messages
        })
        if result and "output" in result:
            ai_response = result["output"]
            save_exchange(user_input, ai_response)
            return ai_response
        else:
            return "I'm having trouble processing your request."
    except Exception:
        return "An error occurred while generating the response."
        

# def main():
#     """Main function with initialization checks"""
#     print("🚀 Starting Enhanced Automotive Assistant...")
    
#     # Setup RAG system
#     rag_success = setup_fast_rag()
#     if not rag_success:
#         print("Continuing without PDF knowledge base...")
    
#     # Start chat
#     get_bot_response()

# if __name__ == "__main__":
#     main()