# 🤖 RFQ Intelligence & Automated Quotation Platform

AI-powered engineering document intelligence system for **RFQ analysis, BOQ extraction, RAG-based question answering, cross-document conflict detection, cost estimation, and automated quotation generation**.

The system combines multiple engineering document processing workflows with a **hybrid RAG pipeline** and an automated **cost & quotation engine** through a FastAPI-based web application.

---

## ✨ Key Features

### 📄 Multi-Format Engineering Document Processing

Process engineering and RFQ documents across multiple formats:

* Excel (`.xlsx`, `.xls`)
* PDF
* CSV
* DOCX
* TXT
* DWG
* DXF

The system extracts usable information from uploaded documents and prepares it for downstream RFQ analysis.

---

### 📊 Intelligent BOQ / BOM Extraction

Automatically extract important information from engineering BOQ/BOM documents.

* BOQ item extraction
* Quantity extraction
* Material identification
* Specification extraction
* Table extraction
* Processing of messy and unstructured Excel sheets

---

### 🧠 RAG-Based Document Intelligence

The system uses a Retrieval-Augmented Generation pipeline to answer questions using information from uploaded RFQ documents.

#### RAG Pipeline

```text
Upload RFQ Files
       ↓
Document Extraction
       ↓
Text / BOQ / CAD Processing
       ↓
Text Chunking
       ↓
OpenAI Embeddings
       ↓
FAISS + BM25
       ↓
Hybrid Retrieval
       ↓
CrossEncoder Reranking
       ↓
Context Construction
       ↓
OpenAI LLM
       ↓
Answer + Sources
```

### Retrieval Components

**FAISS**

Used for semantic similarity search using OpenAI embeddings.

**BM25**

Used for keyword-based retrieval.

**Hybrid Retrieval**

Combines semantic and keyword retrieval:

```text
FAISS Vector Search → 70%
BM25 Keyword Search → 30%
```

**CrossEncoder**

Reranks retrieved candidates according to their relevance to the user's question before the final context is sent to the LLM.

---

### 💬 Conversational RFQ Analysis

Users can interact with uploaded documents through the web interface.

Example questions:

```text
List all items from the BOQ with their quantities.

Are there any conflicts between the CAD drawings and the BOQ?

What are the fire safety standards required by the specifications?
```

The system retrieves relevant document context and generates an answer using the configured OpenAI model.

---

### 🔍 Engineering Conflict Detection

The conflict engine compares engineering information across different document sources.

#### Conflict Detection Workflow

```text
Extract Entity
     ↓
Normalize Item Name
     ↓
Fuzzy Match Similar Items
     ↓
Extract Numbers / Dimensions
     ↓
Validate Numeric Compatibility
     ↓
Compare Quantities
     ↓
 ┌───────────────┐
 │               │
 ▼               ▼
MATCH         CONFLICT
```

Example:

```text
BOQ.xlsx
Steel Pipe → 50

Specification.pdf
Steel Pipe → 60

Result:
CONFLICT
```

The conflict analysis provides:

* Total entities checked
* Conflicts found
* Conflict details
* Cross-document comparison results
* Comparison matrix

---

### 💰 Automated Cost Estimation

The quotation workflow uses extracted BOQ entities and the material pricing database.

#### Cost Calculation

```text
BOQ Item
   ↓
Material Price Lookup
   ↓
Quantity × Unit Price
   ↓
Material Cost
   ↓
Labor Cost
   ↓
Profit
   ↓
Final Quote
```

Material cost:

```text
Item Cost = Quantity × Unit Price
```

If a matching price cannot be found, the item is marked for manual review.

Current calculation defaults:

```text
Labor = 15%
Profit = 10%
```

---

### 🧾 Automated Quotation Generation

The system generates a structured quotation from the processed BOQ and calculated costs.

Generated quotation information includes:

* Quote ID
* Generation date
* Line items
* Quantity
* Unit price
* Material subtotal
* Labor cost
* Profit
* Final quote total
* Price verification status

---

### 📑 PDF Quotation Export

