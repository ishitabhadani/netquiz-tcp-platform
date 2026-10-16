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
│   ├── quiz/            # Question bank and quiz state engine
│   │   ├── questions.json           # 15 Computer Networks questions
│   │   ├── quiz_manager.py          # Server-side QuizManager & PlayerQuizState
│   │   ├── test_quiz_engine.py      # Unit test suite for quiz logic
│   │   └── test_stage3_tcp_quiz.py  # Multi-user concurrent TCP quiz integration test
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
The `MessageFramingBuffer` accumulates incoming bytes, queues parsed messages, splits on `\n`, decodes JSON objects, and handles malformed payloads without crashing the server.

---

## 4. Stage 3: Server-Side Quiz Engine & Player State

Stage 3 adds application-layer quiz logic on top of the TCP socket layer while preserving strict network boundaries.

### 4.1 System Interaction Flow

```
Client (Student)
       │
       │  1. TCP JSON Line {"type": "answer", "question_id": 1, "answer": "B"}\n
       ▼
ClientHandler Thread
       │
       │  2. submit_answer(connection_id, question_id, answer)
       ▼
QuizManager (Server Core)
       │
       │  3. Validates order, duplicate checks & evaluates correctness server-side
       ▼
ClientHandler Thread
       │
       │  4. Sends {"type": "answer_result", "correct": true, "current_score": 1}\n
       │  5. Sends {"type": "question", "question_number": 2, ...}\n
       ▼
Client (Student)
```

### 4.2 Security & Server-Side Source-of-Truth
- **Zero Client Trust:** The client never submits scores. The server evaluates candidate answers against `questions.json` and increments scores strictly within `PlayerQuizState`.
- **Cheat Prevention:** Correct answers and explanations are stripped from question payloads before delivery over TCP.
- **Strict Validation:** Duplicate submissions, out-of-order questions, invalid options (e.g. `Z`), and post-completion submissions are rejected with error messages without server disruption.

---

## 5. How to Run and Test

### 1. Run All Automated Test Suites

```bash
source venv/bin/activate

# 1. Verify Stage 2 TCP Socket Networking (8 tests)
python -m backend.networking.test_stage2

# 2. Verify Stage 3 QuizManager Logic & Validations (12 tests)
python -m backend.quiz.test_quiz_engine

# 3. Verify Stage 3 Multi-User Concurrent TCP Quiz (3 concurrent students)
python -m backend.quiz.test_stage3_tcp_quiz
```

---

### 2. Run Interactive CLI Quiz Client

#### Step 1: Start TCP Server
In **Terminal 1**:
```bash
source venv/bin/activate
python -m backend.networking.tcp_server
```

#### Step 2: Play the Quiz Interactively in Terminal
In **Terminal 2**:
```bash
source venv/bin/activate
python -m backend.networking.test_client Ishita --interactive
```
The terminal client will connect via TCP port 5000, display each Computer Networks question, prompt you for `A/B/C/D`, display live server evaluations with explanations, and finish with a formatted results card!

---

### 3. Run Simultaneous Multi-Client Simulation

In **Terminal 2 (Student A)**:
```bash
python -m backend.networking.test_client Ishita --quiz --answers A A C B C B C B B C
```

In **Terminal 3 (Student B)**:
```bash
python -m backend.networking.test_client Aarav --quiz --answers A A A A A B C B B C
```

In **Terminal 4 (Student C)**:
```bash
python -m backend.networking.test_client Riya --quiz --answers B C C B C B C B B C
```

Each client executes concurrently over TCP, receiving independent scores (Ishita: 8/10, Aarav: 5/10, Riya: 10/10) with verified state isolation.

---

## 6. Web Platform Run Instructions

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
