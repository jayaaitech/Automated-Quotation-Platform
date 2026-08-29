"""
RFQ AI System - Core Pipeline Orchestrator
This module handles file processing (Excel, PDFs, CAD), extracts entities, 
detects conflicts, and generates the final chat-ready quotation HTML.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

# Adjust these import paths based on your actual project folder structure
from app.services.excel_service import extract_boq_data
from app.brain.conflict_engine import detect_conflicts
from app.pipeline.rfq_pipeline import process_unstructured_file
from app.qoute_service.cost_service import estimate_cost
from app.qoute_service.quotation_service import generate_quote 

# Set up logging for debugging
logger = logging.getLogger(__name__)

# Define supported file extensions for routing
EXCEL_EXTS = {"xlsx", "xls"}
UNSTRUCTURED_EXTS = {"pdf", "dwg", "dxf"}


# ==========================================
# 1. QUOTATION GENERATION (CHAT UI)
# ==========================================

def generate_chat_quotation(boq_items: list, project_name: str = "RFQ Project") -> dict:
    """
    Takes a list of BOQ items, runs them through the cost and pricing services, 
    and outputs a formatted HTML table ready to be displayed in the frontend chat.
    """
    if not boq_items:
        return {
            "error": "No items found to quote.", 
            "html_view": "❌ No items found in the uploaded documents."
        }

    # Step 1: Run your Cost Estimator to get raw costs
    logger.info("Running cost estimation...")
    cost_data = estimate_cost(boq_items=boq_items)

    # Step 2: Apply business logic (Labor, Profit margins) to generate final quote
    logger.info("Generating final quote data...")
    final_quote = generate_quote(cost_data, labor_rate=0.15, profit_rate=0.10)

    if final_quote.get("status") == "error":
        return {"error": "Quote generation failed", "html_view": "❌ Error generating quote."}

    # Step 3: Extract metadata and format the output into an HTML Table
    meta = final_quote["metadata"]
    summary = final_quote["summary"]
    
    # Format the timestamp into a readable date (e.g., "March 22, 2026")
    date_str = datetime.fromisoformat(meta["generated_at"].replace('Z', '+00:00')).strftime("%B %d, %Y")

    html_output = f"""
    <div class="quote-header" style="margin-bottom: 15px;">
        <h3>📄 Official Quotation</h3>
        <p><strong>Quote ID:</strong> {meta["quote_id"]}</p>
        <p><strong>Date:</strong> {date_str}</p>
    </div>
    
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Unit Cost</th>
                    <th>Total</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    """

    # Populate the table rows dynamically
    for item in final_quote["line_items"]:
        # Add a visual warning if the price was not found in the CSV database
        status_icon = "✅" if item["verified"] else "⚠️ Manual Review"
        row_color = "" if item["verified"] else "background-color: #fff3cd;"

        html_output += f"""
                <tr style="{row_color}">
                    <td>{item['item_name']}</td>
                    <td>{item['quantity']}</td>
                    <td>${item['unit_cost']:,.2f}</td>
                    <td><strong>${item['total_cost']:,.2f}</strong></td>
                    <td style="font-size: 0.8em;">{status_icon}</td>
                </tr>
        """

    # Add the final summary and download button
    html_output += f"""
            </tbody>
        </table>
    </div>
    <div class="quote-summary" style="margin-top: 15px; text-align: right;">
        <p>Material Subtotal: ${summary['material_subtotal']:,.2f}</p>
        <p>Labor & Handling: ${summary['labor_cost']:,.2f}</p>
        <p>Profit Margin: ${summary['profit_markup']:,.2f}</p>
        <p style="font-size: 0.9em; color: gray;">Estimated Tax (5%): ${summary['tax_estimate']:,.2f}</p>
        <h2 style="color: var(--primary-color); margin-top: 10px;">Grand Total: ${summary['total_quote']:,.2f}</h2>
        <button id="downloadPdfBtn" class="action-btn" style="margin-top: 15px;">💾 Download PDF</button>
    </div>
    """

    # Return both raw JSON data (for PDF downloads) and HTML (for the UI)
    return {
        "raw_quote_data": final_quote,
        "html_view": html_output
    }


# ==========================================
# 2. DATA CLEANING HELPERS
# ==========================================

def safe_int(val, default=1):
    """Safely converts various data types (pandas/numpy items, lists, strings) into an integer."""
    try:
        if hasattr(val, "item"): # Handles numpy/pandas datatypes
            val = val.item()
        if isinstance(val, (list, tuple)): # Extracts first item if it's a list
            val = val[0] if val else default
        return int(val)
    except:
        return default

def normalize(item, qty, source, etype, path):
    """Standardizes dictionary keys for extracted items so they match across CAD, PDF, and Excel."""
    return {
        "item": str(item).lower().strip() or "unknown",
        "quantity": safe_int(qty),
        "source": source,
        "type": etype,
        "file_path": path,
    }

def deduplicate(entities):
    """Removes duplicate items extracted from the same file."""
    seen, result = set(), []
    for e in entities:
        key = (e["item"], e["type"], e["file_path"])
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result

def group_by_item(entities):
    """Groups matching items from different files together (useful for finding conflicts)."""
    grouped = defaultdict(list)
    for e in entities:
        grouped[e["item"]].append(e)
    return grouped


# ==========================================
# 3. EXCEL FILE PROCESSOR
# ==========================================

def process_excel_boq(path: Path):
    """Reads an Excel BOQ file and normalizes the items for the main pipeline."""
    boq_data = extract_boq_data(str(path))
    entities = []

    # Map the raw Excel data to our standard system schema
    for item in boq_data.get("conflict_items", []):
        entities.append(
            normalize(
                item.get("item"),
                item.get("quantity"),
                f"BOQ ({path.name})",
                "BOQ",
                str(path),
            )
        )

    # Create pseudo-chunks for vector embeddings (RAG)
    chunks = [f"{e['item']} x{e['quantity']}" for e in entities]

    return entities, chunks


# ==========================================
# 4. MAIN ORCHESTRATOR
# ==========================================

async def process_rfq_bundle(project_name: str, file_paths: List[str]) -> Dict[str, Any]:
    """
    The master function. Takes a list of uploaded files, determines their type, 
    routes them to the correct extraction service, checks for conflicts, 
    and bundles the data together.
    """
    all_entities = []
    results = []

    for file_path in file_paths:
        path = Path(file_path)
        ext = path.suffix.lower().lstrip(".")
        filename = path.name

        try:
            # File validation
            if not path.exists() or path.stat().st_size == 0:
                raise ValueError("Invalid or empty file")

            # Route 1: Structured Excel Data
            if ext in EXCEL_EXTS:
                entities, chunks = process_excel_boq(path)
                status = "processed_boq"

            # Route 2: Unstructured PDFs and CAD Drawings
            elif ext in UNSTRUCTURED_EXTS:
                result = await process_unstructured_file(str(path))

                if result.get("status") != "success":
                    msg = result.get("message") or "Unstructured extraction failed"
                    raise ValueError(str(msg))

                entities = result.get("entities", [])
                chunks = result.get("chunks", [])
                status = "processed_unstructured"

            # Unsupported file types
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            # Log successful file processing
            results.append({
                "file": filename,
                "status": status,
                "entities": entities,
                "chunks": chunks
            })

            all_entities.extend(entities)

        except Exception as e:
            # Log failed file processing without crashing the whole bundle
            logger.error(f"{filename} failed: {e}")
            results.append({
                "file": filename,
                "status": "error",
                "message": str(e),
                "entities": [],
                "chunks": []
            })

    # Data Cleanup & Analysis Step
    all_entities = deduplicate(all_entities)
    grouped = group_by_item(all_entities)

    # Run the Conflict Engine (e.g., checks if CAD says 5 doors but BOQ says 4)
    try:
        conflicts = detect_conflicts(all_entities)
    except Exception as e:
        conflicts = {"error": str(e)}

    # Return the final comprehensive bundle report
    return {
        "project_name": project_name,
        "summary": {
            "files": len(file_paths),
            "entities": len(all_entities)
        },
        "documents": results,
        "grouped_entities": grouped,
        "conflicts": conflicts
    }