# AlgoDraft AI — Research Copilot MVP

An offline-first, IDE-native research copilot for querying local papers (PDFs/LaTeX) and injecting generated code directly into your VS Code editor. Optimized for dense academic papers on data structures, algorithms, ML, and data analytics.

Supports both **local AI (Ollama)** and **cloud AI providers** (OpenAI, Anthropic, Hugging Face, Google) with seamless switching.

## Key Features

✅ **Multi-Provider AI Support**
- Local: Ollama (offline, no API key needed)
- Cloud: OpenAI (GPT-4o), Anthropic (Claude-3), Hugging Face (Llama), Google (Gemini)
- Switch between providers without restarting

✅ **RAG (Retrieval-Augmented Generation)**
- Ingest research papers (PDFs, LaTeX, Markdown)
- ChromaDB vector store for semantic search
- Context-aware responses with source citations

✅ **VS Code Integration**
- Chat interface in IDE sidebar
- Code analysis and suggestions
- Real-time configuration updates

✅ **Security & Privacy**
- Local mode runs completely offline
- API keys stored securely (never logged)
- Git-safe configuration with example templates

## Architecture

- **Backend**: FastAPI + LangChain RAG with ChromaDB, supports local (Ollama) and cloud LLM providers
- **Frontend**: VS Code Extension (TypeScript) with Webview UI for chat, config, and code analysis
- **Hardware Target**: Ubuntu 24.04 LTS, Ryzen 7 5800H, RTX 3060 6GB, 16GB RAM (works on any system)

## Quick Start

### 1. Clone & Install Backend

```bash
git clone https://github.com/Goutham6905/ALGODRAFT.git
cd ALGODRAFT
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Setup AI Provider

**Option A: Local AI (Ollama) - No API Key**
```bash
# Install from https://ollama.com
ollama pull mistral
ollama pull deepseek-coder:6.7b
ollama serve  # Run in background
```

**Option B: Cloud AI - Bring Your Own API Key**
```bash
# Get API key from your provider
# OpenAI: https://platform.openai.com/account/api-keys
# Anthropic: https://console.anthropic.com/
# Hugging Face: https://huggingface.co/settings/tokens
# Google: https://aistudio.google.com/app/apikey

