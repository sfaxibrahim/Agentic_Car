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
import queue
from langchain.callbacks.base import BaseCallbackHandler

Base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(Base_dir, '..', 'data', 'PDF')
DATA_DIR = os.path.abspath(DATA_DIR)
VECTORSTORE_PATH = os.path.join(Base_dir, '..', 'data', 'vector_store_faiss')
VECTORSTORE_PATH = os.path.abspath(VECTORSTORE_PATH)
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

# def setup_fast_rag():
#     """Ultra-fast RAG setup - loads once, stores in memory"""
#     global vector_store, bm25_retriever, pdf_texts
    
#     if not os.path.exists(DATA_DIR):
#         print(f"⚠️ PDF directory not found: {DATA_DIR}")
#         print("Creating directory...")
#         os.makedirs(DATA_DIR, exist_ok=True)
#         print("Please add PDF files to this directory and restart.")
#         return False
    
#     pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
#     if not pdf_files:
#         print(f"⚠️ No PDF files found in {DATA_DIR}")
#         print("Please add PDF files to this directory for knowledge base functionality.")
#         return False
    
#     print(f"📚 Loading {len(pdf_files)} PDF files into memory...")
#     all_docs = []
    
#     for pdf_file in pdf_files:
#         try:
#             print(f"  📄 Loading: {os.path.basename(pdf_file)}")
#             loader = PyPDFLoader(pdf_file)
#             docs = loader.load()
            
#             full_text = " ".join([doc.page_content for doc in docs])
#             pdf_texts[pdf_file] = full_text
            
#             all_docs.extend(docs)
#         except Exception as e:
#             print(f"⚠️ Error loading {pdf_file}: {e}")
#             continue
    
#     if not all_docs:
#         print("⚠️ No documents could be loaded")
#         return False
    
#     try:
#         print("🔄 Processing documents...")
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#         chunks = text_splitter.split_documents(all_docs)
        
#         print("🔄 Creating embeddings...")
#         embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#         vector_store = FAISS.from_documents(chunks, embeddings)
        
#         print("🔄 Setting up BM25 retriever...")
#         bm25_retriever = BM25Retriever.from_documents(chunks)
#         bm25_retriever.k = 15
        
#         print(f"✅ RAG system ready! Loaded {len(chunks)} chunks from {len(pdf_files)} PDFs")
#         return True
        
