/**
 * NetQuiz Frontend API Service Module
 * Centralizes all HTTP communication with the FastAPI Application Layer (Port 8000).
 *
 * Academic Architecture:
 * React Browser (5173) ──[HTTP REST]──> FastAPI (8000) ──[In-Memory]──> QuizManager / TCP Server (5000)
 */

const API_BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Generic fetch wrapper with timeout and structured error handling.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      let detail = errorText;
      try {
        const parsed = JSON.parse(errorText);
        detail = parsed.detail || errorText;
      } catch (_) {}
      throw new Error(detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    const message =
      err.name === "AbortError"
        ? "Connection timed out (backend unreachable)"
        : err.message || "Network error";
    return { ok: false, error: message };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Infrastructure / Status Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/** Checks FastAPI service health. GET /api/health */
export async function getHealth() {
  return request("/health");
}

/** Queries live metrics from the TCP socket layer. GET /api/server/status */
export async function getServerStatus() {
  return request("/server/status");
}

/** Queries active TCP client connections. GET /api/server/clients */
export async function getServerClients() {
  return request("/server/clients");
}

/** Retrieves question bank metadata. GET /api/quiz/info */
export async function getQuizInfo() {
  return request("/quiz/info");
}

/** Retrieves server-evaluated student rankings. GET /api/quiz/leaderboard */
export async function getLeaderboard() {
  return request("/quiz/leaderboard");
}

// ─────────────────────────────────────────────────────────────────────────────
// Stage 6: Quiz Participation Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Joins a new quiz session on the server.
 * POST /api/quiz/join
 * @param {string} studentName
 * @returns {{ ok, data: { connection_id, student_name, total_questions, message } }}
 */
export async function joinQuiz(studentName) {
  return request("/quiz/join", {
    method: "POST",
    body: JSON.stringify({ student_name: studentName }),
  });
}

/**
 * Fetches the current question for an active session.
 * GET /api/quiz/question?connection_id=...
 * NOTE: The server NEVER sends the correct_answer in this response.
 * @param {string} connectionId
 * @returns {{ ok, data: { question_number, total_questions, question_id, question, options } }}
 */
export async function fetchCurrentQuestion(connectionId) {
  return request(
    `/quiz/question?connection_id=${encodeURIComponent(connectionId)}`
  );
}

/**
 * Submits an answer for server-side evaluation.
 * POST /api/quiz/answer
 * @param {string} connectionId
 * @param {number} questionId
 * @param {string} answer - One of 'A','B','C','D'
 * @returns {{ ok, data: { correct, submitted_answer, correct_answer, explanation, current_score, quiz_completed } }}
 */
export async function submitAnswer(connectionId, questionId, answer) {
  return request("/quiz/answer", {
    method: "POST",
    body: JSON.stringify({
      connection_id: connectionId,
      question_id: questionId,
      answer: answer,
    }),
  });
}

/**
 * Fetches the final quiz summary for a completed session.
 * GET /api/quiz/summary?connection_id=...
 * @param {string} connectionId
 * @returns {{ ok, data: { student_name, score, total_questions, correct_answers, incorrect_answers, percentage } }}
 */
export async function fetchQuizSummary(connectionId) {
  return request(
    `/quiz/summary?connection_id=${encodeURIComponent(connectionId)}`
  );
}
