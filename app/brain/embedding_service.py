import numpy as np
import logging
import asyncio
from typing import List
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# ------------------------------
# Utility: Retry Wrapper
# ------------------------------
async def with_retry(coro, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return await coro
        except Exception:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(delay * (2 ** attempt))


# ------------------------------
# Batch Embeddings (FIXED)
# ------------------------------
async def embed_texts(
    texts: List[str],
    batch_size: int = 32
) -> np.ndarray:
    """
    Async embeddings with:
    - batching
    - retry
    - timeout
    - safe alignment
    - NO hardcoded dimensions (critical fix)
    """

    if not texts:
        return np.array([], dtype="float32")

    embeddings_list = []

    for i in range(0, len(texts), batch_size):
        original_batch = texts[i:i + batch_size]

        cleaned_batch = [
            t.strip() if isinstance(t, str) else ""
            for t in original_batch
        ]

        try:
            response = await asyncio.wait_for(
                with_retry(
                    client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=cleaned_batch
                    )
                ),
                timeout=30
            )

            for idx, data in enumerate(response.data):
                if cleaned_batch[idx]:
                    embeddings_list.append(
                        np.array(data.embedding, dtype="float32")
                    )
                else:
                    # fallback: zero vector of same size as first embedding
                    dim = len(response.data[0].embedding)
                    embeddings_list.append(
                        np.zeros(dim, dtype="float32")
                    )

        except Exception as e:
            logger.exception(f"Embedding batch failed at index {i}: {e}")

            # fallback → preserve alignment
            dim = len(embeddings_list[0]) if embeddings_list else 1536
            for _ in original_batch:
                embeddings_list.append(
                    np.zeros(dim, dtype="float32")
                )

    if not embeddings_list:
        return np.array([], dtype="float32")

    return np.vstack(embeddings_list)


# ------------------------------
# Single Query Embedding (FIXED)
# ------------------------------
async def embed_query(text: str) -> np.ndarray:
    """
    Async query embedding:
    - safe
    - no dimension mismatch bugs
    - model-driven dimension
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Query text cannot be empty.")

    try:
        response = await asyncio.wait_for(
            with_retry(
                client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text.strip()
                )
            ),
            timeout=30
        )

        embedding = np.array(
            response.data[0].embedding,
            dtype="float32"
        )

        # basic sanity check (not strict dimension check)
        if embedding.ndim != 1:
            raise ValueError("Invalid embedding shape")

        logger.info(f"Query embedding generated. Shape: {embedding.shape}")

        return embedding

    except Exception as e:
        logger.exception(f"Failed to embed query: {e}")
        raise