# AlgoDraft AI — Research Copilot MVP

An offline-first, IDE-native research copilot for querying local papers (PDFs/LaTeX) and injecting generated code directly into your VS Code editor. Optimized for dense academic papers on data structures, algorithms, ML, and data analytics.

## Architecture

- **Backend**: FastAPI + LangChain RAG with ChromaDB vector store, supports local (Ollama) and cloud (OpenAI, Anthropic, Gemini) LLM routing.
- **Frontend**: VS Code Extension (TypeScript) with Webview sidebar for chat and code analysis.
- **Hardware Target**: Ubuntu 24.04 LTS, Ryzen 7 5800H, RTX 3060 6GB, 16GB RAM.

## Directory Structure

```
ALGODRAFT/
├── backend/
│   ├── papers/                 # PDFs, .tex files go here
│   ├── chroma_db/              # Chroma vector store (auto-created)
│   ├── requirements.txt
│   ├── ingest.py               # Ingestion script
│   ├── main.py                 # FastAPI server
│   └── config.json             # Server config (auto-created)
├── vscode-extension/
│   ├── src/
│   │   ├── extension.ts        # Extension entry point
│   │   └── webview/
│   │       └── webview.html.ts # Webview HTML/JS
│   ├── package.json
│   ├── tsconfig.json
│   └── out/                    # Compiled JS (auto-generated)
└── README.md
```

## Setup & Execution

### 1. Backend Environment

From workspace root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install & Setup Ollama

Download and install from https://ollama.com/docs. Then pull models (the server auto-pulls on demand, but you can prefetch):

```bash
ollama pull mistral
ollama pull deepseek-coder:6.7b
```

Ensure `ollama serve` is running in the background (it starts automatically on most systems).

### 3. Ingest Papers

Add your PDFs and .tex files to `backend/papers/`. Then run ingestion:

```bash
cd backend
source .venv/bin/activate
python ingest.py
```

This builds the ChromaDB vector store in `backend/chroma_db/`.

### 4. Start FastAPI Server

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Server listens at `http://127.0.0.1:8000`. Config is persisted in `config.json` and can be updated via `POST /config` from the extension UI.

### 5. VS Code Extension Setup

In a new terminal from workspace root:

```bash
cd vscode-extension
npm install
npm run build
```

Open the `vscode-extension` folder in VS Code and press **F5** to launch the Extension Development Host.

### 6. Using AlgoDraft

1. In the Extension Development Host, open the **AlgoDraft** activity icon in the left sidebar.
2. Type queries about your papers in the chat box (e.g., "Explain quicksort's complexity").
3. Select code in any editor, right-click → **AlgoDraft: Analyze Selected Code** to get a critique.
4. Use the **Settings** panel to toggle between Local (Ollama) and Cloud (OpenAI, etc.) modes and input API keys.

## Configuration

Edit `backend/config.json` or use the Webview UI:

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

- **mode**: `"local"` (Ollama) or `"cloud"` (API).
- **local_model**: Model name for queries (default: `mistral`).
- **local_code_model**: Model name for code tasks (default: `deepseek-coder:6.7b`).
- **cloud_provider**: `"openai"` (extensible).
- **cloud_model**: Model name when using cloud (e.g., `gpt-4o`).
- **api_key**: API key for cloud provider (set via Webview or `OPENAI_API_KEY` env var).

## API Endpoints

### `/query` (POST)

Query papers and return RAG-based answer.

**Request:**
```json
{
  "prompt": "Explain quicksort complexity",
  "top_k": 3
}
```

**Response:**
```json
{
  "answer": "Quicksort has O(n log n) average complexity...",
  "sources": [{"source": "papers/algo.pdf", "chunk": 0}, ...]
}
```

### `/analyze` (POST)

Analyze selected code against research context.

**Request:**
```json
{
  "selected_code": "def quick_sort(arr): ...",
  "context": null
}
```

**Response:**
```json
{
  "analysis": "1. Missing handling for edge cases...\n2. Incorrect partition logic..."
}
```

### `/config` (GET / POST)

Get or update server configuration.

**GET Response:** Current config (JSON).
**POST Request:** Partial config update (JSON).

## Performance Tuning for RTX 3060 6GB + 16GB RAM

- **Local models only** for offline-first, low-latency inference.
- **Mistral** (~7B) fine for general NLP tasks; fits comfortably in shared VRAM.
- **Deepseek-coder 6.7B** optimized for code generation.
- **Monitor VRAM**: Watch `nvidia-smi` during ingestion and queries. If OOM, reduce `chunk_size` in `ingest.py` or run Ollama with CPU offloading.
- **Chroma persistence**: Use NVMe SSD for faster retrieval.
- **Batch embedding**: HuggingFace sentence-transformers auto-batches; use `all-mpnet-base-v2` (110M params) for weight.

## Troubleshooting

- **Ollama model not found**: Ensure `ollama serve` is running. The backend auto-pulls missing models.
- **Chroma DB is empty**: Run `python ingest.py` after adding PDFs to `papers/`.
- **CORS errors on extension**: Ensure backend is running and `BACKEND_URL` matches in `extension.ts`.
- **Extension dev host crashes**: Run `npm run build` to recompile TypeScript.
- **Out of VRAM**: Reduce embedding batch size or use cloud mode temporarily.

## Next Steps (Future Enhancements)

- Add streaming responses for long queries.
- Implement code-block detection and syntax-aware insertion.
- Add document upload UI (bypass manual `papers/` folder).
- Support for Anthropic, Gemini, and other cloud providers.
- Fine-tune local models on common research domains.
- Add user authentication and multi-user support.

---

**Built with**: FastAPI, LangChain, ChromaDB, Ollama, HuggingFace, VS Code Extension API.
