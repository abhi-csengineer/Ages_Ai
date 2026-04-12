# Aegis-AI // Tactical LLM Governance & Observability

**Aegis-AI** is a high-performance, deep-tech observability "sidecar" designed to protect and monitor Large Language Models (LLMs) in production. It moves beyond standard logging by performing **Real-Time Vector Mathematics** to detect semantic drift and estimate model accuracy without human labeling.

---

## 🏗 System Architecture

Aegis-AI is engineered as a heavy-duty infrastructure layer that sits between the user and the LLM (e.g., Google Gemini 1.5).

### **The "Heavy" Backend Stack**
* **Stream Processing:** Built with **Bytewax (Rust-core)** for sub-100ms parallel processing of vector streams.
* **Analytical Engine:** Powered by **DuckDB** for high-speed, in-memory statistical calculations (MMD Drift, K-S Tests).
* **Dimensionality Reduction:** Utilizes **UMAP** to squash 1536-dimensional embeddings into a visual 2D coordinate system.
* **Storage:** A hybrid approach using a **Vector Database** for spatial indexing and a relational store for telemetry metadata.

---

## 🔥 Key Technical Features

### 🧠 1. Label-less Accuracy (Hui-Walter Paradigm)
Estimating accuracy in production usually requires expensive human labeling. Aegis-AI implements the **Hui-Walter Paradigm**, a latent class analysis method that estimates the health of the production model by comparing it against a **Fresh Baseline** (Shadow Model) and a **Challenger** (Gemini Pro).

### 📍 2. Spatial Drift Detection
We visualize the AI's internal state by mapping live vectors against a "Golden" reference set.
* **Reference Set:** The safe distribution the model was trained on.
* **Live Set:** Real-time production prompts.
The backend calculates **Maximum Mean Discrepancy (MMD)** between these sets to flag "Silent Model Decay."

### 🛡 3. The Inference Sidecar (Active Firewall)
The FastAPI-based sidecar intercepts requests to perform:
* **PII Redaction:** Automated masking of sensitive data (Emails, Phone Numbers, Aadhar).
* **Adversarial Defense:** Semantic analysis to block "Jailbreak" attempts in real-time.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React, Chakra UI, Framer Motion, WebSockets |
| **API / Sidecar** | FastAPI (Asynchronous Python) |
| **Compute** | NumPy, SciPy, Scikit-learn, Sentence-Transformers |
| **Databases** | DuckDB (Analytics), ChromaDB (Vector) |
| **Model** | Google Gemini 1.5 Flash |

---

## 🚀 Getting Started

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000

### Frontened Setup
cd frontend
npm install
npm start
