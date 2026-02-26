#!/usr/bin/env python3
"""
AlgoDraft RAG Backend
=====================
FastAPI application exposing endpoints for research paper queries, code
analysis, conversational chat, code generation, and paper management.

All AI interactions are delegated to the AgentHandler module which supports
both local (Ollama) and cloud (OpenAI, Anthropic, Hugging Face) models —
the user has full freedom to choose either.
"""

import json
import logging
import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .agent_handler import AgentHandler, CLOUD_PROVIDERS

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("algodraft")

BASE = Path(__file__).parent
CONFIG_FILE = BASE / "config.json"

DEFAULT_CONFIG = {
    "mode": "local",
    "local_model": "mistral",
    "local_code_model": "deepseek-coder:6.7b",
    "cloud_provider": "openai",
    "cloud_model": "gpt-4o",
    "api_key": "",
}

app = FastAPI(title="AlgoDraft RAG Backend")

# Thread-safe config file access
_config_lock = Lock()

# CORS — restrict origins in production via ALLOWED_ORIGINS env var (comma-separated)
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = (
    [o.strip() for o in _allowed_origins.split(",")]
    if _allowed_origins != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def save_config(cfg):
    """Save configuration to JSON file with atomic writes and locking."""
    with _config_lock:
        try:
            # Write to temporary file first
            temp_file = CONFIG_FILE.with_suffix('.json.tmp')
            temp_file.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
            # Atomic rename (on most filesystems)
            temp_file.replace(CONFIG_FILE)
            logger.debug("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise


if not CONFIG_FILE.exists():
    save_config(DEFAULT_CONFIG)


def load_config():
    """Load configuration from JSON file with validation."""
    with _config_lock:
        try:
            content = CONFIG_FILE.read_text(encoding='utf-8')
            # Validate JSON format
            cfg = json.loads(content)
            # Ensure all required keys exist
            for key in DEFAULT_CONFIG:
                if key not in cfg:
                    cfg[key] = DEFAULT_CONFIG[key]
            return cfg
        except json.JSONDecodeError as e:
            logger.error(f"Config file corrupted: {e}. Restoring from defaults.")
            # Restore from defaults if corrupted
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Failed to load config: {e}. Using defaults.")
            return DEFAULT_CONFIG


def get_agent_handler() -> AgentHandler:
    """Create an AgentHandler with the current config."""
    cfg = load_config()
    return AgentHandler(cfg)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    prompt: str
    top_k: Optional[int] = 3
    session_id: Optional[str] = None


class AnalyzeRequest(BaseModel):
    selected_code: str
    context: Optional[str] = None


class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str
    language: Optional[str] = "python"
    session_id: Optional[str] = None


class ConfigRequest(BaseModel):
    mode: str
    local_model: Optional[str] = None
    local_code_model: Optional[str] = None
    cloud_provider: Optional[str] = None
    cloud_model: Optional[str] = None
    api_key: Optional[str] = None


class RemoveFileRequest(BaseModel):
    filename: str


# ---------------------------------------------------------------------------
# AI-powered endpoints (delegated to AgentHandler)
# ---------------------------------------------------------------------------

@app.post("/query")
async def query(req: QueryRequest):
    """Query papers and return RAG-based answer.

    Supports both local and cloud AI models based on config.
    Returns structured response with separated code/text sections
    alongside the legacy 'answer' field for backward compatibility.
    """
    try:
        handler = get_agent_handler()
        response = handler.query(
            prompt=req.prompt,
            top_k=req.top_k or 3,
            session_id=req.session_id,
        )

        if response.error:
            raise HTTPException(status_code=500, detail=response.error)

        # Backward-compatible: include 'answer' alongside structured 'sections'
        result = response.to_dict()
        result["answer"] = response.raw

        # Include sources from vectorstore
        from .agent_handler import CHROMA_DIR
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        emb = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2", model_kwargs={"device": "cpu"})
        vectordb = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=emb)
        docs_and_scores = vectordb.similarity_search_with_score(req.prompt, k=req.top_k or 3)
        result["sources"] = [d.metadata for d, _ in docs_and_scores]

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Analyze selected code against research context.

    Supports both local and cloud AI models based on config.
    Returns structured response alongside the legacy 'analysis' field.
    """
    try:
        handler = get_agent_handler()
        response = handler.analyze(
            code=req.selected_code,
            context=req.context,
        )

        if response.error:
            raise HTTPException(status_code=500, detail=response.error)

        # Backward-compatible: include 'analysis' alongside structured 'sections'
        result = response.to_dict()
        result["analysis"] = response.raw
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    """Conversational AI chat with session-based memory.

    Supports both local and cloud AI models based on config.
    Maintains conversation context across messages within the same session.
    """
    try:
        handler = get_agent_handler()
        response = handler.chat(
            prompt=req.prompt,
            session_id=req.session_id,
        )

        if response.error:
            raise HTTPException(status_code=500, detail=response.error)

        result = response.to_dict()
        result["answer"] = response.raw
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate(req: GenerateRequest):
    """Generate code from a natural language description.

    Supports both local and cloud AI models based on config.
    For local mode, automatically uses the code-specific model if configured.
    """
    try:
        handler = get_agent_handler()
        response = handler.generate_code(
            prompt=req.prompt,
            language=req.language or "python",
            session_id=req.session_id,
        )

        if response.error:
            raise HTTPException(status_code=500, detail=response.error)

        result = response.to_dict()
        result["answer"] = response.raw
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Retrieve conversation history for a session."""
    try:
        handler = get_agent_handler()
        history = handler.get_session_history(session_id)
        return {"session_id": session_id, "messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Clear a conversation session."""
    try:
        handler = get_agent_handler()
        cleared = handler.clear_session(session_id)
        return {"status": "ok" if cleared else "not_found", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

@app.post("/config")
async def config(req: ConfigRequest):
    """Update server configuration (switch between local/cloud modes, etc.)."""
    try:
        # Validate input
        if req.api_key is not None and not isinstance(req.api_key, str):
            raise ValueError("API key must be a string")
        
        # Load current config
        cfg = load_config()
        
        # Update with new values
        update_data = req.model_dump(exclude_none=True)
        
        # Validate configuration before saving
        if "cloud_provider" in update_data:
            provider = update_data["cloud_provider"].lower()
            if provider not in CLOUD_PROVIDERS and provider != "local":
                supported = ", ".join(CLOUD_PROVIDERS.keys())
                raise ValueError(f"Unsupported provider: {provider}. Supported: {supported}")
        
        if "mode" in update_data:
            mode = update_data["mode"].lower()
            if mode not in ["local", "cloud"]:
                raise ValueError("Mode must be 'local' or 'cloud'")
        
        # Apply updates
        cfg.update(update_data)
        
        # Save configuration
        save_config(cfg)
        
        # Return sanitized response (don't expose API key)
        response_cfg = cfg.copy()
        response_cfg["api_key"] = "***hidden***" if cfg.get("api_key") else ""
        
        return {
            "status": "ok",
            "message": "Configuration updated successfully",
            "config": response_cfg
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Config update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@app.get("/config")
async def get_cfg():
    """Get current configuration with available providers."""
    try:
        cfg = load_config()
        # Never expose the actual API key in responses
        cfg["api_key"] = "***hidden***" if cfg.get("api_key") else ""
        cfg["available_providers"] = CLOUD_PROVIDERS
        return cfg
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Paper management endpoints
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a paper file and ingest it into the vectorstore."""
    try:
        papers_dir = BASE / "papers"
        papers_dir.mkdir(exist_ok=True)

        # Save the file
        file_path = papers_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info("File uploaded: %s", file.filename)

        # Trigger ingestion
        from .ingest import load_texts_from_papers, chunk_and_store

        docs = load_texts_from_papers(papers_dir)
        if docs:
            chunk_and_store(docs)
            logger.info("Ingested %d documents from papers", len(docs))

        return {"status": "ok", "filename": file.filename}
    except Exception as e:
        logger.error("Upload failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remove-file")
async def remove_file(request: RemoveFileRequest):
    """Remove a paper file and re-ingest remaining files."""
    try:
        filename = request.filename
        if not filename:
            raise ValueError("filename is required")

        papers_dir = BASE / "papers"
        file_path = papers_dir / filename

        if file_path.exists():
            file_path.unlink()
            logger.info("File removed: %s", filename)

        # Re-ingest all remaining files
        from .ingest import load_texts_from_papers, chunk_and_store

        docs = load_texts_from_papers(papers_dir)
        if docs:
            chunk_and_store(docs)
            logger.info("Re-ingested %d documents after file removal", len(docs))
        else:
            logger.warning("No documents found after file removal")

        return {"status": "ok", "filename": filename}
    except Exception as e:
        logger.error("File removal failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers")
async def list_papers():
    """List all uploaded papers."""
    try:
        papers_dir = BASE / "papers"
        papers_dir.mkdir(exist_ok=True)

        papers = []
        for p in papers_dir.glob("*"):
            if p.is_file() and p.suffix.lower() in [".pdf", ".txt", ".tex", ".md"]:
                papers.append(p.name)

        return {"papers": sorted(papers)}
    except Exception as e:
        logger.error("Failed to list papers: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Health & root
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint for load balancers and orchestration."""
    try:
        from .agent_handler import CHROMA_DIR
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        emb = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2", model_kwargs={"device": "cpu"})
        vectordb = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=emb)
        count = vectordb._collection.count()
        return {"status": "ok", "chroma_documents": count}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "degraded", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "AlgoDraft RAG Backend"}
