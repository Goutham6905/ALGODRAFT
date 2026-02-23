#!/usr/bin/env python3
import os
import subprocess
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_huggingface.llms import HuggingFaceEndpoint

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("algodraft")

BASE = Path(__file__).parent
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", str(BASE / "chroma_db")))
CONFIG_FILE = BASE / "config.json"

DEFAULT_CONFIG = {
    "mode": "local",
    "local_model": "mistral",
    "local_code_model": "deepseek-coder:6.7b",
    "cloud_provider": "openai",
    "cloud_model": "gpt-4o",
    "api_key": ""
}

# Supported cloud providers and their default models
CLOUD_PROVIDERS = {
    "openai": {"default_model": "gpt-4o", "name": "OpenAI"},
    "anthropic": {"default_model": "claude-3-sonnet-20240229", "name": "Anthropic"},
    "huggingface": {"default_model": "meta-llama/Llama-2-70b-chat-hf", "name": "Hugging Face"},
}

app = FastAPI(title="AlgoDraft RAG Backend")

# CORS — restrict origins in production via ALLOWED_ORIGINS env var (comma-separated)
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in _allowed_origins.split(",")] if _allowed_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

if not CONFIG_FILE.exists():
    save_config(DEFAULT_CONFIG)

def load_config():
    return json.loads(CONFIG_FILE.read_text())

class QueryRequest(BaseModel):
    prompt: str
    top_k: Optional[int] = 3

class AnalyzeRequest(BaseModel):
    selected_code: str
    context: Optional[str] = None

class ConfigRequest(BaseModel):
    mode: str
    local_model: Optional[str] = None
    local_code_model: Optional[str] = None
    cloud_provider: Optional[str] = None
    cloud_model: Optional[str] = None
    api_key: Optional[str] = None

class RemoveFileRequest(BaseModel):
    filename: str

def ensure_ollama_model(model_name: str):
    """Ensure Ollama model is installed; pull if not present."""
    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
        if model_name not in res.stdout:
            logger.info("Model %s not found in ollama; pulling...", model_name)
            pull = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True, check=False)
            if pull.returncode != 0:
                raise RuntimeError(f"Failed to pull ollama model {model_name}: {pull.stderr}")
            logger.info("Pulled %s", model_name)
        else:
            logger.debug("Ollama model %s present.", model_name)
    except FileNotFoundError:
        raise RuntimeError("`ollama` CLI not found on PATH. Install Ollama and retry.")

class OllamaWrapper:
    """Simple wrapper for Ollama local execution."""
    def __init__(self, model_name):
        self.model_name = model_name
    
    def __call__(self, messages, **kwargs):
        full = ""
        for m in messages:
            role = m.get("role") if isinstance(m, dict) else "user"
            content = m.get("content") if isinstance(m, dict) else str(m)
            full += f"[{role}]\n{content}\n\n"
        proc = subprocess.run(
            ["ollama", "run", self.model_name],
            input=full,
            text=True,
            capture_output=True,
            timeout=300
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ollama run failed: {proc.stderr}")
        return proc.stdout.strip()

def get_chat_model(cfg):
    """Get chat model based on config: local Ollama or cloud provider."""
    mode = cfg.get("mode", "local")
    if mode == "cloud":
        provider = cfg.get("cloud_provider", "openai").lower()
        model = cfg.get("cloud_model")
        api_key = cfg.get("api_key") or os.environ.get("ALGODRAFT_API_KEY")
        
        if provider == "openai":
            if not api_key:
                raise RuntimeError("OpenAI API key not configured. Please set your OpenAI API key in settings.")
            return ChatOpenAI(model=model, openai_api_key=api_key, temperature=0.0)
        
        elif provider == "anthropic":
            if not api_key:
                raise RuntimeError("Anthropic API key not configured. Please set your Anthropic API key in settings.")
            return ChatAnthropic(model=model, api_key=api_key, temperature=0.0)
        
        elif provider == "huggingface":
            if not api_key:
                raise RuntimeError("Hugging Face API key not configured. Please set your Hugging Face API key in settings.")
            return HuggingFaceEndpoint(repo_id=model, huggingfacehub_api_token=api_key, temperature=0.0)
        
        else:
            raise RuntimeError(f"Unsupported cloud provider: {provider}. Supported providers: {', '.join(CLOUD_PROVIDERS.keys())}")
    else:
        local_model = cfg.get("local_model")
        ensure_ollama_model(local_model)
        return OllamaWrapper(local_model)

def get_vectorstore():
    """Get Chroma vectorstore for retrieval."""
    emb = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
    vectordb = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=emb)
    return vectordb