#     except Exception as e:
#         print(f"❌ Error setting up RAG system: {e}")
#         return False
def load_vectorstore():
    """Load FAISS vectorstore from disk if not already in memory."""
    global vector_store
    if vector_store is None:
        if os.path.exists(VECTORSTORE_PATH):
            print(f"📂 Loading FAISS vectorstore from: {VECTORSTORE_PATH}")
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

            vector_store = FAISS.load_local(
                VECTORSTORE_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("❌ No saved FAISS vectorstore found on disk.")
    return vector_store

def load_bm25():
    """Rebuild BM25 retriever from FAISS stored documents if needed."""
    global bm25_retriever, vector_store
    if bm25_retriever is None and vector_store is not None:
        print("🔄 Rebuilding BM25 retriever from FAISS docs...")
        # FAISS stores docs internally
        docs = vector_store.docstore._dict.values()
        bm25_retriever = BM25Retriever.from_documents(list(docs))
        bm25_retriever.k = 15
    return bm25_retriever

def fast_rag_search(query):
    """Hybrid RAG search with semantic + keyword results"""
    global vector_store, bm25_retriever
    
    print(f"🔍 Searching PDF knowledge base for: '{query}'")
    
    vector_store = load_vectorstore()
    bm25_retriever = load_bm25()    
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
    """Enhanced YouTube search that returns structured data for frontend embedding"""
    if not os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY") == "":
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
                 
        print(f"✅ Found {len(video_results)} videos, returning top 3")
                 
        # Collect structured video data
        videos_data = []
        for video in video_results[:3]:
            video_url = video.get('link', '')
            video_id = ''
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
            video_block = f"Video {i}: {v['title']}\nChannel: {v['channel']}\n[VIDEO_EMBED]{v['embed_url']}[/VIDEO_EMBED]"
            video_blocks.append(video_block)
        
        # Combine with proper formatting
        result_text = intro_text + "\n\n" + "\n\n".join(video_blocks) + "\n\nEnjoy watching!"
        
        return result_text
             
    except Exception as e:
        print(f"❌ YouTube search failed: {e}")
        return f"❌ YouTube search error: {str(e)}"

def google_search_wrapper(query):
    """Google search wrapper with real-time feedback"""
    if not os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY") == "your_serpapi_key_here":
        return "❌ Google search unavailable: SERPAPI_API_KEY not configured"
    
    try:
        print(f"Searching Google for: '{query}'")
        params={
            "engine": "google",
            "q": query,
            "api_key": os.environ["SERPAPI_API_KEY"],
            "num": 5
        }
        # google_search = SerpAPIWrapper()
        search=GoogleSearch(params)
        results=search.get_dict()
        organic_results = results.get("organic_results", [])
        print(f"✅ Found {len(organic_results)} results")
        formatted_results = []
        for i, result in enumerate(organic_results[:3], 1):
            title = result.get('title', 'No title')
            link = result.get('link', '#')
            snippet = result.get('snippet', 'No description available')
            
            result_info = f"""🔗 **Result {i}:** {title}
**URL:** {link}
**Description:** {snippet}"""
            
            formatted_results.append(result_info)
        
        final_result = "🔍 **Google Search Results:**\n" + "="*50 + "\n\n" + "\n\n".join(formatted_results)
        
        print("✅ Google search completed")
        return final_result


        # result = google_search.run(query)
        # print("Google search completed")
        return result
    except Exception as e:
        print(f"❌ Google search failed: {e}")
        return f"❌ Google search error: {str(e)}"

# Enhanced Tools with better descriptions
tools = [
    Tool(
        name="PDF_Knowledge_Base",
        func=fast_rag_search,
        description=""""Use this tool ONLY for structured, text-based automotive knowledge.
        Best for:
        - Car maintenance guides, step-by-step instructions
        - Troubleshooting, repair manuals
        - Technical specifications, features, comparisons  
        - General automotive knowledge and how things work
        - Safety tips, best practices
        - General automotive explanations ("how does X work?")
        Do NOT use if user asks for videos, visual demonstrations, prices, news, or dealerships.
        Input: clear technical or how-to question."""
    ),
    Tool(
        name="YouTube_Search",
        func=youtube_search_fast,
        description="""Search YouTube for automotive videos. Use when user asks for:
        - Videos, visual demonstrations, tutorials
        - Requests with words like "video", "show me", "watch", "see", "tutorial"
        - Step-by-step visual guides
        Input: search terms describing the automotive video requested."""
    ),
    Tool(
        name="Google_Search", 
        func=google_search_wrapper,
        description="""Search Google for current information. Use for:
        - Current prices, dealership info, inventory
        - Latest news, recalls, new models releases
        - Real-time data, local services, prices
        - Anything time-sensitive or location-specific
        - General web search if unsure
         Input: clear query about news, prices, availability, or real-time info."""
    )
]

class QueueCallback(BaseCallbackHandler):
    def __init__(self, q: queue.Queue):
        self.q = q
        self.collecting = False
        self.buffer = ""

    def on_llm_new_token(self, token: str, **kwargs):
        self.buffer += token

        if not self.collecting and "Final Answer:" in self.buffer:
            self.collecting = True
            token = self.buffer.split("Final Answer:", 1)[1]
            self.q.put(token)
        elif self.collecting:
            self.q.put(token)

    def on_chain_end(self, outputs, **kwargs):
        self.q.put(None)

def create_conversational_agent(memory, streaming_handler=None):
    """Create a conversational ReAct agent with proper prompt template"""
    try:
        callbacks=[]
        if streaming_handler:
            callbacks.append(streaming_handler)
        else:
            callbacks.append(StreamingStdOutCallbackHandler())


        # Create LLM with streaming
        llm = ChatOllama(
            model=CONFIG["model_name"], 
            verbose=False,
            callbacks=callbacks,
            streaming=True,
        )
        
        try:
            prompt = hub.pull("hwchase17/react-chat")
            print("Using standard ReAct prompt from hub")
        except:
            # Fallback: Create custom prompt template
            print("Hub unavailable, using custom prompt")
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
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=4,
            return_intermediate_steps=False,
        )
        
        return agent_executor
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        print("Please ensure:")
        print("1. Ollama is running: ollama serve")
        print(f"2. Model is pulled: ollama pull {CONFIG['model_name']}")
        raise

import threading 
def get_bot_response_stream(user_input: str):
    q = queue.Queue()
    cb = QueueCallback(q)

    memory = setup_memory()
    load_previous_history(memory)
    agent_executor = create_conversational_agent(memory, streaming_handler=cb)

    def token_generator():
        def run_agent():
            try:
                agent_executor.invoke({
                    "input": user_input,
                    "chat_history": memory.chat_memory.messages
                })
            except Exception as e:
                q.put(f"[Agent error: {e}]")
            finally:
                q.put(None)

        threading.Thread(target=run_agent, daemon=True).start()

        collected = []
        while True:
            token = q.get()
            if token is None:
                break
            collected.append(token)
            yield token  

        # save full answer
        full_output = "".join(collected)
        try:
            save_exchange(user_input, full_output)
        except Exception:
            pass

    return token_generator()


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
        




# result = fast_rag_search("how to change a tire")
# print(result)