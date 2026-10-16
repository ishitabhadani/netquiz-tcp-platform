# NETQUIZ — Multi-User TCP Quiz Platform

**Academic Context:** B.Tech Computer Networks Mini-Project  
**Formal Title:** *Design and Implementation of a Multi-User Quiz Platform Using TCP Client-Server Architecture*

---

## 1. Project Overview

NetQuiz is an academic Computer Networks project demonstrating genuine TCP socket programming (`socket.AF_INET`, `socket.SOCK_STREAM`), multithreaded concurrent client handling, IPv4 addressing, port binding, and reliable transport layer communication.

To provide both a rich visual demonstration for academic evaluation and strict networking fidelity, the platform adopts a layered design:

```
React Frontend (Vite) [Port 5173]
       │  (HTTP / Fetch)
       ▼
FastAPI Application Bridge [Port 8000]
       │
       ▼
Quiz Manager & State Engine (Stage 3)
       │
       ▼
Python TCP Socket Server [Port 5000] (Stage 2)
       │
       ├──── TCP Client 1 (Student A Thread)
       ├──── TCP Client 2 (Student B Thread)
       └──── TCP Client 3 (Student C Thread)
```

> **Note on Stage 1:**  
> Stage 1 establishes the clean project architecture, Python backend environment, FastAPI application bridge, and React frontend foundation.  
> The genuine Python TCP socket layer will be implemented in **Stage 2**.

---

## 2. Directory Structure

```
mini project/
├── backend/
│   ├── api/             # FastAPI REST endpoints (e.g. /api/health)
│   ├── models/          # Schemas and data models
│   ├── networking/      # Real Python TCP socket server (Stage 2)
│   ├── quiz/            # Question bank and quiz state engine (Stage 3)
│   ├── config.py        # Host & Port definitions (FastAPI & TCP)
│   └── main.py          # Backend entry point
├── frontend/
│   ├── src/
│   │   ├── services/    # api.js for calling backend endpoints
│   │   ├── App.jsx      # Main view and health status card
│   │   ├── App.css
│   │   └── index.css    # Clean academic styling system
│   ├── package.json
│   └── vite.config.js
├── requirements.txt     # Python dependencies (fastapi, uvicorn)
├── .gitignore
└── README.md
```

---

## 3. How to Run the Project

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

---

### Step 1: Start the Backend (FastAPI Application Layer)

Open a terminal in the project root:

```bash
# 1. Create and activate a Python virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the FastAPI server
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Verify backend health in your browser or terminal:
```bash
curl http://127.0.0.1:8000/api/health
# Output: {"status":"ok","service":"NetQuiz Backend"}
```

---

### Step 2: Start the Frontend (React + Vite)

Open a second terminal in the project root:

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies (if not already done)
npm install

# 3. Start the Vite development server
npm run dev
```

Open your browser at:
`http://localhost:5173`

The frontend will load the NetQuiz landing card and display:
`FastAPI Application Layer: ● ONLINE`
