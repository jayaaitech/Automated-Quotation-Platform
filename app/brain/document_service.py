import os
import logging
from typing import List

# Extraction services
from app.services.pdf_service import extract_pdf
from app.services.docx_service import extract_docx
from app.services.csv_service import extract_csv
from app.services.excel_service import extract_boq_data
from app.services.text_service import extract_text
from app.services.cad_service import extract_dwg, summarize_dxf

# AI pipeline services
from app.brain.chunk_service import chunk_text
from app.brain.embedding_service import embed_texts
from app.brain.vector_service import store_vector, save_index, rebuild_bm25

from app.config import DWG_TEMP_DIR

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".csv", ".xlsx", ".xls", ".txt", ".dwg", ".dxf"
}


async def process_document(file_path: str) -> str:
    """
    Production-ready document processing pipeline:
    Extract → Normalize → Chunk → Embed → Store → Index
    """

    # --------------------------------------------------
    # 1️⃣ VALIDATION
    # --------------------------------------------------
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        raise ValueError("File exceeds maximum allowed size (10MB)")

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    try:
        chunks: List[str] = []
        clean_text = ""

        # --------------------------------------------------
        # 2️⃣ EXTRACTION + NORMALIZATION
        # --------------------------------------------------

        # ✅ EXCEL (BOQ Handling - FIXED)
        if ext in [".xlsx", ".xls"]:
            boq_data = extract_boq_data(file_path)

            if not boq_data:
                raise ValueError("No data extracted from Excel")

            for row in boq_data:
                if not row:
                    continue

                # 🔥 Normalize keys (VERY IMPORTANT)
                
                item = row.get("Item") or row.get("item") or ""
                desc = row.get("Material") or row.get("description") or ""
                qty = row.get("Quantity") or row.get("quantity") or ""
                unit = row.get("Unit") or row.get("unit") or ""

                text_chunk = f"Item {item}: {desc} | Qty: {qty} {unit}"
                chunks.append(text_chunk)

            clean_text = "\n".join(chunks)

            logger.info(f"📊 Excel processed → {len(chunks)} BOQ chunks")

        # ✅ OTHER FILE TYPES
        else:
            if ext == ".pdf":
                raw = extract_pdf(file_path)
            elif ext == ".docx":
                raw = extract_docx(file_path)
            elif ext == ".csv":
                raw = extract_csv(file_path)
            elif ext == ".txt":
                raw = extract_text(file_path)
            elif ext == ".dwg":
                raw = extract_dwg(file_path, DWG_TEMP_DIR)
            elif ext == ".dxf":
                raw = summarize_dxf(file_path, DWG_TEMP_DIR)
            else:
                raw = ""

            # Normalize extractor output
            if isinstance(raw, dict):
                text_chunks = raw.get("text_chunks", [])
                summary = raw.get("summary", "")
                clean_text = f"{summary}\n\n{' '.join(text_chunks)}"
            else:
                clean_text = str(raw)

            clean_text = clean_text.strip()

            if len(clean_text) < 10:
                raise ValueError("No meaningful text extracted")

            # Chunk text
            raw_chunks = chunk_text(clean_text)
            chunks = [c.strip() for c in raw_chunks if c and len(c.strip()) > 20]

            logger.info(f"📄 Text processed → {len(chunks)} chunks")

        # --------------------------------------------------
        # 3️⃣ VALIDATE CHUNKS
        # --------------------------------------------------
        if not chunks:
            raise ValueError("No valid chunks generated")

        logger.debug(f"Sample chunks: {chunks[:2]}")

        # --------------------------------------------------
        # 4️⃣ EMBEDDINGS
        # --------------------------------------------------
        embeddings = await embed_texts(chunks)
        if embeddings is None or len(embeddings) == 0:
             raise ValueError("Embedding generation failed")

        logger.info(f"🧠 Generated {len(embeddings)} embeddings")

        # --------------------------------------------------
        # 5️⃣ STORE VECTORS
        # --------------------------------------------------
        filename = os.path.basename(file_path)

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            store_vector(
                text=chunk,
                embedding=emb,
                metadata={
                    "source": file_path,
                    "file_name": filename,
                    "chunk_id": i
                }
            )

        # --------------------------------------------------
        # 6️⃣ INDEX UPDATE
        # --------------------------------------------------
        rebuild_bm25()
        save_index()

        logger.info(f"✅ Document indexed successfully: {filename}")

        return clean_text

    except Exception as e:
        logger.error(f"❌ Document processing failed: {file_path} | {e}", exc_info=True)
        raise RuntimeError(f"Document processing failed: {e}") from e