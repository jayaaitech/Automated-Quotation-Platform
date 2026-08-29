/**
 * RFQ AI System - Frontend Logic
 * Handles file uploads, chat interactions, document management, and PDF generation.
 */

// =========================================
// 1. DOM ELEMENTS & STATE
// =========================================
const chat = document.getElementById("chat");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileName");
const progressBar = document.getElementById("progress");
const documentsContainer = document.getElementById("documents");
const modeToggle = document.getElementById("modeToggle");

let lastCalculatedQuote = null; // Stores raw JSON data for the PDF generator
let isLoading = false; // Prevents spam-clicking the send button

// =========================================
// 2. FILE UPLOAD LOGIC (Drag & Drop)
// =========================================
if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());
    fileInput.style.display = "none";

    fileInput.addEventListener("change", async () => {
        if (fileInput.files.length > 0) {
            await handleFiles(fileInput.files);
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", async (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            await handleFiles(e.dataTransfer.files);
        }
    });
}

async function handleFiles(files) {
    fileNameDisplay.textContent = `Uploading ${files.length} file(s)...`;
    progressBar.style.width = "0%";

    try {
        const responseData = await uploadBundle(files);
        fileNameDisplay.textContent = "✅ Upload complete";
        progressBar.style.width = "100%";

        const aiDiv = createMessageElement("ai");
        const summary = responseData.summary || {};
        const conflicts = responseData.conflicts || {};

        aiDiv.innerHTML = `
            <b>📂 RFQ Bundle Processed</b><br>
            Files: ${responseData.files_processed}<br>
            Entities: ${summary.entities || 0}<br><br>
            ${[...files].map(f => "• " + f.name).join("<br>")}
        `;

        // If you have a conflict reporting function, trigger it here
        if (conflicts && Object.keys(conflicts).length > 0 && typeof displayConflictReport === 'function') {
            displayConflictReport(conflicts); 
        }

    } catch (error) {
        console.error(error);
        alert("❌ Upload failed");
        progressBar.style.width = "0%";
    }

    // Reset UI after 3 seconds
    setTimeout(() => {
        fileNameDisplay.textContent = "";
        progressBar.style.width = "0%";
    }, 3000);

    loadDocuments();
}

function uploadBundle(files) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append("project_name", "RFQ " + new Date().toLocaleTimeString());

        [...files].forEach(file => formData.append("files", file));

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload/bundle");

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                progressBar.style.width = (e.loaded / e.total) * 100 + "%";
            }
        };

        xhr.onload = () => {
            try {
                const data = JSON.parse(xhr.responseText);
                if (xhr.status >= 200 && xhr.status < 300) resolve(data);
                else reject(data.detail || "Upload failed");
            } catch {
                reject("Invalid response");
            }
        };

        xhr.onerror = () => reject("Network error");
        xhr.send(formData);
    });
}

// =========================================
// 3. UI HELPERS & TOGGLE
// =========================================
function createMessageElement(type) {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight; // Auto-scroll to bottom
    return div;
}

// Switch between Q&A Mode and Quote Generation Mode
modeToggle.addEventListener("change", () => {
    if (modeToggle.checked) {
        questionInput.placeholder = "Generate quotation or cost estimation...";
        questionInput.value = "Generate a complete quotation";
        askAI(); // Auto trigger when switched to quote mode
    } else {
        questionInput.placeholder = "Ask a question about your RFQ...";
        questionInput.value = "";
    }
});

// =========================================
// 4. CHAT INTERACTION LOGIC
// =========================================
async function askAI() {
    if (isLoading) return;

    const question = questionInput.value.trim();
    if (!question) return;

    isLoading = true;
    sendBtn.disabled = true;

    // Display user message
    createMessageElement("user").innerText = question;
    questionInput.value = "";

    // Show loading state
    const aiDiv = createMessageElement("ai");
    aiDiv.innerHTML = "⏳ Generating...";
    aiDiv.classList.add("loading"); // Add loading class for CSS animation

    try {
        const response = await fetch("/query/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question })
        });

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error("Invalid response format");
        }

        if (!response.ok) {
            throw new Error(data.detail?.[0]?.msg || "Request failed");
        }

        // ✅ Save the raw quote data so the PDF generator can use it later!
        if (data.result) {
            lastCalculatedQuote = data.result; 
        }

        aiDiv.classList.remove("loading");
        aiDiv.innerHTML = `<div class="ai-content">${data.answer || "No response"}</div>`;

    } catch (err) {
        console.error(err);
        aiDiv.classList.remove("loading");
        aiDiv.innerHTML = `❌ Error: ${err.message || "Failed to get response"}`;
    }

    isLoading = false;
    sendBtn.disabled = false;
}

// =========================================
// 5. PDF DOWNLOAD (EVENT DELEGATION)
// =========================================
// ✅ Because the download button is generated by the AI, we must listen 
// for clicks on the parent `chat` container and check what was clicked.
chat.addEventListener("click", async (e) => {
    if (e.target && e.target.id === "downloadPdfBtn") {
        
        if (!lastCalculatedQuote) {
            alert("No quote data available to download.");
            return;
        }

        const btn = e.target;
        const originalText = btn.innerText;
        btn.innerText = "⏳ Generating PDF...";
        btn.disabled = true;

        try {
            const res = await fetch("/export/quote-pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(lastCalculatedQuote)
            });

            if (!res.ok) throw new Error("Failed to generate PDF");

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);

            const a = document.createElement("a");
            a.href = url;
            // Name the file dynamically based on the Quote ID
            const quoteId = lastCalculatedQuote.metadata?.quote_id || "Draft";
            a.download = `Quotation_${quoteId}.pdf`;
            a.click();

            URL.revokeObjectURL(url);
        } catch (error) {
            console.error(error);
            alert("❌ Failed to download PDF.");
        } finally {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    }
});

// =========================================
// 6. DOCUMENT MANAGEMENT
// =========================================
async function loadDocuments() {
    try {
        const res = await fetch("/documents");
        
        // Failsafe if the document endpoint isn't built yet
        if (res.status === 404) {
             documentsContainer.innerHTML = "<p>No documents uploaded.</p>";
             return;
        }

        const data = await res.json();
        documentsContainer.innerHTML = "";

        if (!data.documents?.length) {
            documentsContainer.innerHTML = "<p>No documents uploaded.</p>";
            return;
        }

        data.documents.forEach(doc => {
            const div = document.createElement("div");
            div.className = "document-item";
            div.innerHTML = `<span>${doc}</span>`;

            const btn = document.createElement("button");
            btn.className = "delete-btn";
            btn.innerText = "🗑️";
            btn.title = "Delete document";
            btn.onclick = () => deleteDocument(doc);

            div.appendChild(btn);
            documentsContainer.appendChild(div);
        });

    } catch (err) {
        console.error("Doc load error:", err);
        documentsContainer.innerHTML = "<p>Ready for uploads.</p>";
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
        await fetch(`/delete/${filename}`, { method: "DELETE" });
        loadDocuments();
    } catch (err) {
        console.error("Failed to delete", err);
    }
}

// =========================================
// 7. INITIALIZATION & LISTENERS
// =========================================
sendBtn.onclick = askAI;

questionInput.onkeydown = (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        askAI();
    }
};

// Load initial document list on page load
loadDocuments();