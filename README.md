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
│   ├── api/             # FastAPI REST endpoints
│   │   ├── routes.py         # /api/health, /api/server/status, /api/server/clients, /api/quiz/*
│   │   └── test_api.py       # Automated API test suite
│   ├── models/          # Typed Pydantic schemas
│   │   └── schemas.py        # Request/response validation schemas
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
│   └── main.py          # FastAPI application entry point with Lifespan & CORS
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   │   ├── Navbar.jsx               # Brand header, IP:Port pill, and status badge
│   │   │   ├── StatusBadge.jsx          # Live TCP ONLINE / OFFLINE indicator
│   │   │   ├── NetworkStatCards.jsx     # Parameter cards (Transport, IPv4, Sockets)
│   │   │   ├── NetworkArchitecture.jsx  # CSS client-server topology diagram
│   │   │   └── Footer.jsx               # Technical footer with port mappings
│   │   ├── pages/       # Application views
│   │   │   └── Home.jsx                 # Landing page & student join card
│   │   ├── services/    # Centralized API service layer
│   │   │   └── api.js                   # getHealth, getServerStatus, getQuizInfo, etc.
│   │   ├── App.jsx      # Top-level state coordinator
│   │   ├── App.css      # Component and layout styling
│   │   └── index.css    # Design tokens and theme variables
│   ├── package.json
│   └── vite.config.js
├── requirements.txt     # Python dependencies (fastapi, uvicorn, httpx)
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

## 5. Stage 4: FastAPI Application / Bridge Layer

FastAPI acts as an **application bridge** between the web browser and the underlying Python TCP socket server.

### 5.1 Layer Separation & Port Allocation

```
React Browser [Port 5173]
       │
       │ HTTP REST (JSON)
       ▼
FastAPI Application Layer [Port 8000]
       │
       │ Shared In-Memory Metrics & State
       ▼
Python TCP Socket Server [Port 5000]
       │
       ├──── TCP Client 1 (Student A Thread)
       ├──── TCP Client 2 (Student B Thread)
       └──── TCP Client 3 (Student C Thread)
```

| Component | Port | Transport Protocol | Role |
|---|:---:|:---:|---|
| **React Frontend** | `5173` | HTTP / Browser | User interface running in the student's browser |
| **FastAPI Bridge** | `8000` | HTTP / REST | Exposes live TCP status, client registries, and leaderboard to web UI |
| **Python TCP Server** | `5000` | TCP (`SOCK_STREAM`) | Genuine Computer Networks transport layer for quiz message exchange |

### 5.2 Exposed API Endpoints

- `GET /api/health`: Health status of FastAPI bridge layer.
- `GET /api/server/status`: Live TCP metrics (active clients, total connections, packets sent/received, questions sent, answers received, completed quizzes).
- `GET /api/server/clients`: Currently connected TCP clients registry (connection ID, student name, IP, ephemeral port, live score).
- `GET /api/quiz/info`: Question bank configuration and topic metadata.
- `GET /api/quiz/leaderboard`: Server-evaluated student leaderboard ranked by score and percentage.
- `GET /docs`: Interactive Swagger / OpenAPI documentation.

---

## 6. Stage 5: Polished React Frontend Foundation

Stage 5 creates the academic, modern web interface that connects directly to the FastAPI application bridge.

### 6.1 Frontend Component Architecture

```
frontend/src/
├── components/
│   ├── Navbar.jsx               # Branded top nav with 127.0.0.1:5000 pill & TCP ● ONLINE status
│   ├── StatusBadge.jsx          # Reusable pulsing online/offline badge
│   ├── NetworkStatCards.jsx     # 6 parameter cards (TCP, IPv4, Sockets, Question Bank)
│   ├── NetworkArchitecture.jsx  # CSS client-server topology diagram
│   └── Footer.jsx               # Technical footer with port mappings
├── pages/
│   └── Home.jsx                 # Hero, student join form, parameter grid, and live terminal
├── services/
│   └── api.js                   # Centralized API service methods
├── App.jsx                      # Root state polling & offline banner
└── App.css                      # Design system styling & responsive layout
```

### 6.2 Key UI Features
- **Prominent Networking Identity:** Visibly highlights `TCP`, `IPv4`, `SOCK_STREAM`, and `Port 5000` so professors and examiners immediately see the networking focus.
- **Live Status Synchronization:** Queries `GET /api/server/status` to display real-time connection state (`TCP SERVER ONLINE` with a pulsing emerald dot).
- **CSS Client-Server Topology Diagram:** Visualizes the central server branching to concurrent client threads over reliable byte streams.
- **Live Server Terminal Card:** Displays low-level socket parameters, active socket counts, and questions delivered.

## 7. Stage 6 & 7: Frontend Integration, Multi-User Hardening & Demo Readiness

