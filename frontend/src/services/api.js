/**
 * NetQuiz Frontend API Service
 * Handles communication with the FastAPI Application Layer (port 8000)
 */

const API_BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Checks connectivity to the FastAPI backend.
 * @returns {Promise<{status: string, service?: string}>}
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        "Accept": "application/json"
      }
    });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
