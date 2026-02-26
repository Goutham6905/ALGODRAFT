#!/usr/bin/env python3
"""
AlgoDraft AI Agent Handler
==========================
Centralized module for managing AI agent interactions. Supports both local
models (Ollama) and cloud providers (OpenAI, Anthropic, Hugging Face).

Modules:
    - PromptManager:        Named prompt template registry
    - InputProcessor:       Validation & sanitization
    - OutputParser:         Separate code blocks, text, errors from raw LLM output
    - ConversationManager:  In-memory session-based conversation history
    - AgentHandler:         Main orchestrator tying everything together
"""

import logging
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv  # type: ignore[import-unresolved]
from langchain_anthropic import ChatAnthropic  # type: ignore[import-unresolved]
from langchain_chroma import Chroma  # type: ignore[import-unresolved]
from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore[import-unresolved]
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # type: ignore[import-unresolved]
from langchain_huggingface.llms import HuggingFaceEndpoint  # type: ignore[import-unresolved]
from langchain_openai import ChatOpenAI  # type: ignore[import-unresolved]

load_dotenv()

logger = logging.getLogger("algodraft.agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", str(BASE / "chroma_db")))

# Supported cloud providers and their default models
CLOUD_PROVIDERS = {
    "openai": {"default_model": "gpt-4o", "name": "OpenAI"},
    "anthropic": {"default_model": "claude-3-sonnet-20240229", "name": "Anthropic"},
    "huggingface": {
        "default_model": "meta-llama/Llama-2-70b-chat-hf",
        "name": "Hugging Face",
    },
}

# Token limits per provider family (conservative estimates)
TOKEN_LIMITS = {
    "local": 4096,
    "openai": 128000,
    "anthropic": 200000,
    "huggingface": 4096,
}

# Maximum input length (characters) to prevent abuse
MAX_INPUT_LENGTH = 50000
MAX_CODE_INPUT_LENGTH = 100000

# Session defaults
DEFAULT_MAX_HISTORY_TURNS = 10
SESSION_TTL_SECONDS = 1800  # 30 minutes


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CodeBlock:
    """A single extracted code block from an AI response."""

    language: str
    content: str
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"language": self.language, "content": self.content, "label": self.label}


@dataclass
class ResponseSection:
    """A section of a parsed AI response — either text, code, or error."""

    type: str  # "text" | "code" | "error"
    content: str
    language: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "content": self.content, "language": self.language}


@dataclass
class AgentResponse:
    """Structured response from the AI agent."""

    sections: List[ResponseSection] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    summary: str = ""
    has_code: bool = False
    raw: str = ""
    error: Optional[str] = None
    model_used: str = ""
    provider_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sections": [s.to_dict() for s in self.sections],
            "code_blocks": [c.to_dict() for c in self.code_blocks],
            "summary": self.summary,
            "has_code": self.has_code,
            "raw": self.raw,
            "error": self.error,
            "model_used": self.model_used,
            "provider_used": self.provider_used,
        }


