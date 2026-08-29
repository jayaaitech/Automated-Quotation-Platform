"""
RFQ AI System - Upload Router
Handles file uploads (PDFs, CAD, Excel) from the frontend sidebar. 
Saves the files to disk and triggers the extraction pipelines.
"""

import os
import shutil
import logging
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

# --- Models ---
from app.models.rfq_model import RFQRequest, RFQResponse

# --- Services ---
from app.brain.document_upload import add_document
from app.pipeline.rfq_pipeline import process_unstructured_file
from app.pipeline.quotation_pipeline import process_rfq_bundle

# --- Shared Memory ---
# 🧠 We import this so we can pass the extracted data to the chat/quote router!
from app.routers.query_router import GLOBAL_SESSION_MEMORY

# Set up logging and the router prefix
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["File Upload"])

# Ensure the upload directory exists when the server starts
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==========================================================
# 1️⃣ SINGLE RFQ PROCESSING (Unstructured Only)
# ==========================================================
@router.post("/process", response_model=RFQResponse)
async def process_rfq_request(request: RFQRequest):
    """
    Processes a single pre-existing unstructured file (like a PDF).
    """
    try:
        # Run the extraction pipeline on the single file
        result = await process_unstructured_file(request.file_path)

        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return RFQResponse(
            status="success",
            message="RFQ processed successfully",
            data=result
        )

    except Exception as e:
        logger.exception("❌ Single RFQ failed")
        raise HTTPException(
            status_code=500,
            detail=f"RFQ processing failed: {str(e)}"
        )


# ==========================================================
# 2️⃣ RFQ BUNDLE PROCESSING (Drag & Drop from UI)
# ==========================================================
@router.post("/bundle")
async def upload_rfq_bundle(
    project_name: str = Form("New RFQ Project"),
    files: List[UploadFile] = File(...)
):
    """
    Handles multiple files dropped into the UI sidebar. 
    Saves them, runs the master pipeline, and saves the extracted 
    items to memory so the user can generate a quote in the chat.
    """
    try:
        saved_paths = []

        # -------------------------------
        # Step 1: Save Files to Disk
        # -------------------------------
        for file in files:
            path = os.path.join(UPLOAD_DIR, file.filename)

            # Write the file chunk by chunk to avoid memory crashes on large CAD files
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(path)
            
            # Register the document in your vector DB / Document Tracker
            add_document(file.filename)

        logger.info(f"📂 Saved {len(saved_paths)} files")

        # -------------------------------
        # Step 2: Process the Bundle
        # -------------------------------
        # This routes the files to the Excel or CAD extractors 
        # based on their extensions and checks for conflicts.
        result = await process_rfq_bundle(
            project_name=project_name,
            file_paths=saved_paths
        )

        # -------------------------------
        # Step 3: 🧠 UPDATE GLOBAL MEMORY
        # -------------------------------
        # We need to flatten the grouped entities so the quote generator can read them
        extracted_items_for_quote = []
        
        if "grouped_entities" in result:
            for item_name, instances in result["grouped_entities"].items():
                if instances:
                    # Sum up the quantities if the same item appears multiple times
                    total_qty = sum(inst.get("quantity", 0) for inst in instances)
                    extracted_items_for_quote.append({
                        "item": item_name,
                        "quantity": total_qty,
                        "unit": "pcs" # Defaulting to pcs
                    })
        
        # Save to the dictionary that query_router.py is watching!
        GLOBAL_SESSION_MEMORY["current_boq_items"] = extracted_items_for_quote
        logger.info(f"✅ Saved {len(extracted_items_for_quote)} items to memory for quoting.")

        # -------------------------------
        # Step 4: Return Success to UI
        # -------------------------------
        return {
            "status": "success",
            "project": project_name,
            "files_processed": len(files),
            "summary": result.get("summary"),
            "conflicts": result.get("conflicts"),
            "message": "RFQ bundle processed successfully"
        }

    except Exception as e:
        logger.exception("❌ Bundle upload failed")
        raise HTTPException(
            status_code=500,
            detail=f"Bundle processing failed: {str(e)}"
        )