@app.post("/query")
async def query(req: QueryRequest):
    """Query papers and return RAG-based answer."""
    try:
        cfg = load_config()
        vectordb = get_vectorstore()
        docs_and_scores = vectordb.similarity_search_with_score(req.prompt, k=req.top_k)
        contexts = []
        for doc, score in docs_and_scores:
            contexts.append(doc.page_content)
        
        system_prompt = (
            "You are AlgoDraft Research Assistant. Answer the user's question using ONLY the provided context. "
            "If the answer is not contained in the context, reply with: 'Insufficient context to answer.' Be concise."
        )
        
        context_text = "\n\n".join(contexts)
        user_message = f"Context:\n\n{context_text}\n\nUser question: {req.prompt}"
        
        model = get_chat_model(cfg)
        if isinstance(model, OllamaWrapper):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            resp_text = model(messages)
        elif hasattr(model, "invoke"):
            # For HuggingFaceEndpoint and chat models
            try:
                msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
                resp = model.invoke(msgs)
                resp_text = resp.content if hasattr(resp, 'content') else str(resp)
            except Exception as e:
                logger.error(f"Error invoking model: {e}")
                raise
        else:
            raise RuntimeError("Unknown model type - cannot invoke")
        
        return {
            "answer": resp_text,
            "sources": [d.metadata for d, _ in docs_and_scores]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Analyze selected code against research context."""
    try:
        cfg = load_config()
        vectordb = get_vectorstore()
        
        contexts = []
        if req.context:
            contexts = [req.context]
        else:
            results = vectordb.similarity_search(req.selected_code, k=3)
            contexts = [r.page_content for r in results]
        
        system_prompt = (
            "You are AlgoDraft Code Reviewer. Examine the provided code and the research context. "
            "Do NOT modify the code. Produce an analysis listing missing key points from the research, "
            "and enumerate mistakes or conceptual errors. For each error, describe why it is incorrect. "
            "Return concise numbered items."
        )
        
        context_text = "\n".join(contexts)
        user_message = f"Context:\n{context_text}\n\nSelected code:\n{req.selected_code}"
        
        model = get_chat_model(cfg)
        if isinstance(model, OllamaWrapper):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            resp_text = model(messages)
        else:
            # For ChatOpenAI, ChatAnthropic, HuggingFaceEndpoint
            try:
                msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
                resp = model.invoke(msgs)
                resp_text = resp.content if hasattr(resp, 'content') else str(resp)
            except Exception as e:
                logger.error(f"Error invoking model: {type(e).__name__}: {str(e)}", exc_info=True)
                raise
        
        return {"analysis": resp_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
async def config(req: ConfigRequest):
    """Update server configuration."""
    try:
        cfg = load_config()
        for k, v in req.model_dump(exclude_none=True).items():
            cfg[k] = v
        save_config(cfg)
        return {"status": "ok", "config": cfg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_cfg():
    """Get current configuration."""
    cfg = load_config()
    # Include available providers in response
    cfg["available_providers"] = CLOUD_PROVIDERS
    return cfg


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a paper file and ingest it."""
    try:
        papers_dir = BASE / "papers"
        papers_dir.mkdir(exist_ok=True)
        
        # Save the file
        file_path = papers_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File uploaded: {file.filename}")
        
        # Trigger ingestion
        from .ingest import load_texts_from_papers, chunk_and_store
        docs = load_texts_from_papers(papers_dir)
        if docs:
            chunk_and_store(docs)
            logger.info(f"Ingested {len(docs)} documents from papers")
        
        return {"status": "ok", "filename": file.filename}
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
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
            logger.info(f"File removed: {filename}")
        
        # Re-ingest all remaining files
        from .ingest import load_texts_from_papers, chunk_and_store
        docs = load_texts_from_papers(papers_dir)
        if docs:
            chunk_and_store(docs)
            logger.info(f"Re-ingested {len(docs)} documents after file removal")
        else:
            logger.warning("No documents found after file removal")
        
        return {"status": "ok", "filename": filename}
    except Exception as e:
        logger.error(f"File removal failed: {e}", exc_info=True)
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
        logger.error(f"Failed to list papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint for load balancers and orchestration."""
    try:
        vectordb = get_vectorstore()
        count = vectordb._collection.count()
        return {"status": "ok", "chroma_documents": count}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "degraded", "error": str(e)}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "AlgoDraft RAG Backend"}
