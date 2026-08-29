"""
RFQ AI System - Main Application Entry Point
Wires together all routers, static files, and background services.
"""

import os
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --- Routers ---
from app.routers import upload_router
from app.routers import query_router
from app.routers import document_router
from app.routers import export_router

# --- Vector Store ---
from app.brain.vector_service import load_index, save_index

# --- Config ---
from app.config import UPLOAD_DIR, APP_NAME, EMBEDDING_MODEL, OPENAI_API_KEY

# =========================================================
# 📝 LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# =========================================================
# 🚀 APP INIT
# =========================================================
app = FastAPI(title=APP_NAME)

# =========================================================
# 🌐 CORS (PRODUCTION SAFE)
# =========================================================
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ⚠️ Set in ENV for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 🟢 STARTUP EVENT
# =========================================================
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 40)
    logger.info(f"🚀 Starting {APP_NAME}")
    logger.info("=" * 40)

    # 1. Validate API Key
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OpenAI API key not set. LLM features may fail.")

    # 2. Ensure directories exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"📁 Upload dir ready: {UPLOAD_DIR}")

    # 3. Load vector index
    try:
        load_index()
        logger.info("📦 Vector index loaded")
    except Exception as e:
        logger.warning(f"⚠️ Index load failed: {e}")

    logger.info(f"🧠 Embedding model: {EMBEDDING_MODEL}")
    logger.info("✅ System ready")

# =========================================================
# 🛑 SHUTDOWN EVENT
# =========================================================
@app.on_event("shutdown")
async def shutdown_event():
    try:
        logger.info("💾 Saving vector index...")
        save_index()
        logger.info("✅ Index saved")
    except Exception as e:
        logger.error(f"❌ Failed saving index: {e}")

# =========================================================
# ❤️ HEALTH CHECK
# =========================================================
@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "ok",
        "service": APP_NAME
    })

# =========================================================
# 🔌 REGISTER ROUTERS
# =========================================================
# Note: quote_router has been successfully merged into query_router
app.include_router(document_router.router)
app.include_router(upload_router.router)
app.include_router(query_router.router)
app.include_router(export_router.router)

# =========================================================
# 📁 STATIC FILES & FRONTEND
# =========================================================
STATIC_DIR = "app/web"

# Mount the static directory so the HTML can load app.js and style.css
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning(f"⚠️ Static directory not found at {STATIC_DIR}")

@app.get("/")
async def serve_frontend():
    """Serves the main Chat/Upload UI on the root URL."""
    index_path = os.path.join(STATIC_DIR, "index.html")

    if not os.path.exists(index_path):
        return JSONResponse({
            "error": "Frontend not found. Please ensure index.html is in app/web."
        }, status_code=404)

    return FileResponse(index_path)