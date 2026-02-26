#!/usr/bin/env python3
import os
import logging
from typing import List
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from pathlib import Path

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("algodraft.ingest")

BASE = Path(__file__).parent
PAPERS = BASE / "papers"
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", str(BASE / "chroma_db")))
EMBED_MODEL = "all-mpnet-base-v2"

def load_texts_from_papers(papers_dir: Path) -> List:
    docs = []
    for p in papers_dir.glob("**/*"):
        if p.suffix.lower() == ".pdf":
            try:
                loader = PyPDFLoader(str(p))
                pages = loader.load()
                docs.extend(pages)
            except Exception as e:
                logger.error("Failed to load PDF %s: %s", p, e)
        elif p.suffix.lower() in [".tex", ".txt", ".md"]:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                from langchain_core.documents import Document
                docs.append(Document(page_content=text, metadata={"source": str(p)}))
            except Exception as e:
                logger.error("Failed to read %s: %s", p, e)
    return docs

def chunk_and_store(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )
    texts = []
    metadatas = []
    for d in docs:
        chunks = splitter.split_text(d.page_content)
        for i, c in enumerate(chunks):
            texts.append(c)
            md = dict(d.metadata or {})
            md.update({"chunk": i})
            metadatas.append(md)

    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={"device": "cpu"})
    vectordb = Chroma.from_texts(
        texts,
        embedding=emb,
        metadatas=metadatas,
        persist_directory=str(CHROMA_DIR),
    )
    vectordb.persist()
    logger.info("Ingestion complete. Chroma persisted at: %s", CHROMA_DIR)

if __name__ == "__main__":
    PAPERS.mkdir(exist_ok=True)
    CHROMA_DIR.mkdir(exist_ok=True)
    docs = load_texts_from_papers(PAPERS)
    if not docs:
        logger.warning("No documents found in ./papers. Add PDFs or .tex files and re-run.")
    else:
        chunk_and_store(docs)
