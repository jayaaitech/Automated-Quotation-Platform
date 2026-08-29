from fastapi import APIRouter
from app.brain.document_upload import get_documents
from app.brain.vector_service import debug_stats

router = APIRouter(prefix="/documents")


# ----------------------------------------------------------
# 📄 LIST DOCUMENTS
# ----------------------------------------------------------
@router.get("/")
def list_documents():
    docs = get_documents()

    return {
        "total_documents": len(docs),
        "documents": docs
    }


# ----------------------------------------------------------
# 🧠 VECTOR DB STATS (VERY USEFUL)
# ----------------------------------------------------------
@router.get("/stats")
def get_vector_stats():
    stats = debug_stats()

    return {
        "status": "success",
        "vector_store": stats
    }