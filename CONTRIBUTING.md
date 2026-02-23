# Contributing to AlgoDraft

Thank you for your interest in contributing to AlgoDraft! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/yourusername/algodraft.git
cd algodraft
```

### 2. Set Up Development Environment

**Backend:**
```bash
python -m venv .venv
source .venv/bin/activate
cd backend
pip install -r requirements.txt
```

**Frontend (VS Code Extension):**
```bash
cd vscode-extension
npm install
```

### 3. Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

For local development, you need:
- **Ollama**: For local LLM inference (https://ollama.com)
- **ChromaDB**: Automatically initialized in `backend/chroma_db/`

## Development Workflow

### Backend Development

1. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Start the development server with auto-reload:
   ```bash
   cd backend
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. The API will be available at `http://127.0.0.1:8000`

### Frontend Development

1. Install dependencies:
   ```bash
   cd vscode-extension
   npm install
   ```

2. Build the extension:
   ```bash
   npm run build
   ```

3. Watch for changes:
   ```bash
   npm run watch
   ```

4. To test in VS Code:
   - Open the `vscode-extension` folder in VS Code
   - Press `F5` to start debugging with the extension

## Making Changes

### Branching

Create a feature branch:
```bash
git checkout -b feature/your-feature-name
git checkout -b fix/your-bug-fix
```

### Commits

Write clear, descriptive commit messages:
```bash
git commit -m "feat: add support for LaTeX document ingestion"
git commit -m "fix: resolve module import error in backend"
git commit -m "docs: update README with installation steps"
```

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring without feature changes
- `test:` - Adding or updating tests
- `perf:` - Performance improvements

### Testing

Before submitting:
- [ ] Backend server starts without errors
- [ ] Extension compiles with `npm run build`
- [ ] No console errors in VS Code extension
- [ ] Manual testing of changed features

## Pull Request Process

1. Update documentation and README if needed
2. Ensure all commits are clean and well-described
3. Push to your fork
4. Create a pull request with:
   - Clear title describing the change
   - Description of what changed and why
   - Links to any related issues
   - Screenshots for UI changes

## Project Structure

```
algodraft/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── ingest.py            # Document ingestion pipeline
│   ├── requirements.txt      # Python dependencies
│   ├── papers/              # User-uploaded research papers
│   └── chroma_db/           # Vector database (generated)
├── vscode-extension/
│   ├── src/
│   │   ├── extension.ts     # Extension entry point
│   │   └── webview/         # Webview UI
│   ├── package.json
│   ├── tsconfig.json
│   └── out/                 # Compiled output (generated)
├── README.md
├── LICENSE
└── .gitignore
```

## Architecture Overview

- **Backend**: FastAPI + LangChain RAG with ChromaDB vector database
- **Frontend**: VS Code Extension with Webview sidebar
- **LLM Support**: Local (Ollama) and cloud providers (OpenAI, Anthropic, Hugging Face)

## Debugging

### Backend Issues

Enable debug logging:
```bash
LOG_LEVEL=DEBUG uvicorn backend.main:app --reload
```

### Extension Issues

Check VS Code Developer Tools:
- Press `Ctrl+Shift+I` in the webview
- Check the console for errors

## Security

- Never commit `.env` files or API keys
- API keys are configured via the extension UI
- Sensitive information is sanitized in error messages

## Questions?

- Open an issue on GitHub
- Check existing documentation in README.md

Thank you for contributing!
