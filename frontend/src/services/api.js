/**
 * NetQuiz Frontend API Service Module
 * Centralizes all HTTP communication with the FastAPI Application Layer (Port 8000).
 * 
 * Academic Architecture:
 * React Browser (5173) ──[HTTP REST]──> FastAPI (8000) ──[In-Memory]──> TCP Server (5000)
 */

const API_BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Generic fetch wrapper with timeout and JSON parsing.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    const message = err.name === "AbortError" 
      ? "Connection timed out (backend unreachable)" 
      : (err.message || "Network error");
    return { ok: false, error: message };
  }
}

/**
 * Checks FastAPI service health.
 * GET /api/health
 */
export async function getHealth() {
  return request("/health");
}

/**
 * Queries live metrics from the genuine Python TCP socket layer (port 5000).
 * GET /api/server/status
 */
export async function getServerStatus() {
  return request("/server/status");
}

/**
 * Queries active TCP client connections from the server client registry.
 * GET /api/server/clients
 */
export async function getServerClients() {
  return request("/server/clients");
}

/**
 * Retrieves question bank metadata and quiz configurations.
 * GET /api/quiz/info
 */
export async function getQuizInfo() {
  return request("/quiz/info");
}

/**
 * Retrieves server-evaluated student rankings.
 * GET /api/quiz/leaderboard
 */
export async function getLeaderboard() {
  return request("/quiz/leaderboard");
}
