/**
 * NetQuiz Frontend API Service Module
 * Centralizes all HTTP communication with the FastAPI Application Layer (Port 8000).
 *
 * Academic Architecture:
 * React Browser (5173) ──[HTTP REST]──> FastAPI (8000) ──[In-Memory]──> QuizManager / TCP Server (5000)
 */

const API_BASE_URL = (
  import.meta.env.DEV
    ? (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api")
    : (import.meta.env.VITE_API_BASE_URL || "https://netquiz-backend-rsba.onrender.com/api")
).replace(/\/+$/, "");

const TEACHER_TOKEN_KEY = "netquiz_teacher_token";

export function getTeacherToken() {
  return localStorage.getItem(TEACHER_TOKEN_KEY) || "";
}

export function setTeacherToken(token) {
  if (token) {
    localStorage.setItem(TEACHER_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TEACHER_TOKEN_KEY);
  }
}

export function removeTeacherToken() {
  localStorage.removeItem(TEACHER_TOKEN_KEY);
}

/**
 * Generic fetch wrapper with timeout and structured error handling.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    const headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    const token = getTeacherToken();
    if (token && !headers.Authorization && !headers.authorization) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers,
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
export async function submitAnswer(connectionId, questionId, answer, studentName = null) {
  const payload = {
    connection_id: connectionId,
    question_id: questionId,
    answer: answer,
  };
  if (studentName) {
    payload.student_name = studentName;
  }
  return request("/quiz/answer", {
    method: "POST",
    body: JSON.stringify(payload),
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

// ─────────────────────────────────────────────────────────────────────────────
// Teacher Dashboard Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/** Authenticates teacher credentials. POST /api/teacher/login */
export async function teacherLogin(email, password) {
  return request("/teacher/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

/** Verifies current teacher session. GET /api/teacher/me */
export async function getTeacherProfile() {
  return request("/teacher/me");
}

/** Retrieves summary statistics for teacher dashboard. GET /api/teacher/stats */
export async function getTeacherStats() {
  return request("/teacher/stats");
}

/** Retrieves all quizzes created by teacher. GET /api/teacher/quizzes */
export async function getTeacherQuizzes() {
  return request("/teacher/quizzes");
}

/** Retrieves complete quiz details (including correct answers). GET /api/teacher/quizzes/:id */
export async function getTeacherQuiz(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}`);
}

/** Creates a new custom quiz with questions. POST /api/teacher/quizzes */
export async function createTeacherQuiz(quizData) {
  return request("/teacher/quizzes", {
    method: "POST",
    body: JSON.stringify(quizData),
  });
}

/** Updates metadata and questions for an existing quiz. PUT /api/teacher/quizzes/:id */
export async function updateTeacherQuiz(quizId, quizData) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}`, {
    method: "PUT",
    body: JSON.stringify(quizData),
  });
}

/** Deletes a quiz. DELETE /api/teacher/quizzes/:id */
export async function deleteTeacherQuiz(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}`, {
    method: "DELETE",
  });
}

/** Transitions quiz from Draft to Published. POST /api/teacher/quizzes/:id/publish */
export async function publishTeacherQuiz(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}/publish`, {
    method: "POST",
  });
}

/** Activates quiz for live participation. POST /api/teacher/quizzes/:id/start */
export async function startTeacherQuiz(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}/start`, {
    method: "POST",
  });
}

/** Ends the quiz, preventing new attempts. POST /api/teacher/quizzes/:id/end */
export async function endTeacherQuiz(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}/end`, {
    method: "POST",
  });
}

/** Retrieves quiz-specific leaderboard for teacher. GET /api/teacher/quizzes/:id/leaderboard */
export async function getTeacherQuizLeaderboard(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}/leaderboard`);
}

/** Retrieves live participant tracking for teacher. GET /api/teacher/quizzes/:id/participants */
export async function getTeacherQuizParticipants(quizId) {
  return request(`/teacher/quizzes/${encodeURIComponent(quizId)}/participants`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Student Quiz Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/** Retrieves public quiz details for student join view (safe, no answers). GET /api/quizzes/:id */
export async function getPublicQuiz(quizId) {
  return request(`/quizzes/${encodeURIComponent(quizId)}`);
}

/** Student joins a specific custom quiz attempt. POST /api/quizzes/:id/join */
export async function joinCustomQuiz(quizId, studentName) {
  return request(`/quizzes/${encodeURIComponent(quizId)}/join`, {
    method: "POST",
    body: JSON.stringify({ student_name: studentName }),
  });
}

/** Retrieves student's current question (safe, no answers). GET /api/quizzes/:id/question */
export async function fetchCustomQuestion(quizId, connectionId) {
  return request(
    `/quizzes/${encodeURIComponent(quizId)}/question?connection_id=${encodeURIComponent(connectionId)}`
  );
}

/** Submits an answer for server evaluation in a custom quiz. POST /api/quizzes/:id/answer */
export async function submitCustomAnswer(quizId, connectionId, questionId, answer, studentName = null) {
  const payload = {
    connection_id: connectionId,
    question_id: questionId,
    answer: answer,
  };
  if (studentName) {
    payload.student_name = studentName;
  }
  return request(`/quizzes/${encodeURIComponent(quizId)}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Retrieves final student summary for completed custom quiz. GET /api/quizzes/:id/summary */
export async function fetchCustomSummary(quizId, connectionId) {
  return request(
    `/quizzes/${encodeURIComponent(quizId)}/summary?connection_id=${encodeURIComponent(connectionId)}`
  );
}

/** Retrieves the public leaderboard for a custom quiz. GET /api/quizzes/:id/leaderboard */
export async function fetchCustomLeaderboard(quizId) {
  return request(`/quizzes/${encodeURIComponent(quizId)}/leaderboard`);
}