@dataclass
class ConversationMessage:
    """A single message in a conversation."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}


# ---------------------------------------------------------------------------
# PromptManager
# ---------------------------------------------------------------------------


class PromptManager:
    """Registry of named prompt templates for different agent tasks."""

    _templates: Dict[str, str] = {
        "research_assistant": (
            "You are AlgoDraft Research Assistant. Answer the user's question "
            "using ONLY the provided context from research papers. "
            "If the answer is not contained in the context, reply with: "
            "'Insufficient context to answer.'\n\n"
            "Guidelines:\n"
            "- Be concise and precise\n"
            "- Cite the source paper when possible\n"
            "- Format code examples with proper markdown fenced code blocks "
            "(```language)\n"
            "- Separate explanatory text from code clearly\n"
            "- Use numbered lists for multi-step explanations"
        ),
        "code_reviewer": (
            "You are AlgoDraft Code Reviewer. Examine the provided code and "
            "the research context.\n\n"
            "Instructions:\n"
            "- Do NOT modify the code\n"
            "- List missing key points from the research\n"
            "- Enumerate mistakes or conceptual errors with explanations\n"
            "- For each error, explain WHY it is incorrect\n"
            "- Suggest improvements as separate code blocks (```language)\n"
            "- Return concise numbered items\n"
            "- Clearly separate analysis text from any code suggestions"
        ),
        "code_generator": (
            "You are AlgoDraft Code Generator. Generate high-quality, "
            "well-documented code based on the user's request.\n\n"
            "Guidelines:\n"
            "- Write clean, production-ready code\n"
            "- Include docstrings and inline comments for complex logic\n"
            "- Use proper markdown code blocks with language tags (```{language})\n"
            "- Explain your approach BEFORE the code block\n"
            "- Explain key design decisions AFTER the code block\n"
            "- Handle edge cases and include error handling\n"
            "- If context from research papers is provided, incorporate "
            "relevant algorithms or patterns"
        ),
        "chat": (
            "You are AlgoDraft, an intelligent AI assistant specialized in "
            "algorithms, data structures, and computer science research.\n\n"
            "Guidelines:\n"
            "- Be conversational but precise\n"
            "- When writing code, always use markdown fenced code blocks "
            "(```language)\n"
            "- Clearly separate code from explanatory text\n"
            "- Reference previous messages in the conversation when relevant\n"
            "- If you don't know something, say so honestly\n"
            "- For complex answers, use structured formatting (headers, lists)"
        ),
    }

    @classmethod
    def get_prompt(cls, template_name: str, **kwargs: Any) -> str:
        """Get a prompt template by name, optionally formatting with kwargs.

        Args:
            template_name: Template name (research_assistant, code_reviewer,
                           code_generator, chat).
            **kwargs: Variables to substitute into the template.

        Returns:
            Rendered prompt string.

        Raises:
            ValueError: If template name is unknown.
        """
        template = cls._templates.get(template_name)
        if template is None:
            available = ", ".join(cls._templates.keys())
            raise ValueError(
                f"Unknown prompt template '{template_name}'. Available: {available}"
            )
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                # If template doesn't use the kwargs, return as-is
                return template
        return template

    @classmethod
    def register_prompt(cls, name: str, template: str) -> None:
        """Register a custom prompt template.

        Args:
            name: Template name.
            template: Prompt string (may contain {variable} placeholders).
        """
        cls._templates[name] = template

    @classmethod
    def list_prompts(cls) -> List[str]:
        """Return all available prompt template names."""
        return list(cls._templates.keys())


# ---------------------------------------------------------------------------
# InputProcessor
# ---------------------------------------------------------------------------


class InputProcessor:
    """Validates and sanitizes user inputs before sending to the AI model."""

    # Patterns that could be prompt injection attempts
    _INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?above",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if",
        r"new\s+instructions?\s*:",
        r"system\s*:\s*",
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Sanitize input text by normalizing whitespace and trimming.

        Args:
            text: Raw input text.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""
        # Normalize various whitespace characters
        text = text.strip()
        # Strip trailing horizontal whitespace before newlines
        text = re.sub(r"[ \t]+\n", "\n", text)
        # Collapse multiple blank lines into two
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove null bytes
        text = text.replace("\x00", "")
        return text

    @classmethod
    def validate_prompt(cls, text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
        """Validate a user prompt — checks emptiness and length.

        Args:
            text: Input prompt text.
            max_length: Maximum allowed character count.

        Returns:
            The validated text.

        Raises:
            ValueError: If input is empty or too long.
        """
        cleaned = cls.sanitize(text)
        if not cleaned:
            raise ValueError("Prompt cannot be empty.")
        if len(cleaned) > max_length:
            raise ValueError(
                f"Prompt too long ({len(cleaned)} chars). "
                f"Maximum allowed: {max_length} characters."
            )
        return cleaned

    @classmethod
    def validate_code(cls, code: str) -> str:
        """Validate code input for analysis/review.

        Args:
            code: Source code string.

        Returns:
            The validated code.

        Raises:
            ValueError: If code is empty or too long.
        """
        cleaned = cls.sanitize(code)
        if not cleaned:
            raise ValueError("Code input cannot be empty.")
        if len(cleaned) > MAX_CODE_INPUT_LENGTH:
            raise ValueError(
                f"Code too long ({len(cleaned)} chars). "
                f"Maximum allowed: {MAX_CODE_INPUT_LENGTH} characters."
            )
        return cleaned

    @classmethod
    def check_injection(cls, text: str) -> bool:
        """Check if text contains potential prompt injection patterns.

        Args:
            text: Input text to check.

        Returns:
            True if a potential injection is detected.
        """
        lower = text.lower()
        for pattern in cls._INJECTION_PATTERNS:
            if re.search(pattern, lower):
                logger.warning("Potential prompt injection detected: %s", pattern)
                return True
        return False

    @classmethod
    def extract_code_context(cls, text: str) -> Dict[str, Any]:
        """Detect and extract any embedded code blocks from the user prompt.

        Args:
            text: User prompt that may contain code.

        Returns:
            Dict with 'has_code', 'code_blocks' list, and 'clean_text'.
        """
        code_pattern = r"```(\w*)\n(.*?)```"
        matches = re.findall(code_pattern, text, re.DOTALL)
        code_blocks = []
        for lang, code in matches:
            code_blocks.append({"language": lang or "text", "content": code.strip()})
        clean_text = re.sub(code_pattern, "", text, flags=re.DOTALL).strip()
        return {
            "has_code": len(code_blocks) > 0,
            "code_blocks": code_blocks,
            "clean_text": clean_text,
        }


# ---------------------------------------------------------------------------
# OutputParser
# ---------------------------------------------------------------------------


class OutputParser:
    """Parses raw LLM text output into structured sections and code blocks."""

    # Regex to match fenced code blocks: ```lang\ncode\n```
    _CODE_BLOCK_PATTERN = re.compile(
        r"```(\w*)\s*\n(.*?)```", re.DOTALL
    )

    @classmethod
    def parse(cls, raw_text: str) -> AgentResponse:
        """Parse raw AI response text into a structured AgentResponse.

        Separates code blocks from text, extracts metadata, and produces
        an ordered list of ResponseSections.

        Args:
            raw_text: Raw text output from the AI model.

        Returns:
            AgentResponse with sections, code_blocks, summary, etc.
        """
        if not raw_text or not raw_text.strip():
            return AgentResponse(
                raw=raw_text or "",
                error="Empty response from AI model.",
                sections=[
                    ResponseSection(
                        type="error", content="Empty response from AI model."
                    )
                ],
            )

        raw_text = raw_text.strip()
        sections: List[ResponseSection] = []
        code_blocks: List[CodeBlock] = []
        text_parts: List[str] = []

        # Split the text by code blocks, preserving order
        last_end = 0
        for match in cls._CODE_BLOCK_PATTERN.finditer(raw_text):
            # Text before this code block
            text_before = raw_text[last_end : match.start()].strip()  # type: ignore[index]
            if text_before:
                sections.append(ResponseSection(type="text", content=text_before))
                text_parts.append(text_before)

            # The code block itself
            lang = match.group(1) or "text"
            code_content = match.group(2).strip()
            sections.append(
                ResponseSection(type="code", content=code_content, language=lang)
            )
            code_blocks.append(
                CodeBlock(language=lang, content=code_content)
            )
            last_end = match.end()

        # Any remaining text after the last code block
        remaining = raw_text[last_end:].strip()  # type: ignore[index]
        if remaining:
            sections.append(ResponseSection(type="text", content=remaining))
            text_parts.append(remaining)

        # If no code block regex matched, the entire text is one section
        if not sections:
            sections.append(ResponseSection(type="text", content=raw_text))
            text_parts.append(raw_text)

        summary = "\n\n".join(text_parts)

        return AgentResponse(
            sections=sections,
            code_blocks=code_blocks,
            summary=summary,
            has_code=len(code_blocks) > 0,
            raw=raw_text,
        )

    @classmethod
    def extract_first_code_block(cls, raw_text: str) -> Optional[CodeBlock]:
        """Extract only the first code block from the response.

        Args:
            raw_text: Raw AI response text.

        Returns:
            CodeBlock or None if no code block found.
        """
        match = cls._CODE_BLOCK_PATTERN.search(raw_text)
        if match:
            lang = match.group(1) or "text"
            return CodeBlock(language=lang, content=match.group(2).strip())
        return None


# ---------------------------------------------------------------------------
# ConversationManager
# ---------------------------------------------------------------------------


@dataclass
class _Session:
    """Internal session data."""

    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    max_turns: int = DEFAULT_MAX_HISTORY_TURNS


class ConversationManager:
    """In-memory conversation history manager with session support and TTL."""

    def __init__(
        self,
        max_history_turns: int = DEFAULT_MAX_HISTORY_TURNS,
        ttl_seconds: int = SESSION_TTL_SECONDS,
    ):
        self._sessions: Dict[str, _Session] = {}
        self._lock = Lock()
        self._max_turns = max_history_turns
        self._ttl = ttl_seconds

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new conversation session.

        Args:
            session_id: Optional custom session ID. Auto-generated if None.

        Returns:
            The session ID.
        """
        sid = session_id or str(uuid.uuid4())
        with self._lock:
            self._sessions[sid] = _Session(
                session_id=sid, max_turns=self._max_turns
            )
        logger.debug("Created session: %s", sid)
        return sid

    def add_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Add a message to a session's history.

        Creates the session automatically if it doesn't exist.

        Args:
            session_id: Session ID.
            role: 'user', 'assistant', or 'system'.
            content: Message content.
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = _Session(
                    session_id=session_id, max_turns=self._max_turns
                )
            session = self._sessions[session_id]
            session.messages.append(ConversationMessage(role=role, content=content))
            session.last_active = time.time()

            # Trim to max turns (keep system messages + last N user/assistant pairs)
            if len(session.messages) > session.max_turns * 2:
                system_msgs = [
                    m for m in session.messages if m.role == "system"
                ]
                non_system = [
                    m for m in session.messages if m.role != "system"
                ]
                # Keep last max_turns * 2 non-system messages
                keep = session.max_turns * 2
                trimmed = non_system[len(non_system) - keep:]
                session.messages = system_msgs + trimmed

    def get_history(
        self, session_id: str, max_turns: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get conversation history for a session.

        Args:
            session_id: Session ID.
            max_turns: Optional limit on number of turns to return.

        Returns:
            List of message dicts with 'role' and 'content'.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            messages = session.messages
            if max_turns:
                # Return last N*2 messages (user + assistant pairs)
                messages = messages[-(max_turns * 2) :]
            return [m.to_dict() for m in messages]

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages from a session.

        Args:
            session_id: Session ID.

        Returns:
            True if session existed and was cleared.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug("Cleared session: %s", session_id)
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove sessions that have exceeded their TTL.

        Returns:
            Number of sessions removed.
        """
        now = time.time()
        removed = 0
        with self._lock:
            expired = [
                sid
                for sid, s in self._sessions.items()
                if (now - s.last_active) > self._ttl
            ]
            for sid in expired:
                del self._sessions[sid]
                removed += 1
        if removed:
            logger.info("Cleaned up %d expired sessions", removed)
        return removed

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions with metadata.

        Returns:
            List of session info dicts.
        """
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "message_count": len(s.messages),
                    "created_at": s.created_at,
                    "last_active": s.last_active,
                }
                for s in self._sessions.values()
            ]