Generated quotations can be exported as professional PDF documents directly from the application.

```text
RFQ / BOQ
   ↓
Cost Estimation
   ↓
Quotation
   ↓
PDF Generation
   ↓
Download
```

---

### 📐 CAD Processing

The system supports engineering CAD workflows involving:

* DWG files
* DXF files
* DWG → DXF conversion
* DXF entity parsing

CAD information can participate in engineering document analysis and cross-document conflict detection.

DWG processing requires the **ODA File Converter**.

---

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │     Web Frontend      │
                         │    HTML / CSS / JS    │
                         └───────────┬──────────┘
                                     │
                                     ▼
                         ┌──────────────────────┐
                         │      FastAPI API     │
                         └───────────┬──────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
       Document Upload          RAG Query             Quotation
              │                      │                      │
              ▼                      ▼                      ▼
        Document Services       Hybrid Search         Cost Service
              │                      │                      │
              ▼                      ▼                      ▼
          Extraction            FAISS + BM25          Price Database
              │                      │                      │
              ▼                      ▼                      ▼
           Chunking             CrossEncoder           Quote Engine
              │                      │                      │
              ▼                      │                      │
         Embeddings                  │                      │
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     ▼
                              ┌──────────────┐
                              │  OpenAI API  │
                              └──────────────┘
```

---

## 🔄 Main Workflows

### Document RAG Workflow

```text
Upload
  ↓
Extract
  ↓
Chunk
  ↓
Embed
  ↓
FAISS + BM25
  ↓
Retrieve
  ↓
Rerank
  ↓
Generate Answer
  ↓
Return Sources
```

### RFQ Quotation Workflow

```text
Upload RFQ
    ↓
BOQ Extraction
    ↓
Engineering Analysis
    ↓
Conflict Detection
    ↓
Material Price Lookup
    ↓
Material Cost
    ↓
Labor
    ↓
Profit
    ↓
Quotation
    ↓
PDF Export
```

---

## 📂 Project Structure

```text
RFQ-AI-System-main/
│
├── app/
│   │
│   ├── main.py
│   ├── config.py
│   │
│   ├── brain/
│   │   ├── conflict_engine.py
│   │   ├── document_service.py
│   │   ├── document_upload.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   └── vector_service.py
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── bom_extractor.py
│   │   ├── spec_extractor.py
│   │   └── table_extractor.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── query_model.py
│   │   └── rfq_model.py
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── query_pipeline.py
│   │   ├── quotation_pipeline.py
│   │   └── rfq_pipeline.py
│   │
│   ├── qoute_service/
│   │   ├── __init__.py
│   │   ├── cost_service.py
│   │   ├── price_service.py
│   │   └── quotation_service.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── document_router.py
│   │   ├── export_router.py
│   │   ├── query_router.py
│   │   └── upload_router.py
│   │
│   └── services/
│       ├── cad_service.py
│       ├── csv_service.py
│       ├── docx_service.py
│       ├── excel_service.py
│       ├── export_service.py
│       ├── pdf_service.py
│       └── text_service.py
│
├── data/
│   └── material_prices.csv
│
├── web/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── uploads/
├── vectorstore/
├── temp_dxf/
│
├── requirements.txt
└── .env
```

---

## 🔌 API Endpoints

| Method | Endpoint            | Purpose                             |
| ------ | ------------------- | ----------------------------------- |
| `GET`  | `/health`           | Health check                        |
| `GET`  | `/documents/`       | List uploaded documents             |
| `GET`  | `/documents/stats`  | Vector/document statistics          |
| `POST` | `/upload/bundle`    | Upload and process RFQ files        |
| `POST` | `/query/ask`        | RAG question / quotation generation |
| `POST` | `/query/stream`     | SSE-style answer response           |
| `POST` | `/export/quote-pdf` | Generate quotation PDF              |

### Swagger Documentation

When running locally:

```text
http://127.0.0.1:8000/docs
```

---

## 🛠️ Tech Stack

| Category            | Technology                         |
| ------------------- | ---------------------------------- |
| Backend             | Python, FastAPI                    |
| API                 | REST, JSON, SSE-style response     |
| LLM                 | OpenAI API                         |
| Embeddings          | OpenAI `text-embedding-3-large`    |
| RAG                 | FAISS, BM25                        |
| Reranking           | Sentence Transformers CrossEncoder |
| Document Processing | PyPDF2, python-docx, Pandas        |
| Excel               | Pandas, OpenPyXL                   |
| CAD                 | ezdxf, ODA File Converter          |
| Cost Engine         | Python                             |
| PDF Export          | FPDF                               |
| Frontend            | HTML, CSS, JavaScript              |
| Vector Storage      | FAISS, NumPy                       |
| Configuration       | python-dotenv                      |
| Server              | Uvicorn                            |

---

## 💾 Pricing Database

The quotation engine uses:

```text
data/material_prices.csv
```

The pricing file should contain at least:

```text
item,price
```

Example:

```csv
item,price
Steel Pipe,150
Copper Wire,80
PVC Pipe,45
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd RFQ-AI-System-main
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate Environment

#### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

#### Windows CMD

```cmd
.venv\Scripts\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key

OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072

CHUNK_SIZE=1000
CHUNK_OVERLAP=200

TOP_K=8
MAX_CONTEXT_CHARS=12000
```

The application currently requires `OPENAI_API_KEY` during configuration loading.

---

## ▶️ Run the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Application:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 📖 Usage

### Step 1 — Upload Documents

Upload RFQ documents through the web interface.

Supported engineering document types include:

```text
Excel
PDF
CSV
DOCX
TXT
DWG
DXF
```

### Step 2 — Document Analysis

Use the conversational interface to ask questions about the uploaded documents.

Example:

```text
List all items from the BOQ with their quantities.
```

### Step 3 — Engineering Analysis

Ask questions involving multiple document sources.

Example:

```text
Are there any conflicts between the CAD drawings and the BOQ?
```

### Step 4 — Cost Estimation

Switch to the **Cost Estimation** workflow to generate a quotation from the extracted BOQ information.

### Step 5 — Export

Generate and export the quotation as a PDF.

---

## 🧮 Quotation Calculation

The current quotation workflow follows:

```text
Material Cost
     +
Labor Cost
     ↓
Subtotal
     +
Profit
     ↓
Final Quote Total
```

Current defaults:

```text
Labor = 15%
Profit = 10%
```

The UI also displays a **5% tax estimate**, but the current implementation does not add this tax to the final quotation total.

---

## ⚠️ Current Limitations

The current implementation has the following limitations:

* Scanned PDFs are not processed with OCR.
* DOCX extraction currently processes paragraphs, not tables.
* DWG processing requires the ODA File Converter.
* ODA path is currently hardcoded.
* FAISS vector dimension is fixed to `3072` in the vector service.
* CrossEncoder may download its model during first use.
* `/query/stream` simulates streaming by splitting the completed response.
* BOQ session state is stored globally in memory.
* No authentication or authorization is implemented.
* No persistent database is implemented.
* Upload validation is inconsistent across processing paths.
* Quotation generation can use fallback sample BOQ data when no BOQ is available.
* Tax is displayed as an estimate but is not included in the final quote total.
* The main bundle workflow primarily processes `xlsx/xls`, `pdf`, `dwg`, and `dxf`.
* `/documents/stats` currently does not return the expected debug statistics.
* Frontend deletion references a `/delete/{filename}` route that is not present in the provided router code.

---

## 🎯 Project Focus

The RFQ AI System brings together several engineering automation workflows in one application:

```text
Engineering Documents
        ↓
Document Intelligence
        ↓
BOQ Extraction
        ↓
Hybrid RAG
        ↓
Engineering Conflict Detection
        ↓
Cost Estimation
        ↓
Quotation Generation
        ↓
PDF Export
```

It is designed to reduce manual effort involved in analyzing RFQ documentation, extracting BOQ information, identifying inconsistencies, estimating costs, and preparing quotations.
