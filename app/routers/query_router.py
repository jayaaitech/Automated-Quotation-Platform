"""
RFQ AI System - Query & Chat Router
Handles all user questions from the frontend chat UI, routing them to either
the Document Q&A (RAG) pipeline or the Quotation generation pipeline.
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import your pipelines and models
from app.pipeline.query_pipeline import ask_rfq
from app.pipeline.quotation_pipeline import generate_chat_quotation
from app.models.query_model import QueryResponse

logger = logging.getLogger(__name__)

# Define the router with a prefix so all routes start with /query
router = APIRouter(prefix="/query", tags=["Query & Chat"])

# ==========================================================
# 🧠 TEMPORARY MEMORY (Replace with a Database/Redis later!)
# ==========================================================
# This stores the extracted items from the upload router 
# so the query router can access them when the user asks for a quote.
GLOBAL_SESSION_MEMORY = {
    "current_boq_items": []
}

class QueryRequest(BaseModel):
    """Schema for incoming chat requests."""
    question: str
    
    
# ==========================================================
# 💬 ENDPOINT 1: MAIN CHAT ROUTER (Q&A + QUOTES)
# ==========================================================
@router.post("/ask")
async def ask_question(request: QueryRequest):
    """
    Listens to the frontend chat. 
    If the user asks for a quote, it builds an HTML table. 
    Otherwise, it answers normally using the Document Q&A pipeline.
    """
    question = request.question.lower().strip()
    
    try:
        # --------------------------------------------------
        # MODE A: QUOTE GENERATION
        # --------------------------------------------------
        if "generate" in question and ("quotation" in question or "quote" in question):
            logger.info("Quote requested via chat UI.")
            
            # Fetch the items we extracted during the file upload step
            boq_items = GLOBAL_SESSION_MEMORY.get("current_boq_items", [])
            
            # Fallback test data if no files were uploaded yet
            if not boq_items:
                logger.warning("No BOQ items in memory. Using test data.")
                boq_items = [
                    {"item": "10mm Steel Pipe", "quantity": 50, "unit": "pcs"},
                    {"item": "20mm Steel Pipe", "quantity": 10, "unit": "pcs"}
                ]
            
            # Run the pipeline to calculate costs and get the HTML table
            result = generate_chat_quotation(boq_items=boq_items)
            
            if "error" in result:
                return {"answer": result["html_view"], "result": None}
            
            # Return the HTML for the chat UI, and raw data for PDF export
            return {
                "answer": result["html_view"],
                "result": result["raw_quote_data"] 
            }
            
        # --------------------------------------------------
        # MODE B: STANDARD DOCUMENT Q&A (RAG)
        # --------------------------------------------------
        else:
            logger.info("Standard Q&A requested.")
            # Call your existing Document Q&A pipeline
            result = await ask_rfq(request.question)
            return {
                "answer": result.get("answer", "No answer found."),
                "sources": result.get("sources", [])
            }

    except Exception as e:
        logger.exception("❌ Error processing chat query")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# 🔥 ENDPOINT 2: STREAMING QUERY (SSE - PRODUCTION READY)
# ==========================================================
@router.post("/stream")
async def query_stream(request: QueryRequest):
    """
    A streaming endpoint for Q&A. This sends the answer back in chunks 
    so the frontend chat can show the "typing" effect.
    """
    async def generate():
        try:
            # Step 1: Run the standard Q&A pipeline
            result = await ask_rfq(request.question)

            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Step 2: Stream answer in chunks (simulate token streaming)
            for i in range(0, len(answer), 50):
                chunk = answer[i:i+50]
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Step 3: Send final metadata (sources) when finished
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

        except Exception as e:
            # Stream error messages back to the client
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")