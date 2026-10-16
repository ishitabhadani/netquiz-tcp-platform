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

---

## 2. Directory Structure

```
mini project/
├── backend/
│   ├── api/             # FastAPI REST endpoints (/api/health)
│   ├── models/          # Schemas and data models
│   ├── networking/      # Real Python TCP socket layer
│   │   ├── protocol.py       # Message framing (newline-delimited JSON buffer)
│   │   ├── client_handler.py # Multithreaded client handler thread
│   │   ├── tcp_server.py     # AF_INET SOCK_STREAM socket server on port 5000
│   │   ├── test_client.py    # Standalone test client for student simulation
│   │   └── test_stage2.py    # Automated 8-test verification suite
│   ├── quiz/            # Question bank and quiz state engine (Stage 3)
│   ├── config.py        # Host & Port definitions (FastAPI: 8000, TCP: 5000)
│   └── main.py          # FastAPI application entry point
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

## 3. Stage 2: Genuine TCP Socket Networking Layer

Stage 2 implements the real Computer Networks core of NetQuiz using Python's standard `socket` and `threading` libraries.

### 3.1 Networking Architecture & Concurrency

```
                    ┌─────────────────────────┐
                    │    Main Server Thread   │
                    │   socket.bind(5000)     │
                    │   socket.listen(10)     │
                    └───────────┬─────────────┘
                                │  socket.accept()
                  ┌─────────────┴─────────────┐
                  │                           │
                  ▼                           ▼
        ┌──────────────────┐        ┌──────────────────┐
        │  Client Thread 1 │        │  Client Thread 2 │
        │  Student: Ishita │        │  Student: Aarav  │
        │  Addr: :61570    │        │  Addr: :61571    │
        │  Independent Recv│        │  Independent Recv│
        └──────────────────┘        └──────────────────┘
```

- **Socket Creation:** `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`
  - `AF_INET`: Specifies IPv4 addressing family.
  - `SOCK_STREAM`: Specifies reliable, connection-oriented, sequenced byte stream transport (TCP).
- **Socket Options:** `SO_REUSEADDR` is set so the server can rebind to port `5000` immediately upon restart without waiting through the `TIME_WAIT` socket state.
- **Port Binding:** `bind(('127.0.0.1', 5000))` reserves port 5000 for quiz traffic.
- **Listening & Accepting:** `listen(10)` puts the socket in passive state; `accept()` completes the TCP 3-way handshake (`SYN` $\rightarrow$ `SYN-ACK` $\rightarrow$ `ACK`).
- **Concurrency (Multithreading):** Each accepted client connection runs on a dedicated `ClientHandler(threading.Thread)` instance. An active student answering or waiting on I/O will never block other students, and state is isolated.

### 3.2 TCP Stream Framing: Why Newline-Delimited JSON?

Unlike UDP (which preserves packet boundaries), **TCP is an unstructured byte stream**. This means:
1. One `send()` might be split across multiple TCP segments.
2. Multiple `send()` calls can be coalesced into one segment by Nagle's algorithm.
3. A single `recv()` call does **not** guarantee returning exactly one JSON message.

To solve this without complex binary length-headers, NetQuiz uses **Newline-Delimited JSON (JSON Lines)**:
```json
{"type": "join", "student_name": "Ishita"}\n
```
The `MessageFramingBuffer` accumulates incoming bytes, slices strings when encountering `\n`, decodes JSON objects, and handles malformed payloads without crashing the server.

---

## 4. How to Run and Test the TCP Layer

### Run the Stage 2 Automated Test Suite
A comprehensive 8-step test suite tests all edge cases (concurrency, ping/pong, disconnects, malformed JSON, and server rebound):

```bash
source venv/bin/activate
python -m backend.networking.test_stage2
```
Expected output:
```
============================================================
  ALL 8/8 TESTS COMPLETED SUCCESSFULLY!
============================================================
```

---

### Run the Standalone TCP Server & Clients Manually

#### Step 1: Start the TCP Server
Open **Terminal 1**:
```bash
source venv/bin/activate
python -m backend.networking.tcp_server
```

#### Step 2: Connect Multiple Concurrent Clients
Open **Terminal 2 (Student 1)**:
```bash
source venv/bin/activate
python -m backend.networking.test_client Ishita --ping --stay 15
```

Open **Terminal 3 (Student 2)**:
```bash
source venv/bin/activate
python -m backend.networking.test_client Aarav --ping --stay 15
```

Open **Terminal 4 (Student 3)**:
```bash
source venv/bin/activate
python -m backend.networking.test_client Riya --ping --stay 15
```

The TCP Server terminal will log 3 concurrent connections:
```text
[CONNECTION] New client connection from 127.0.0.1:62155
[CLIENT] Student joined: 'Ishita' (ID: 857735c8)
[SERVER] Active Clients: 3 | Total Connections: 3
```

---

## 5. Web Platform Run Instructions (From Stage 1)

### Start FastAPI Application Bridge
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Start React Frontend
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Visit: `http://localhost:5173`
