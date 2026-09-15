# 💰 Cost-Aware Multi-Model Router Workspace

> **Production Monorepo for the Cost-Aware Multi-Model Router platform.**

---

## 📸 Workspace Structure

```
multi_model/
│
├── backend/
│   └── cost-aware-router/       # FastAPI Backend Server & LangGraph Router
│       ├── app/                 # Backend source code (auth, db, router, mcp, models)
│       ├── docs/                # Architecture (ARCHITECTURE.md) & Workflows (WORKFLOW.md)
│       ├── tests/               # Automated test suite
│       ├── evaluation/          # Evaluation benchmarks & held-out dataset
│       ├── logs/                # Event logs
│       ├── api_server.py        # FastAPI API Gateway Entry Point
│       ├── .env                 # Environment configuration
│       ├── .env.example         # Environment template
│       └── requirements.txt     # Python dependencies
│
├── frontend/
│   └── cost-aware-router/       # Next.js 16 Production Web Application
│       ├── src/                 # React UI components & app router pages
│       ├── lib/                 # API client utilities
│       ├── public/              # Static assets
│       ├── package.json         # Node dependencies
│       └── next.config.ts       # Next.js configuration
│
├── analysis/                    # Analysis scripts, debugging tools & legacy components
├── infrastructure/              # Infrastructure configs (MongoDB docker-compose)
│
├── README.md                    # Monorepo Workspace Guide
├── .gitignore                   # Workspace Git ignore rules
└── .venv/                       # Shared Python virtual environment
```

---

## 🚀 Quick Start Guide

### 1. Backend Server Setup

```bash
cd backend/cost-aware-router

# Activate python environment & install dependencies
pip install -r requirements.txt

# Run FastAPI backend server
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

Backend server runs at `http://localhost:8000`. Health check: `http://localhost:8000/health`.

### 2. Frontend Web Application Setup

```bash
cd frontend/cost-aware-router

# Install dependencies & run development server
npm install
npm run dev
```

Frontend application runs at `http://localhost:3000`.

---

## 🧪 Running Tests & Build Verification

### Backend Tests

```bash
cd backend/cost-aware-router
python -m pytest -q
```

### Frontend Build

```bash
cd frontend/cost-aware-router
npm run build
```

---

## 📚 Technical Documentation

- **[System Architecture](file:///k:/multi_model/backend/cost-aware-router/docs/ARCHITECTURE.md)**: System topology, component responsibilities, MongoDB persistence schema, security boundaries.
- **[Operational Workflows](file:///k:/multi_model/backend/cost-aware-router/docs/WORKFLOW.md)**: Step-by-step user authentication, routing execution, MCP tool invocation, and dashboard aggregation workflows.