# Set environment variable
export ALGODRAFT_API_KEY=your_api_key_here
```

See [API_KEY_SETUP.md](API_KEY_SETUP.md) for detailed provider-specific instructions.

### 3. Ingest Papers

```bash
# Add your PDFs, LaTeX, or Markdown files
cp your_papers/*.pdf backend/papers/

# Build vector store
cd backend && python ingest.py
```

### 4. Start Backend Server

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Server available at `http://127.0.0.1:8000`

### 5. Install VS Code Extension

```bash
cd vscode-extension
npm install
npm run build
```

Open the `vscode-extension` folder in VS Code and press **F5** to launch.

## Configuration

### Switch Providers

**Via HTTP Endpoint:**
```bash
# Switch to OpenAI
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "cloud",
    "cloud_provider": "openai",
    "cloud_model": "gpt-4o",
    "api_key": "sk-proj-your_key_here"
  }'

# Switch to Local Ollama
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "local",
    "local_model": "mistral",
    "api_key": ""
  }'
```

**Via VS Code Extension UI:**
- Open **AlgoDraft Settings** in sidebar
- Select mode (Local/Cloud)
- Choose provider and model
- Paste API key (if cloud)
- Settings auto-save

**Via Environment Variable:**
```bash
export ALGODRAFT_API_KEY=your_api_key_here
```

### Configuration File

Edit `backend/config.json`:
```json
{
  "mode": "local",
  "local_model": "mistral",
  "local_code_model": "deepseek-coder:6.7b",
  "cloud_provider": "openai",
  "cloud_model": "gpt-4o",
  "api_key": ""
}
```

## Supported Cloud Providers

| Provider | Format | Models | Link |
|----------|--------|--------|------|
| **OpenAI** | `sk-proj-...` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | https://platform.openai.com |
| **Anthropic** | `sk-ant-...` | claude-3-opus, claude-3-sonnet | https://console.anthropic.com |
| **Hugging Face** | `hf_...` | meta-llama/Llama-2-70b, etc. | https://huggingface.co/settings/tokens |
| **Google** | `AIza...` | Gemini Pro, Gemini Pro Vision | https://aistudio.google.com/app/apikey |

## Directory Structure

```
ALGODRAFT/
├── backend/
│   ├── papers/                 # Upload PDFs, LaTeX, Markdown here
│   ├── chroma_db/              # Vector store (auto-created)
│   ├── main.py                 # FastAPI server
│   ├── agent_handler.py        # AI orchestration (local + cloud)
│   ├── ingest.py               # Paper indexing
│   ├── requirements.txt         # Python dependencies
│   ├── config.json             # Configuration (git-ignored)
│   ├── config.json.example     # Config template
│   └── Dockerfile              # Container setup
├── vscode-extension/
│   ├── src/
│   │   ├── extension.ts        # Extension entry point
│   │   └── webview/            # UI components
│   ├── package.json
│   └── tsconfig.json
├── .env.example                # Environment template
├── API_KEY_SETUP.md            # Detailed API key guide
├── SETUP.md                    # Detailed setup instructions
├── CONTRIBUTING.md             # Development guidelines
└── README.md                   # This file
```

## API Endpoints

### `/query` (POST)

Query papers with RAG-based responses.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is quicksort?", "top_k": 3}'
```

**Response:**
```json
{
  "answer": "Quicksort is a divide-and-conquer algorithm...",
  "sections": [...],
  "code_blocks": [...],
  "sources": [...]
}
```

### `/analyze` (POST)

Analyze code against research context.

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"selected_code": "def quicksort(arr): ..."}'
```

### `/generate` (POST)

Generate code from natural language.

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write binary search", "language": "python"}'
```

### `/chat` (POST)

Conversational chat with session memory.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "session_id": "user-123"}'
```

### `/config` (GET/POST)

Get or update configuration.

```bash
# Get current config (API key hidden)
curl http://localhost:8000/config

# Update config
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "cloud", "api_key": "..."}'
```

### `/upload` (POST)

Upload papers for ingestion.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@research_paper.pdf"
```

### `/health` (GET)

Health check for deployment.

```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Ollama Errors

**"Ollama CLI not found"**
- Install from https://ollama.com
- Ensure `ollama serve` is running
- Add Ollama to PATH

**"Model not found"**
- Run: `ollama pull mistral`
- Check available models: `ollama list`

### Cloud Provider Errors

**"API key not configured"**
- Set via environment: `export ALGODRAFT_API_KEY=...`
- Set via `/config` endpoint
- Check key format matches provider

**"Connection timeout"**
- Verify internet connection
- Confirm API key is valid
- Check provider status page

### Config Issues

**"Failed to save config"**
- Ensure `backend/config.json` is writable
- Check disk space
- Restart the server

**"Extra data in JSON"** (if occurs)
- Delete `backend/config.json`
- Server auto-restores from defaults
- Reconfigure via `/config` endpoint

## Performance Tips

- **Ollama**: Monitor VRAM with `nvidia-smi`
- **Vector Search**: NVMe SSD recommended for ChromaDB
- **Embeddings**: Using `all-mpnet-base-v2` (110M params, lightweight)
- **Chunking**: Adjust in `ingest.py` if OOM occurs
- **Cloud**: Check rate limits for your provider

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Security

✅ API keys never logged or exposed
✅ Config file is git-ignored
✅ Environment variables recommended for production
✅ No external data collection
✅ Local mode: 100% offline

## Future Enhancements

- Streaming responses for long queries
- Web UI alternative to VS Code
- Document upload UI
- User authentication & multi-user support
- Fine-tuned models for specialized domains
- Real-time collaboration

---

**Built with**: FastAPI, LangChain, ChromaDB, Ollama, Sentence Transformers, VS Code Extension API

