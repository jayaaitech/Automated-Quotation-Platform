import os
import logging
from typing import Dict, Any, List

from app.brain.embedding_service import embed_query
from app.brain.vector_service import hybrid_search, rerank
from app.brain.llm_service import ask_llm

logger = logging.getLogger(__name__)


def safe_get(d: dict, key: str, default=None):
    try:
        return d.get(key, default)
    except Exception:
        return default


async def ask_rfq(question: str, top_k: int = 8) -> Dict[str, Any]:
    """
    Full RFQ query pipeline (Hybrid + Rerank + LLM)
    """

    try:
        logger.info("RFQ Query: %s", question)

        # --------------------------------------------------
        # 1️⃣ EMBEDDING
        # --------------------------------------------------
        embedding = await embed_query(question)

        # --------------------------------------------------
        # 2️⃣ HYBRID RETRIEVAL
        # --------------------------------------------------
        results = hybrid_search(question, embedding, top_k=15) or []
        logger.info(f"Retrieved (pre-rerank): {len(results)}")

        if not results:
            return {
                "question": question,
                "answer": "No relevant information found.",
                "sources": [],
                "chunks_used": 0,
                "context_preview": ""
            }

        # --------------------------------------------------
        # 3️⃣ 🔥 RERANK (MOST IMPORTANT)
        # --------------------------------------------------
        results = rerank(question, results, top_k=top_k)
        logger.info(f"After rerank: {len(results)}")

        # --------------------------------------------------
        # 4️⃣ DEDUPE + STRUCTURE
        # --------------------------------------------------
        sources: List[str] = []
        context_parts: List[str] = []
        seen_hashes = set()

        for i, r in enumerate(results):
            text = safe_get(r, "text", "").strip()

            if not text:
                continue

            # Better dedupe using hash (not raw text)
            text_hash = hash(text)
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            # 🔥 Add chunk labels (VERY IMPORTANT for LLM)
            formatted_chunk = f"[Chunk {i+1}]\n{text}"
            context_parts.append(formatted_chunk)

            # Source extraction
            meta = safe_get(r, "metadata", {}) or {}

            source_path = (
                meta.get("source")
                or meta.get("file")
                or meta.get("file_path")
            )

            if isinstance(source_path, str):
                filename = os.path.basename(source_path.strip())

                if filename and filename.lower() not in ["unknown", "none"]:
                    if filename not in sources:
                        sources.append(filename)

        # --------------------------------------------------
        # 5️⃣ SMART CONTEXT BUILDING
        # --------------------------------------------------
        MAX_CONTEXT_CHARS = 5000
        context = ""
        chunks_used = 0

        for chunk in context_parts:
            if len(context) + len(chunk) > MAX_CONTEXT_CHARS:
                break
            context += chunk + "\n\n"
            chunks_used += 1

        # --------------------------------------------------
        # 6️⃣ WEAK CONTEXT GUARD
        # --------------------------------------------------
        if len(context.strip()) < 200:
            logger.warning("⚠️ Weak context detected")

            return {
                "question": question,
                "answer": "Not enough relevant information found in documents.",
                "sources": sources,
                "chunks_used": chunks_used,
                "context_preview": context[:500]
            }

        logger.info(f"Context size: {len(context)} | Chunks: {chunks_used}")

        # --------------------------------------------------
        # 7️⃣ LLM CALL
        # --------------------------------------------------
        answer = await ask_llm(question, context)

        logger.info("✅ Answer generated")

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "chunks_used": chunks_used,
            "context_preview": context[:500]
        }

    except Exception as e:
        logger.exception("❌ Query processing failed")

        return {
            "question": question,
            "answer": "I encountered an error while analyzing the documents.",
            "error": str(e),
            "sources": [],
            "chunks_used": 0,
            "context_preview": ""
        }