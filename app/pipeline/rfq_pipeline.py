import os
import logging

from app.brain.document_service import process_document
from app.extraction.bom_extractor import extract_bom
from app.extraction.spec_extractor import extract_specs
from app.extraction.table_extractor import extract_tables
from app.brain.chunk_service import chunk_text
from app.brain.embedding_service import embed_texts
from app.brain.vector_service import store_vector, rebuild_bm25, save_index
from app.services.cad_service import extract_dwg
from app.config import UPLOAD_DIR

logger = logging.getLogger(__name__)


# -------------------------------
# CHUNK CLASSIFIER (optimized)
# -------------------------------
def classify_chunk(chunk: str) -> str:
    chunk = chunk.lower()

    if any(k in chunk for k in ["qty", "quantity", "price"]):
        return "boq"
    if any(k in chunk for k in ["spec", "material", "standard"]):
        return "spec"
    if "|" in chunk or "\t" in chunk:
        return "table"

    return "general"


# -------------------------------
# ENTITY BUILDER
# -------------------------------
def build_entities(bom, cad_entities, filename, path):
    entities = []

    for item in bom:
        entities.append({
            "item": item.get("item", "unknown"),
            "quantity": item.get("quantity"),
            "type": "BOM",
            "source": filename,
            "file_path": path
        })

    for c in cad_entities:
        entities.append({
            "item": c.get("item", "unknown"),
            "quantity": c.get("qty"),
            "type": "CAD",
            "source": filename,
            "file_path": path
        })

    return entities


# -------------------------------
# MAIN DOCUMENT PROCESSOR
# -------------------------------
async def process_unstructured_file(file_path: str):

    try:
        filename = os.path.basename(file_path)
        # 1️⃣ Extract text
        text = await process_document(file_path)
        if not text:
            raise ValueError("empty text")

        # 2️⃣ Structured extraction
        bom = extract_bom(text)
        specs = extract_specs(text)
        tables = extract_tables(text)

        # 3️⃣ Chunking
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("no chunks")

        # 4️⃣ Embeddings
        embeddings = await embed_texts(chunks)
        if embeddings is None or len(embeddings) == 0:   # ✅ FIXED
            raise ValueError("no embeddings")

        # 5️⃣ Vector storage
        stored = 0
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):

            if len(chunk.strip()) < 30:
                continue

            try:
                store_vector(
                    text=chunk,
                    embedding=emb,
                    metadata={
                        "file": filename,
                        "chunk_id": i,
                        "type": classify_chunk(chunk),
                        "source": file_path,
                    }
                )
                stored += 1
            except Exception as e:
                print(f"Vector error: {e}")   # better debugging

        rebuild_bm25()
        save_index()

       
        # 6️⃣ CAD (optional)
        cad_entities = []
        if file_path.endswith(".dwg"):
            cad = extract_dwg(file_path, UPLOAD_DIR)
            cad_entities = cad.get("parsed_entities", [])

        # 7️⃣ Build unified entities
        entities = build_entities(bom, cad_entities, filename, file_path)

        return {
            "status": "success",
            "entities": entities,
            "chunks_stored": stored,
            "specs": specs,
            "tables": tables
        }

    except Exception as e:
        logger.error(f"RFQ failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }