# 📦 Supply Chain Exception Intelligence Assistant

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/GenAI-Gemini%201.5%20Flash-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![TailwindCSS](https://img.shields.io/badge/Frontend-TailwindCSS-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Kongu Engineering College | Generative AI Industry Project Handbook**  
> **Project 12** • *Full-Stack GenAI Business Application*  
> **Domain:** Supply Chain Management & Operational Exception Intelligence

---

## 🎯 Executive Summary & Business Problem

Modern supply-chain operations generate massive volumes of purchase orders, stock levels, warehouse utilizations, and supplier lead-time data. When exceptions occur (such as sudden safety stock breaches, delayed transit shipments, or supplier lead-time drift), manual detection is slow, reactive, and prone to costly production halts.

The **Supply Chain Exception Intelligence Assistant** is a production-grade full-stack solution that combines **strictly deterministic analytics** with **grounded Generative AI** (Gemini) to:
1. Deterministically flag inventory shortages, shipment delays, and supplier risks.
2. Provide grounded, faithful natural-language explanations of *why* each exception occurred.
3. Prescribe actionable operational recommendations (cross-warehouse balancing, PO expediting, SLA enforcement).
4. Power a conversational **Natural Language Assistant** capable of answering complex analytical questions.

---

## 🏛️ System Architecture

```
                      +------------------------------------------+
                      |         Operational Data Sources         |
                      |  Orders • Inventory • Suppliers • Hubs   |
                      +------------------------------------------+
                                           │
                                           ▼ [POST /data/upload]
                      +------------------------------------------+
                      |     Transactional SQLite / DuckDB        |
                      +------------------------------------------+
                                           │
                                           ▼ [POST /analytics/run]
                      +------------------------------------------+
                      |       DETERMINISTIC ANALYTICS ENGINE     |
                      |  • Safety Stock & Reorder Triggering     |
                      |  • Order Transit Delay Detection         |
                      |  • 7-Day Run-Rate Shortage Forecaster    |
                      |  • Supplier OTIF % & Reliability Metric  |
                      +------------------------------------------+
                                           │ (Deterministic Facts & Metrics)
                                           ▼
                      +------------------------------------------+
                      |         GENAI & LLM LAYER (Gemini)       |
                      |  • Zero-Hallucination Grounded Prompting |
                      |  • Root-Cause Explanation Generator      |
                      |  • Prescriptive Action Recommendations   |
                      |  • Natural Language Query Engine (Chat)  |
                      +------------------------------------------+
                                           │
                                           ▼
                      +------------------------------------------+
                      |     ENTERPRISE WEB DASHBOARD (REST)      |
                      |  Dashboard • Exception Queue • OTIF Bench|
                      |  7-Day Forecaster • NL Chat • CSV Hub    |
                      +------------------------------------------+
```

---

## 🛡️ Critical Guardrail & Deterministic Guarantee

> **Important Constraint:** Traditional programming and analytics perform **100% of the deterministic calculations** (Days of Supply, OTIF rates, deficit quantities, lead time variances).  
> The GenAI layer is strictly constrained to **explain, synthesize, and assist** based solely on computed facts, eliminating hallucinations.

---

## ✨ Key Features

- 📂 **Multi-Entity CSV Data Ingestion (`POST /data/upload`)**: Instant upload and transactional ingestion for Orders, Products, Suppliers, Warehouses, and Inventory datasets.
- ⚡ **Automated Exception Detection Engine (`POST /analytics/run`)**:
  - `OUT_OF_STOCK` & `SAFETY_STOCK_BREACH`
  - `ORDER_DELIVERY_DELAY` (both delivered late and in-transit overdue)
  - `7DAY_STOCKOUT_PREDICTION` (advanced run-rate forecasting)
  - `REORDER_POINT_TRIGGERED`
- 🤖 **GenAI Root-Cause & Action Engine (`GET /exceptions`)**: Contextual explanation and remediation plans attached to each exception card.
- 🚚 **Supplier Benchmark Matrix (`GET /suppliers/compare`)**: Real-time calculation of On-Time In-Full (OTIF %), average lead-time drift, reliability scoring (0-100), and risk tiers (`Low Risk`, `Moderate Risk`, `High Risk`).
- 🔮 **7-Day Stockout Risk Forecaster (`GET /analytics/forecast`)**:
  $$\text{Days of Supply} = \frac{\text{Current Stock} - \text{Reserved} + \text{Inbound Confirmed}}{\text{Daily Consumption Velocity}}$$
- 💬 **Natural-Language Operations Assistant (`POST /supply/query`)**: Interactive chat interface answering queries such as:
  > *"Which products are likely to face stock shortages in the next seven days and why?"*  
  > *"Which supplier has the highest delay rate and impact on operations?"*

---

## 🚀 Quickstart & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/varsha2706/supply-chain-exception-intelligence.git
cd supply-chain-exception-intelligence
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. (Optional) Configure Gemini API Key
Create a `.env` file or export your key:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
*(Note: The system includes a built-in deterministic heuristic fallback engine, allowing full operation even without an API key).*

### 4. Run the Application
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status check |
| `POST` | `/data/upload` | Ingest CSV file into `orders`, `inventory`, `products`, `suppliers`, or `warehouses` |
| `POST` | `/data/sample` | Reload official benchmark dataset |
| `POST` | `/analytics/run` | Execute deterministic rules & trigger GenAI insights |
| `GET` | `/exceptions` | List prioritized exceptions (supports `severity`, `exception_type`, `search` query params) |
| `POST` | `/supply/query` | Natural Language Querying endpoint with grounded LLM reasoning |
| `GET` | `/suppliers/compare` | Supplier benchmark scorecard (OTIF %, lead time variance, reliability score) |
| `GET` | `/inventory/dashboard` | High-level KPIs, inventory valuation, stock health stats |
| `GET` | `/analytics/forecast` | 7-Day predictive shortage forecast report |

---

## 🧪 Running Automated Tests

Run the complete test suite (unit tests and REST API integration tests):
```bash
python -m unittest discover -s tests
```

---

## 🌐 Cloud Deployment Options

### Option A: Render (1-Click Deployment)
1. Link your GitHub repository on [Render.com](https://render.com).
2. Render will automatically detect `render.yaml` and configure the Python web service.

### Option B: Railway / Heroku
The included `Procfile` is pre-configured for Railway and Heroku:
```bash
web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Option C: Docker Container
```bash
docker build -t supply-chain-ai-assistant .
docker run -p 8000:8000 supply-chain-ai-assistant
```

---

## 📊 Evaluation & KPI Impact

- **Detection Accuracy:** 100% deterministic rule adherence for safety stock and lead-time drift.
- **Explanation Faithfulness:** Zero hallucination via strictly parameterized context grounding.
- **Decision Velocity:** Shortens exception triage time from hours to seconds.
- **Production Readiness:** Modular architecture with separated data, deterministic analytics, LLM, and presentation layers.