# ---------------------------------------------------------------------------
# OllamaWrapper (local model support)
# ---------------------------------------------------------------------------


class OllamaWrapper:
    """Wrapper for local Ollama model execution via CLI."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def __call__(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> str:
        """Run a prompt through the local Ollama model.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Model response text.

        Raises:
            RuntimeError: If ollama CLI fails.
        """
        full = ""
        for m in messages:
            role = m.get("role") if isinstance(m, dict) else "user"
            content = m.get("content") if isinstance(m, dict) else str(m)
            full += f"[{role}]\n{content}\n\n"
        
        try:
            proc = subprocess.run(
                ["ollama", "run", self.model_name],
                input=full,
                text=True,
                capture_output=True,
                timeout=300,
            )
            if proc.returncode != 0:
                error_msg = proc.stderr.strip() if proc.stderr else "Unknown error"
                raise RuntimeError(
                    f"Ollama model '{self.model_name}' invocation failed. "
                    f"Error: {error_msg or '(empty response)'}. "
                    f"Ensure Ollama is running: 'ollama serve'"
                )
            return proc.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(
                f"Ollama CLI not found on PATH. Install from https://ollama.com "
                f"or switch to cloud AI via /config endpoint."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Ollama model '{self.model_name}' response timeout (300s). "
                f"The model may be too large for your system."
            )

    @staticmethod
    def ensure_model(model_name: str) -> None:
        """Ensure an Ollama model is installed; pull if not present.

        Args:
            model_name: Ollama model identifier.

        Raises:
            RuntimeError: If ollama CLI is not found or pull fails.
        """
        try:
            res = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, check=False
            )
            if model_name not in res.stdout:
                logger.info("Pulling ollama model: %s", model_name)
                pull = subprocess.run(
                    ["ollama", "pull", model_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if pull.returncode != 0:
                    error_msg = pull.stderr.strip() if pull.stderr else f"Model '{model_name}' not found"
                    raise RuntimeError(
                        f"Failed to pull ollama model '{model_name}'. "
                        f"Reason: {error_msg}. "
                        f"Ensure Ollama is running: 'ollama serve'\n"
                        f"Then try: ollama pull {model_name}"
                    )
                logger.info("Pulled %s", model_name)
            else:
                logger.debug("Ollama model %s present.", model_name)
        except FileNotFoundError:
            raise RuntimeError(
                f"Ollama CLI not found. Install from https://ollama.com or "
                f"switch to cloud AI by setting api_key via /config endpoint."
            )


# ---------------------------------------------------------------------------
# AgentHandler — Main Orchestrator
# ---------------------------------------------------------------------------


class AgentHandler:
    """Main AI agent orchestrator.

    Ties together prompt management, input processing, model invocation,
    output parsing, and conversation management. Supports both local
    (Ollama) and cloud (OpenAI, Anthropic, HuggingFace) models — the
    user has full freedom to choose either.

    Usage::

        handler = AgentHandler(config)
        response = handler.query("What is quicksort?", vectordb=vectordb)
        response = handler.analyze(code="def foo(): pass", vectordb=vectordb)
        response = handler.chat("Hello!", session_id="user-123")
        response = handler.generate_code("binary search in Python", language="python")
    """

    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds

    def __init__(self, config: Dict[str, Any]):
        """Initialize the agent handler.

        Args:
            config: Configuration dict with keys:
                - mode: 'local' or 'cloud'
                - local_model: Ollama model name (for local mode)
                - local_code_model: Ollama code model name (for local mode)
                - cloud_provider: 'openai', 'anthropic', or 'huggingface'
                - cloud_model: Model identifier for cloud provider
                - api_key: API key for cloud provider
        """
        self._config = config
        self._conversation = ConversationManager()
        self._prompt_manager = PromptManager
        self._input_processor = InputProcessor
        self._output_parser = OutputParser

    def _get_model(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """Get the appropriate AI model based on configuration.

        Supports both local (Ollama) and cloud providers. The user can
        freely switch between modes via config.

        Args:
            config: Optional config override. Uses self._config if None.

        Returns:
            Model instance (OllamaWrapper or LangChain chat model).

        Raises:
            RuntimeError: If provider is unsupported or API key is missing.
        """
        cfg = config or self._config
        mode = cfg.get("mode", "local")

        if mode == "cloud":
            provider = cfg.get("cloud_provider", "openai").lower()
            model = cfg.get("cloud_model")
            api_key = cfg.get("api_key") or os.environ.get("ALGODRAFT_API_KEY")

            if provider == "openai":
                if not api_key:
                    raise RuntimeError(
                        "OpenAI API key not configured. "
                        "Set your API key in settings or ALGODRAFT_API_KEY env var."
                    )
                return ChatOpenAI(
                    model=model, openai_api_key=api_key, temperature=0.0
                )

            elif provider == "anthropic":
                if not api_key:
                    raise RuntimeError(
                        "Anthropic API key not configured. "
                        "Set your API key in settings or ALGODRAFT_API_KEY env var."
                    )
                return ChatAnthropic(
                    model=model, api_key=api_key, temperature=0.0
                )

            elif provider == "huggingface":
                if not api_key:
                    raise RuntimeError(
                        "Hugging Face API key not configured. "
                        "Set your API key in settings or ALGODRAFT_API_KEY env var."
                    )
                return HuggingFaceEndpoint(
                    repo_id=model,
                    huggingfacehub_api_token=api_key,
                    temperature=0.0,
                )

            else:
                supported = ", ".join(CLOUD_PROVIDERS.keys())
                raise RuntimeError(
                    f"Unsupported cloud provider: {provider}. "
                    f"Supported: {supported}"
                )
        else:
            # Local mode — Ollama
            local_model = cfg.get("local_model", "mistral")
            OllamaWrapper.ensure_model(local_model)
            return OllamaWrapper(local_model)

    def _get_provider_name(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Get the provider name string for response metadata."""
        cfg = config or self._config
        mode = cfg.get("mode", "local")
        if mode == "cloud":
            return cfg.get("cloud_provider", "openai")
        return "ollama"

    def _get_model_name(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Get the model name string for response metadata."""
        cfg = config or self._config
        mode = cfg.get("mode", "local")
        if mode == "cloud":
            return cfg.get("cloud_model", "unknown")
        return cfg.get("local_model", "mistral")

    def _invoke_model(
        self,
        model: Any,
        system_prompt: str,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Invoke the AI model with retry logic.

        Supports both OllamaWrapper (local) and LangChain chat models (cloud).

        Args:
            model: Model instance.
            system_prompt: System-level instructions.
            user_message: User's input message.
            history: Optional conversation history messages.

        Returns:
            Raw response text from the model.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if isinstance(model, OllamaWrapper):
                    messages = [{"role": "system", "content": system_prompt}]
                    if history:
                        messages.extend(history)
                    messages.append({"role": "user", "content": user_message})
                    return model(messages)

                elif hasattr(model, "invoke"):
                    msgs = [SystemMessage(content=system_prompt)]
                    if history:
                        for h in history:
                            if h["role"] == "user":
                                msgs.append(HumanMessage(content=h["content"]))
                            elif h["role"] == "assistant":
                                msgs.append(AIMessage(content=h["content"]))
                    msgs.append(HumanMessage(content=user_message))
                    resp = model.invoke(msgs)
                    return resp.content if hasattr(resp, "content") else str(resp)

                else:
                    raise RuntimeError("Unknown model type — cannot invoke")

            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.BASE_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "Model invocation failed (attempt %d/%d): %s. "
                        "Retrying in %.1fs...",
                        attempt + 1,
                        self.MAX_RETRIES,
                        str(e),
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Model invocation failed after %d attempts: %s",
                        self.MAX_RETRIES,
                        str(e),
                    )

        raise RuntimeError(
            f"AI model invocation failed after {self.MAX_RETRIES} attempts: "
            f"{last_error}"
        )

    def _get_vectorstore(self) -> Any:
        """Get the Chroma vectorstore for RAG retrieval.

        Returns:
            Chroma vectorstore instance.
        """
        emb = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2", model_kwargs={"device": "cpu"})
        return Chroma(persist_directory=str(CHROMA_DIR), embedding_function=emb)

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def query(
        self,
        prompt: str,
        top_k: int = 3,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """RAG-based query against ingested research papers.

        Works with both local (Ollama) and cloud models.

        Args:
            prompt: User's research question.
            top_k: Number of context documents to retrieve.
            session_id: Optional session ID for conversation tracking.
            config: Optional config override.

        Returns:
            Structured AgentResponse with parsed sections.
        """
        try:
            prompt = self._input_processor.validate_prompt(prompt)
            cfg = config or self._config

            # Retrieve relevant context from vectorstore
            vectordb = self._get_vectorstore()
            docs_and_scores = vectordb.similarity_search_with_score(prompt, k=top_k)
            contexts = [doc.page_content for doc, _score in docs_and_scores]

            # Build the prompt
            system_prompt = self._prompt_manager.get_prompt("research_assistant")
            context_text = "\n\n".join(contexts)
            user_message = f"Context:\n\n{context_text}\n\nUser question: {prompt}"

            # Get conversation history if session exists
            history = None
            if session_id:
                history = self._conversation.get_history(session_id, max_turns=3)

            # Invoke model
            model = self._get_model(cfg)
            raw_response = self._invoke_model(
                model, system_prompt, user_message, history
            )

            # Parse response
            response = self._output_parser.parse(raw_response)
            response.model_used = self._get_model_name(cfg)
            response.provider_used = self._get_provider_name(cfg)

            # Track conversation
            if session_id:
                self._conversation.add_message(session_id, "user", prompt)
                self._conversation.add_message(
                    session_id, "assistant", raw_response
                )

            return response

        except ValueError as e:
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )
        except Exception as e:
            logger.error("Query failed: %s", e, exc_info=True)
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )

    def analyze(
        self,
        code: str,
        context: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Analyze selected code against research context.

        Works with both local (Ollama) and cloud models.

        Args:
            code: Source code to analyze.
            context: Optional explicit context. Auto-retrieves from
                     vectorstore if not provided.
            config: Optional config override.

        Returns:
            Structured AgentResponse with analysis results.
        """
        try:
            code = self._input_processor.validate_code(code)
            cfg = config or self._config

            # Get context
            contexts = []
            if context:
                contexts = [context]
            else:
                vectordb = self._get_vectorstore()
                results = vectordb.similarity_search(code, k=3)
                contexts = [r.page_content for r in results]

            # Build the prompt
            system_prompt = self._prompt_manager.get_prompt("code_reviewer")
            context_text = "\n".join(contexts)
            user_message = f"Context:\n{context_text}\n\nSelected code:\n{code}"

            # Invoke model
            model = self._get_model(cfg)
            raw_response = self._invoke_model(model, system_prompt, user_message)

            # Parse response
            response = self._output_parser.parse(raw_response)
            response.model_used = self._get_model_name(cfg)
            response.provider_used = self._get_provider_name(cfg)
            return response

        except ValueError as e:
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )
        except Exception as e:
            logger.error("Analysis failed: %s", e, exc_info=True)
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )

    def chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Free-form conversational chat with context awareness.

        Works with both local (Ollama) and cloud models. Maintains
        conversation history per session.

        Args:
            prompt: User's chat message.
            session_id: Session ID for conversation continuity.
                       Auto-created if not provided.
            config: Optional config override.

        Returns:
            Structured AgentResponse.
        """
        try:
            prompt = self._input_processor.validate_prompt(prompt)
            cfg = config or self._config

            # Ensure session
            if not session_id:
                session_id = self._conversation.create_session()

            # Get conversation history
            history = self._conversation.get_history(session_id)

            # Build prompt
            system_prompt = self._prompt_manager.get_prompt("chat")

            # Check if user prompt references papers — do a lightweight RAG
            user_message = prompt
            try:
                vectordb = self._get_vectorstore()
                docs = vectordb.similarity_search(prompt, k=2)
                if docs:
                    paper_context = "\n\n".join(
                        d.page_content[:500] for d in docs
                    )
                    user_message = (
                        f"Relevant research context (use only if related to "
                        f"the question):\n{paper_context}\n\n"
                        f"User message: {prompt}"
                    )
            except Exception:
                # Vectorstore might be empty or unavailable — that's fine
                pass

            # Invoke model
            model = self._get_model(cfg)
            raw_response = self._invoke_model(
                model, system_prompt, user_message, history
            )

            # Parse and track
            response = self._output_parser.parse(raw_response)
            response.model_used = self._get_model_name(cfg)
            response.provider_used = self._get_provider_name(cfg)

            self._conversation.add_message(session_id, "user", prompt)
            self._conversation.add_message(session_id, "assistant", raw_response)

            return response

        except ValueError as e:
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )
        except Exception as e:
            logger.error("Chat failed: %s", e, exc_info=True)
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )

    def generate_code(
        self,
        prompt: str,
        language: str = "python",
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Generate code based on a natural language description.

        Works with both local (Ollama) and cloud models. For local mode,
        prefers the code-specific model if configured.

        Args:
            prompt: Description of the code to generate.
            language: Target programming language.
            session_id: Optional session ID.
            config: Optional config override.

        Returns:
            Structured AgentResponse containing generated code.
        """
        try:
            prompt = self._input_processor.validate_prompt(prompt)
            cfg = config or self._config

            # For local mode, prefer the code-specific model if available
            if cfg.get("mode") == "local" and cfg.get("local_code_model"):
                code_cfg = dict(cfg)
                code_cfg["local_model"] = cfg["local_code_model"]
                model = self._get_model(code_cfg)
                model_name = cfg["local_code_model"]
            else:
                model = self._get_model(cfg)
                model_name = self._get_model_name(cfg)

            # Build prompt
            system_prompt = self._prompt_manager.get_prompt(
                "code_generator", language=language
            )

            # Try to get relevant research context
            user_message = (
                f"Generate {language} code for the following:\n\n{prompt}"
            )
            try:
                vectordb = self._get_vectorstore()
                docs = vectordb.similarity_search(prompt, k=2)
                if docs:
                    paper_context = "\n\n".join(
                        d.page_content[:500] for d in docs
                    )
                    user_message = (
                        f"Relevant research context (incorporate applicable "
                        f"algorithms/patterns):\n{paper_context}\n\n"
                        f"Generate {language} code for the following:\n\n"
                        f"{prompt}"
                    )
            except Exception:
                pass

            # Conversation history for iterative generation
            history = None
            if session_id:
                history = self._conversation.get_history(session_id, max_turns=3)

            # Invoke model
            raw_response = self._invoke_model(
                model, system_prompt, user_message, history
            )

            # Parse response
            response = self._output_parser.parse(raw_response)
            response.model_used = model_name
            response.provider_used = self._get_provider_name(cfg)

            # Track conversation
            if session_id:
                self._conversation.add_message(session_id, "user", prompt)
                self._conversation.add_message(
                    session_id, "assistant", raw_response
                )

            return response

        except ValueError as e:
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )
        except Exception as e:
            logger.error("Code generation failed: %s", e, exc_info=True)
            return AgentResponse(
                error=str(e),
                sections=[ResponseSection(type="error", content=str(e))],
            )

    # -------------------------------------------------------------------
    # Session management
    # -------------------------------------------------------------------

    def get_session_history(
        self, session_id: str
    ) -> List[Dict[str, str]]:
        """Get conversation history for a session.

        Args:
            session_id: Session ID.

        Returns:
            List of message dicts.
        """
        return self._conversation.get_history(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear a conversation session.

        Args:
            session_id: Session ID.

        Returns:
            True if session was found and cleared.
        """
        return self._conversation.clear_session(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active conversation sessions.

        Returns:
            List of session metadata dicts.
        """
        return self._conversation.list_sessions()

    def cleanup_sessions(self) -> int:
        """Remove expired conversation sessions.

        Returns:
            Number of sessions removed.
        """
        return self._conversation.cleanup_expired()
