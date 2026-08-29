# ============================================================
# 🚀 ENTERPRISE VECTOR STORE (FAISS + BM25 + HYBRID + RERANK)
# ============================================================

import faiss
import numpy as np
import os
import re
import hashlib
import logging
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
SAVE_DIR = "./vectorstore"
INDEX_FILE = os.path.join(SAVE_DIR, "index.faiss")
DOCS_FILE = os.path.join(SAVE_DIR, "docs.npy")

DIMENSION = 3072  # MUST match embedding model

os.makedirs(SAVE_DIR, exist_ok=True)

# ------------------------------------------------------------
# GLOBAL STATE
# ------------------------------------------------------------
index = faiss.IndexFlatIP(DIMENSION)  # cosine similarity via normalization
documents = []
document_hashes = set()
bm25 = None

# 🔥 RERANKER
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ============================================================
# HELPERS
# ============================================================

def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def _normalize(vec):
    """
    Normalize embedding for cosine similarity
    """
    vec = np.array([vec]).astype("float32")

    if vec.shape[1] != DIMENSION:
        raise ValueError(f"Embedding dimension mismatch: expected {DIMENSION}, got {vec.shape[1]}")

    faiss.normalize_L2(vec)

    # 🔍 Debug (optional)
    # print("Norm:", np.linalg.norm(vec))

    return vec


def rebuild_bm25():
    global bm25

    if not documents:
        logger.warning("No documents for BM25")
        return

    tokenized = [_tokenize(doc["text"]) for doc in documents]
    bm25 = BM25Okapi(tokenized)

    logger.info("✅ BM25 rebuilt")


# ============================================================
# STORAGE
# ============================================================

def store_vector(text: str, embedding, metadata=None):
    global index, documents, document_hashes

    # ✅ Safe checks
    if embedding is None or len(embedding) == 0:
        logger.warning("⚠️ Empty embedding skipped")
        return

    metadata = metadata or {}
    text_hash = _hash(text)

    if text_hash in document_hashes:
        logger.info("🔁 Duplicate skipped")
        return

    # ✅ NORMALIZATION HERE
    vector = _normalize(embedding)

    index.add(vector)

    documents.append({
        "text": text,
        "hash": text_hash,
        "metadata": metadata
    })

    document_hashes.add(text_hash)

    logger.info(f"✅ Stored | Total docs: {len(documents)}")


# ============================================================
# SEARCH
# ============================================================

def search_vector(query_embedding, top_k=10):
    if index.ntotal == 0:
        logger.warning("⚠️ FAISS index empty")
        return []

    # ✅ NORMALIZATION HERE (VERY IMPORTANT)
    vector = _normalize(query_embedding)

    distances, indices = index.search(vector, top_k)

    return [
        documents[i]
        for i in indices[0]
        if i != -1 and i < len(documents)
    ]


def keyword_search(query: str, top_k=10):
    if bm25 is None:
        logger.warning("⚠️ BM25 not initialized")
        return []

    scores = bm25.get_scores(_tokenize(query))
    ranked = np.argsort(scores)[::-1][:top_k]

    return [documents[i] for i in ranked if scores[i] > 0]


def hybrid_search(query: str, query_embedding, top_k=10, alpha=0.7):
    v_results = search_vector(query_embedding, top_k=10)
    k_results = keyword_search(query, top_k=10)

    if not v_results and not k_results:
        logger.warning("❌ No results from both searches")
        return []

    scores = {}

    # Vector scoring
    for rank, doc in enumerate(v_results):
        scores[doc["hash"]] = scores.get(doc["hash"], 0) + alpha * (1 / (rank + 1))

    # Keyword scoring
    for rank, doc in enumerate(k_results):
        scores[doc["hash"]] = scores.get(doc["hash"], 0) + (1 - alpha) * (1 / (rank + 1))

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for doc_hash, _ in ranked[:top_k]:
        doc = next(d for d in documents if d["hash"] == doc_hash)
        results.append(doc)

    logger.info(f"🔎 Hybrid results: {len(results)}")

    return results


# ============================================================
# RERANKING
# ============================================================

def rerank(query: str, docs: list, top_k=5):
    if not docs:
        return []

    pairs = [(query, doc["text"]) for doc in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in ranked[:top_k]]


# ============================================================
# CONTEXT BUILDER
# ============================================================

def format_context(results):
    formatted = []
    for i, doc in enumerate(results):
        formatted.append(f"[Chunk {i+1}]\n{doc['text']}")
    return "\n\n".join(formatted)


# ============================================================
# RAG PIPELINE
# ============================================================

def retrieve_context(query: str, embedding_fn, top_k=5):
    query_embedding = embedding_fn(query)

    # Step 1: Hybrid search
    results = hybrid_search(query, query_embedding, top_k=10)

    if not results:
        return ""

    # Step 2: Rerank
    results = rerank(query, results, top_k=top_k)

    # Step 3: Format context
    context = format_context(results)

    return context


# ============================================================
# PERSISTENCE
# ============================================================

def save_index():
    faiss.write_index(index, INDEX_FILE)
    np.save(DOCS_FILE, np.array(documents, dtype=object))
    logger.info("💾 Index saved")


def load_index():
    global index, documents, document_hashes

    if os.path.exists(INDEX_FILE) and os.path.exists(DOCS_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            documents = list(np.load(DOCS_FILE, allow_pickle=True))
            document_hashes = {doc["hash"] for doc in documents}

            rebuild_bm25()
            logger.info(f"📦 Loaded {len(documents)} documents")

        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
    else:
        logger.warning("⚠️ No existing index found")


# ============================================================
# DEBUG
# ============================================================

def debug_stats():
    logger.info(f"📊 FAISS size: {index.ntotal}")
    logger.info(f"📊 Documents: {len(documents)}")


# ============================================================
# INIT
# ============================================================

load_index()