"""
ATLAS wrapper for HippoMem — brain-inspired persistent memory for LLM chat.
Uses Gemini's OpenAI-compatible endpoint; no separate API key required.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

USER_ID = "rishi"

# Gemini OpenAI-compatible endpoint (no /v1 suffix for base_url)
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


class AtlasMemory:
    """
    Thin wrapper around HippoMem MemoryService for ATLAS.
    Single-user (user_id="rishi"). Exposes start/recall/remember/stop.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_url: str = "sqlite:///.hippomem/hippomem.db",
        vector_dir: str = ".hippomem/vectors",
        llm_model: str = "gemini-2.0-flash",
        embedding_model: str = "text-embedding-004",
        enable_entity_extraction: bool = True,
        enable_self_memory: bool = True,
        enable_background_consolidation: bool = True,
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._db_url = db_url
        self._vector_dir = vector_dir
        self._llm_model = llm_model
        self._embedding_model = embedding_model
        self._enable_entity_extraction = enable_entity_extraction
        self._enable_self_memory = enable_self_memory
        self._enable_background_consolidation = enable_background_consolidation
        self.service = None
        self._last_decode = None

    async def start(self) -> None:
        """Create DB, session factory, and start background consolidation."""
        if not self._api_key:
            logger.warning("AtlasMemory: GEMINI_API_KEY not set; memory disabled.")
            return
        try:
            from hippomem import MemoryService
            from hippomem.config import MemoryConfig
        except ImportError as e:
            logger.warning("AtlasMemory: hippomem not installed; memory disabled. %s", e)
            return

        config = MemoryConfig(
            db_url=self._db_url,
            vector_dir=self._vector_dir,
            llm_model=self._llm_model,
            embedding_model=self._embedding_model,
            enable_entity_extraction=self._enable_entity_extraction,
            enable_self_memory=self._enable_self_memory,
            enable_background_consolidation=self._enable_background_consolidation,
        )
        self.service = MemoryService(
            llm_api_key=self._api_key,
            llm_base_url=GEMINI_OPENAI_BASE,
            config=config,
        )
        await self.service.setup()
        logger.info("AtlasMemory: started (user_id=%s)", USER_ID)

    async def recall(
        self,
        message: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Pre-inference: retrieve relevant memory context.
        Returns formatted context string (or empty string if none / disabled).
        """
        if not self.service:
            return ""
        conversation_history = conversation_history or []
        try:
            result = await self.service.decode(
                USER_ID,
                message,
                session_id=session_id,
                conversation_history=conversation_history,
            )
            self._last_decode = result
            return result.context or ""
        except Exception as e:
            logger.exception("AtlasMemory recall failed: %s", e)
            return ""

    async def remember(
        self,
        user_message: str,
        assistant_response: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> None:
        """
        Post-inference: store the completed turn.
        Non-blocking; call from fire-and-forget task if needed.
        """
        if not self.service:
            return
        conversation_history = conversation_history or []
        try:
            await self.service.encode(
                USER_ID,
                user_message,
                assistant_response,
                decode_result=self._last_decode,
                session_id=session_id,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.exception("AtlasMemory remember failed: %s", e)

    async def stop(self) -> None:
        """Run consolidation and close the service."""
        if not self.service:
            return
        try:
            await self.service.consolidate(USER_ID)
            await self.service.close()
            logger.info("AtlasMemory: stopped")
        except Exception as e:
            logger.exception("AtlasMemory stop failed: %s", e)
        finally:
            self.service = None
            self._last_decode = None
