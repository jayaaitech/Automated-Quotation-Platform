# 🤖 RFQ AI System

An intelligent, full-stack Request for Quotation (RFQ) processing system built with FastAPI. This application automates the tedious process of reading engineering documents, extracting Bill of Quantities (BOQ) data, and generating professional cost estimations.

## ✨ Key Features

* **Multi-Format Document Parsing:** Drag-and-drop support for Excel (`.xlsx`, `.xls`), PDFs, and CAD drawings (`.dwg`, `.dxf`).
* **Intelligent BOQ Extraction:** Automatically finds and extracts item descriptions and quantities from messy, unstructured Excel sheets.
* **Conversational AI Interface:** Chat directly with your uploaded documents to ask questions about specifications or safety standards.
* **Automated Cost Estimation:** Instantly calculates material, labor, and profit margins based on a customizable pricing database.
* **One-Click PDF Export:** Generates professional, branded quotation PDFs (e.g., for projects like the Radha Krishna Resort) directly from the chat UI.

## 🛠️ Tech Stack

* **Backend:** Python 3.10+, FastAPI, Pandas (data extraction), FPDF2 (PDF generation).
* **Frontend:** HTML5, CSS3 (Custom UI/UX), Vanilla JavaScript (Event Delegation, Fetch API).
* **Architecture:** Retrieval-Augmented Generation (RAG) pipeline for document analysis and a rule-based Cost Engine.

## 📂 Project Structure

```text
RFQ_AI_SYSTEM/
│
├── app/
│   ├── brain/                 # AI, Vector DB, and LLM Logic
│   ├── models/                # Pydantic schemas (RFQRequest, QueryResponse)
│   ├── pipeline/              # Orchestration (RFQ & Quotation pipelines)
│   ├── qoute_service/         # Pricing math and quotation business logic
│   ├── routers/               # FastAPI endpoints
│   │   ├── document_router.py
│   │   ├── export_router.py   # PDF Generation
│   │   ├── query_router.py    # Chat & Quote Generation
│   │   └── upload_router.py   # File handling
│   ├── services/              # File parsers (Excel, CAD, PDF)
│   ├── web/                   # Frontend Assets
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── config.py              # Environment variables and settings
│   └── main.py                # FastAPI application entry point
│
├── data/
│   └── material_prices.csv    # Your base pricing database
│
├── uploads/                   # Temporary storage for uploaded RFQs
└── requirements.txt


python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

Set up your pricing database
Ensure you have a material_prices.csv file located at data/material_prices.csv with at least two columns: item and price.

Start the server

Bash
uvicorn app.main:app --reload --port 8004
💻 Usage
Open your browser and navigate to http://127.0.0.1:8004.

## 🤖 Example Queries
- "List all items from the BOQ with their quantities."
- "Are there any conflicts between the CAD drawings and the BOQ?"
- "What are the fire safety standards required by the specifications?"

Upload: Drag and drop an Excel BOQ file into the sidebar. Wait for the success confirmation.

Chat: Ask standard questions about the document in the "Document Analysis" mode.

Quote: Flip the top toggle to "Cost Estimation". The system will automatically generate a formatted pricing table based on your uploaded files.

Export: Click "💾 Download PDF" at the bottom of the quote to save the official document."# RFQ-AI-System" 
