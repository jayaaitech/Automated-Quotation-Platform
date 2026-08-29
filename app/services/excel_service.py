import pandas as pd
import logging
import re

logger = logging.getLogger(__name__)

ROWS_PER_CHUNK = 20
MAX_CHARS = 2000

IMPORTANT_COL_KEYWORDS = [
    "item", "description", "material",
    "qty", "quantity", "unit", "remarks"
]

def parse_quantity(val):
    if pd.isna(val) or val == "":
        return None
    match = re.search(r"\d+(\.\d+)?", str(val).replace(",", ""))
    return float(match.group()) if match else None

def extract_boq_data(file_path: str) -> dict:
    try:
        sheets = pd.read_excel(file_path, sheet_name=None)
    except Exception as e:
        logger.exception(f"Failed to read Excel file {file_path}")
        raise ValueError(f"Failed to read Excel file: {e}")

    structured_items = []
    text_chunks = []

    for sheet_name, df in sheets.items():
        df = df.dropna(how='all').dropna(axis=1, how='all')
        if df.empty:
            continue

        # 1. DYNAMIC HEADER DETECTION
        # Check if current columns look like headers. If not, scan rows to find the real header.
        cols_str = " ".join(str(c).lower() for c in df.columns)
        if not any(k in cols_str for k in ["item", "description", "qty", "quantity"]):
            for idx, row in df.iterrows():
                row_str = " ".join(str(v).lower() for v in row.values)
                if any(k in row_str for k in ["item", "description"]) and any(k in row_str for k in ["qty", "quantity"]):
                    df.columns = row.values # Set new headers
                    df = df.iloc[idx+1:].reset_index(drop=True) # Drop everything above header
                    break
        
        # Clean up column names after finding the header
        df.columns = [str(c).strip() for c in df.columns]

        # 2. COLUMN FILTERING
        filtered_cols = [
            c for c in df.columns
            if any(k in str(c).lower() for k in IMPORTANT_COL_KEYWORDS)
        ]
        
        if filtered_cols:
            df_filtered = df[filtered_cols].fillna("")
        else:
            df_filtered = df.fillna("") # Fallback if keywords still fail

        # 3. DETECT TARGET COLUMNS
        item_col = next((c for c in df_filtered.columns if "item" in str(c).lower() or "description" in str(c).lower()), None)
        qty_col = next((c for c in df_filtered.columns if "qty" in str(c).lower() or "quantity" in str(c).lower()), None)
        unit_col = next((c for c in df_filtered.columns if "unit" in str(c).lower()), None)

        # 4. STRUCTURED EXTRACTION (For Costing/Conflict check)
        if item_col and qty_col:
            for _, row in df_filtered.iterrows():
                item_val = str(row[item_col]).strip()
                qty = parse_quantity(row[qty_col])
                unit_val = str(row[unit_col]).strip() if unit_col else "pcs"

                # Ignore empty rows or rows that just say "Total"
                if item_val and qty is not None and "total" not in item_val.lower():
                    structured_items.append({
                        "item": item_val,
                        "quantity": qty,
                        "unit": unit_val,
                        "source": f"Excel BOQ ({sheet_name})"
                    })

        # 5. CHUNKING FOR RAG (For Document Analysis Q&A)
        for i in range(0, len(df_filtered), ROWS_PER_CHUNK):
            chunk_df = df_filtered.iloc[i:i + ROWS_PER_CHUNK]
            md_table = chunk_df.to_markdown(index=False)

            chunk_text = (
                f"Excel BOQ Data | Sheet: {sheet_name} | Rows: {i+1}-{i+len(chunk_df)}\n\n"
                f"{md_table}"
            )

            if len(chunk_text) > MAX_CHARS:
                chunk_text = chunk_text[:MAX_CHARS]

            text_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "sheet": sheet_name,
                    "row_range": f"{i+1}-{i+len(chunk_df)}",
                    "type": "excel_boq",
                    "file": file_path
                }
            })

    return {
        "conflict_items": structured_items,
        "text_chunks": text_chunks
    }