Stage 6 and Stage 7 connect the polished React frontend to the Quiz Engine via the FastAPI bridge and harden the multi-user architecture for classroom demonstration.

### Key Hardening Guarantees:
- **Server-Side Scoring:** Candidate answers are checked server-side; client score/percentage overrides are rejected.
- **Answer Secrecy:** `correct_answer` is strictly stripped before question delivery.
- **Session Isolation:** Thread-per-client and UUID-keyed `PlayerQuizState` ensure zero state leakage between students.
- **Duplicate & Out-of-Order Rejection:** Duplicate answers or out-of-order submissions are rejected with clean HTTP 400 responses.
- **Graceful Refresh Handling:** Browser refreshes are detected and cleanly redirected to Home with session-expired notices.

---

## 8. Demo Instructions

Follow these exact steps for a live project presentation or teacher demonstration:

### Terminal 1: Start FastAPI & Background TCP Server
```bash
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2: Start React Frontend (Vite)
```bash
cd frontend
npm run dev
```

Then open: `http://localhost:5173`

### Step-by-Step Demonstration Script:
1. **Open NetQuiz:** Navigate to `http://localhost:5173`.
2. **Show TCP Status:** Point out the `TCP SERVER ONLINE` pill, `127.0.0.1:5000` badge, and live parameter cards.
3. **Join as Ishita:** Enter `Ishita` in the Student Identifier field and click **Connect & Join Quiz**.
4. **Take Ishita's Quiz:** Answer several questions. Note the live progress bar, countdown timer, and server-side answer evaluation.
5. **Open Second Window:** Open another browser window or an Incognito window at `http://localhost:5173`.
6. **Join as Aarav:** Enter `Aarav` and join the quiz simultaneously.
7. **Simultaneous Play:** Answer questions in both windows. Note that scores, current question indices, and timers remain 100% independent.
8. **Complete Both Quizzes:** Finish both student sessions to see the circular score rings, grades (e.g. Distinction, First Class), and completion summaries.
9. **View Leaderboard:** Click **View Leaderboard** in both windows to show live descending score rankings (`Rank 1: Ishita`, `Rank 2: Aarav`) with gold/silver medals and current user highlight (`YOU` badge).
10. **Explain Architecture:** Scroll to the Network Architecture diagram and explain the dual-layer model (TCP :5000 vs FastAPI :8000).

---

## 9. Stage 7 Viva Verification

**Q: Why does the browser not connect directly to TCP port 5000?**  
**A:** Browsers do not provide arbitrary raw TCP socket access to JavaScript. Therefore React communicates with FastAPI over HTTP, while the actual networking implementation remains the Python TCP socket server.

**Q: Is FastAPI replacing TCP?**  
**A:** No. FastAPI is only the browser/application bridge. The actual quiz networking layer uses Python TCP sockets with `AF_INET` and `SOCK_STREAM`.

**Q: How are multiple students handled?**  
**A:** The TCP server creates a separate client handler thread for each connected client, while each player has independent server-side quiz state.

**Q: Where is the score calculated?**  
**A:** On the server inside `QuizManager`.

**Q: Can the client send its own score?**  
**A:** No. The client only sends the selected answer. The server checks the answer against the server-side question bank and calculates the score.

**Q: How does TCP know where one JSON message ends?**  
**A:** NetQuiz uses newline-delimited JSON framing. Each JSON message ends with a newline, and `MessageFramingBuffer` reconstructs complete messages from the TCP byte stream.

**Q: What happens if multiple TCP messages arrive in one recv()?**  
**A:** The framing buffer separates them into individual newline-delimited messages.

**Q: What does SOCK_STREAM mean?**  
**A:** It specifies a TCP stream socket providing reliable, ordered, connection-oriented byte-stream communication.

**Q: What does AF_INET mean?**  
**A:** It specifies the IPv4 address family.

**Q: How is concurrency achieved?**  
**A:** The server accepts connections and creates a separate thread for each client.

---

## 10. Automated Testing Command Reference

```bash
source venv/bin/activate

# 1. Stage 2: Genuine TCP Socket Networking Layer (8 tests)
python -m backend.networking.test_stage2

# 2. Stage 3: Server-Side QuizManager Logic & Validations (12 tests)
python -m backend.quiz.test_quiz_engine

# 3. Stage 3: Multi-User Concurrent TCP Quiz Integration (3 concurrent students)
python -m backend.quiz.test_stage3_tcp_quiz

# 4. Stage 4: FastAPI Endpoints, CORS & Lifespan (8 tests)
python -m backend.api.test_api

# 5. Stage 7: Multi-User Concurrency, Session Isolation & Hardening (10 tests)
python -m backend.api.test_stage7_multiuser

# 6. Frontend Production Bundle Check
npm --prefix frontend run build
```
