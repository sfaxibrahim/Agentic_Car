# Automotive Assistant AI

A professional AI-powered automotive assistant with RAG (Retrieval-Augmented Generation), YouTube search, and Google search capabilities.

## Features

- **RAG System**: Semantic search over PDF documents using FAISS and BM25
- **YouTube Integration**: Search and embed YouTube videos
- **Google Search**: Real-time web search capabilities
- **Conversational AI**: ReAct agent with conversation memory
- **Streaming Responses**: Real-time token streaming for better UX
- **API Integration**: Connects with Spring Boot backend for persistence

## Prerequisites

1. **Python 3.9+**
2. **Ollama** with Mistral model:
   ```bash
   ollama pull mistral:latest
   ollama serve
   ```
3. **SerpAPI Key**: Get one from [serpapi.com](https://serpapi.com)
4. **Spring Boot API** (optional): Running on `http://localhost:8080`

## Installation

### 1. Clone and Setup

```bash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**.env file:**
```env
SERPAPI_API_KEY=your_serpapi_key_here
OLLAMA_MODEL=mistral:latest
MEMORY_WINDOW=5
SAVE_HISTORY=true
SPRING_API_URL=http://localhost:8080
```

### 3. Prepare Data

```bash
# Create data directories
mkdir -p data/PDF
mkdir -p data/vector_store_faiss

# Add your PDF files to data/PDF/
# Build FAISS index (separate script or use existing vectorstore)
```

## Running the Application

### Development Mode

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### 1. Regular Chat (Non-streaming)

**POST** `/chat`

```json
{
  "question": "How do I change a tire?"
}
```

**Response:**
```json
{
  "answer": "Here's how to change a tire..."
}
```

### 2. Streaming Chat

**POST** `/chat/stream`

**Headers:**
```
Authorization: Bearer <your_access_token>
```

**Body:**
```json
{
  "question": "Show me a video about changing oil",
  "convId": "conversation-uuid-here"
}
```

**Response:** Server-Sent Events stream

### 3. Health Check

**GET** `/health`

```json
{
  "status": "healthy"
}
```

## Testing

### Using cURL

```bash
# Streaming chat
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"question": "Show me videos about car maintenance", "convId": "test-123"}' \
  --no-buffer
```

### Using Python

```python
import requests

# Streaming chat
response = requests.post(
    "http://localhost:8000/chat/stream",
    json={
        "question": "Find videos about brake replacement",
        "convId": "conv-123"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    stream=True
)

for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
    if chunk:
        print(chunk, end="", flush=True)
```

## How It Works

### Agent Tools

The AI agent has access to three tools:

1. **PDF_Knowledge_Base**: Searches automotive PDFs using hybrid RAG (FAISS + BM25)
2. **YouTube_Search**: Finds relevant automotive videos on YouTube
3. **Google_Search**: Performs real-time web searches for current information
4. **Car Deals** :perform webscspring through autoscout or webcar.eu to find cars and process thme later 
### Agent Decision Flow

```
User Question
     ↓
ReAct Agent (Mistral)
     ↓
Tool Selection:
  - Technical question? → PDF_Knowledge_Base
  - Want videos? → YouTube_Search
  - Current info/prices? → Google_Search
  - Best car deals 
     ↓
Tool Execution
     ↓
Format Response
     ↓
Stream to User
```

## Customization

### Change LLM Model

Edit `config/settings.py` or `.env`:
```env
OLLAMA_MODEL=llama2:latest
```

### Adjust Memory Window

```env
MEMORY_WINDOW=10  # Keep last 10 exchanges
```

### Modify Tool Descriptions

Edit `core/agent.py` → `get_agent_tools()` function

## Development Notes

### Adding New Tools

1. Create tool function in appropriate service file
2. Add Tool definition in `core/agent.py`
3. Update tool descriptions for agent

### Extending RAG System

- Add new embedding models in `services/rag_service.py`
- Adjust chunk sizes in text splitter
- Modify retriever weights in ensemble

### Custom Callbacks

Create new callback handlers in `core/callbacks.py`

## Troubleshooting

### Issue: "RAG system not initialized"

- Ensure FAISS vectorstore exists at `data/vector_store_faiss/`
- Check PDF files are in `data/PDF/`
- Verify file permissions

### Issue: "Ollama connection failed"

```bash
# Check Ollama is running
ollama serve

# Verify model is available
ollama list

# Pull model if needed
ollama pull mistral:latest
```

### Issue: "SerpAPI rate limit"

- Check your SerpAPI quota
- Reduce search frequency
- Consider caching search results



