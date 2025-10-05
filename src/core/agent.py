"""
Agent creation and management
"""
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain_community.chat_models import ChatOllama
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.prompts import PromptTemplate
from langchain import hub
from langchain.memory import ConversationBufferWindowMemory
from typing import Optional

from config.settings import settings
from services.rag_service import search_pdf_knowledge
from services.search_service import youtube_search, google_search
from services.car_deal_service import car_search


# Define tools with clear descriptions
def get_agent_tools():
    """
    Get the list of tools available to the agent
    
    Returns:
        List of Tool instances
    """
    return [
        Tool(
            name="PDF_Knowledge_Base",
            func=search_pdf_knowledge,
            description="""Use this tool ONLY for structured, text-based automotive knowledge.
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
            func=youtube_search,
            description="""Search YouTube for automotive videos. Use when user asks for:
            - Videos, visual demonstrations, tutorials
            - Requests with words like "video", "show me", "watch", "see", "tutorial"
            - Step-by-step visual guides
            Input: search terms describing the automotive video requested."""
        ),
        
        Tool(
            name="Google_Search",
            func=google_search,
            description="""Search Google for current information. Use for:
            - Current prices, dealership info, inventory
            - Latest news, recalls, new models releases
            - Real-time data, local services, prices
            - Anything time-sensitive or location-specific
            - General web search if unsure
            Input: clear query about news, prices, availability, or real-time info."""
        ),
        Tool(
            name="car_search",
            func=car_search,
            description="""Search for car listings based on user query.
            Best for:
              - Finding cars for sale
              - Searching listings
              - Queries like "find me a 2020 BMW X5 under €50,000 "
            Input: natural language query about the desired car.
            """
        ),
    ]


def create_conversational_agent(
    memory: ConversationBufferWindowMemory,
    streaming_handler: Optional[object] = None
) -> AgentExecutor:
    """
    Create a conversational ReAct agent with proper prompt template
    
    Args:
        memory: Conversation memory instance
        streaming_handler: Optional callback handler for streaming
        
    Returns:
        AgentExecutor instance
    """
    try:
        # Setup callbacks
        callbacks = []
        if streaming_handler:
            callbacks.append(streaming_handler)
        else:
            callbacks.append(StreamingStdOutCallbackHandler())
        
        # Create LLM with streaming
        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            # base_url=settings.OLLAMA_BASE_URL,  # Add this line
            verbose=False,
            callbacks=callbacks,
            streaming=True,
        )
        
        # Try to get prompt from hub, fallback to custom
        try:
            prompt = hub.pull("hwchase17/react-chat")
            # raise Exception("Force custom")  # <--- remove this if you want hub to actually work
            print("✅ Using standard ReAct prompt from hub")
        except Exception:
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

IMPORTANT RULES:
For car_search:
- The tool returns up to 10 car listings in JSON (title, price, year, mileage, fuel, link).
- YOU MUST analyze these results and select ONLY the top 3 that best match the user’s request.
- Consider criteria like price, year, mileage, fuel type, and transmission.
- Never return the full raw JSON to the user. 
- Instead, provide a clear, human-readable summary of the 3 best options with title, price, year, fuel, mileage, and link.

For PDF_Knowledge_Base:
- Use this first for technical "how-to" questions.

For YouTube_Search:
- Use when the user asks for videos or tutorials.

For Google_Search:
- Use when the user asks for current prices, news, dealerships, or other live info.

Previous conversation:

{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""
            
            
            prompt = PromptTemplate(
                input_variables=["tools", "tool_names", "chat_history", "input", "agent_scratchpad"],
                template=template
            )
        
        # Get tools
        tools = get_agent_tools()
        
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
            verbose=True,  # CHANGE THIS to see what's happening
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=False,
            early_stopping_method="generate",  # ADD THIS - stops after first valid answer

        )
        
        print("✅ Agent created successfully")
        return agent_executor
    
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        print("Please ensure:")
        print("1. Ollama is running: ollama serve")
        print(f"2. Model is pulled: ollama pull {settings.OLLAMA_MODEL}")
        raise