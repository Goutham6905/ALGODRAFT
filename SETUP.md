# AlgoDraft Setup Instructions

## System Requirements

- **OS**: Ubuntu 24.04 LTS (or similar Linux/macOS)
- **Python**: 3.9+
- **Node.js**: 16+
- **RAM**: 4GB minimum (8GB+ recommended for LLM inference)
- **GPU** (Optional): NVIDIA GPU recommended for faster local inference

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/algodraft.git
cd algodraft
```

### 2. Backend Setup

```bash
# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment (copy template and edit as needed)
cp .env.example .env
```

### 3. Install Ollama (for local LLM inference)

Visit https://ollama.com and install Ollama for your platform.

Start Ollama in the background:
```bash
ollama serve
```

In another terminal, pull a model:
```bash
ollama pull mistral
ollama pull deepseek-coder:6.7b
```

### 4. VS Code Extension Setup

```bash
cd vscode-extension
npm install
npm run build
```

To develop the extension:
```bash
npm run watch
```

Then press `F5` in VS Code to launch a debug instance.

### 5. Start the Backend Server

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 6. Use in VS Code

1. Open VS Code
2. Go to Extensions marketplace
3. Search for "AlgoDraft" and install (or load from `vscode-extension/` folder for development)
4. Open the AlgoDraft sidebar (View → AlgoDraft or click the AlgoDraft icon)
5. Upload research papers
6. Ask questions about your papers

## Configuration

### Environment Variables

Edit `.env` to customize:

```dotenv
# Logging level
LOG_LEVEL=INFO

# Vector database location
CHROMA_DIR=./backend/chroma_db

# CORS origins (for API access from other applications)
ALLOWED_ORIGINS=*

# Cloud provider API key (if using cloud LLMs)
ALGODRAFT_API_KEY=sk-...
```

### Extension Settings

Configure via VS Code extension UI:
- **Mode**: Local (Ollama) or Cloud (OpenAI, Anthropic, Hugging Face)
- **Provider**: Select cloud provider if using cloud mode
- **Model**: Model name (e.g., `mistral`, `gpt-4o`)
- **API Key**: Required for cloud providers

## Document Formats Supported

- `.pdf` - PDF files
- `.tex` - LaTeX source files
- `.txt` - Plain text
- `.md` - Markdown files

Place files in `backend/papers/` or use the "Upload" button in the extension.

## Troubleshooting

### Backend fails to start with "No module named 'ingest'"

Ensure the backend directory is a Python package:
```bash
touch backend/__init__.py
```

### Ollama not found

Install Ollama from https://ollama.com

Verify it's on your PATH:
```bash
ollama --version
```

### No papers found after upload

Check that:
1. Backend server is running at `http://127.0.0.1:8000`
2. Papers are in `backend/papers/` directory
3. Backend has permissions to read files
4. Supported file format is being used

### Extension won't load

1. Rebuild the extension:
   ```bash
   cd vscode-extension
   npm run build
   ```

2. Reload VS Code window (`Ctrl+R`)

## Performance Tips

- For large PDFs (>50 pages), ingestion may take a minute or two
- Use Ollama with GPU support for faster inference
- Smaller models (7B parameters) are faster but less accurate
- Larger models (70B+) require more VRAM

## Security Considerations

- API keys are stored in `.env` and extension settings (not synced)
- Never commit `.env` containing real API keys
- Sensitive information is redacted from error messages
- CORS is restricted to `*` by default (set `ALLOWED_ORIGINS` for production)

## Next Steps

- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Check [README.md](README.md) for project architecture
- Read the code documentation for implementation details

## Support

For issues, questions, or feature requests, open an issue on GitHub.

Happy researching! 🚀
