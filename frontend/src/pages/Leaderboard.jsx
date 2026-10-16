import React, { useState, useEffect, useCallback } from "react";
import { getLeaderboard } from "../services/api";

const MEDAL = ["🥇", "🥈", "🥉"];

/**
 * Leaderboard Page — Live ranking from the server QuizManager.
 *
 * Academic note: Rankings are computed server-side by the QuizManager
 * using the completed_history list, not by client-side calculation.
 */
export function Leaderboard({ onBack }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await getLeaderboard();
    setLoading(false);
    if (res.ok) {
      setEntries(res.data.leaderboard || []);
      setLastRefreshed(new Date().toLocaleTimeString());
    } else {
      setError(res.error || "Failed to load leaderboard.");
    }
  }, []);

  useEffect(() => {
    fetchLeaderboard();
    const interval = setInterval(fetchLeaderboard, 8000);
    return () => clearInterval(interval);
  }, [fetchLeaderboard]);

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-card">
        {/* Header */}
        <div className="lb-header">
          <div className="lb-title-row">
            <span className="lb-icon">🏆</span>
            <div>
              <h2 className="lb-title">Live Leaderboard</h2>
              <p className="lb-subtitle">Server-side rankings · Ranked by score (descending)</p>
            </div>
          </div>
          <div className="lb-refresh-row">
            {lastRefreshed && (
              <span className="lb-refresh-time">
                Updated {lastRefreshed}
              </span>
            )}
            <button
              className="btn-refresh-lb"
              onClick={fetchLeaderboard}
              disabled={loading}
              id="refresh-leaderboard-btn"
            >
              {loading ? "↻ Loading…" : "↻ Refresh"}
            </button>
          </div>
        </div>

        {/* Academic note */}
        <div className="lb-academic-note">
          <span>📡</span>
          <span>
            Rankings fetched from{" "}
            <code>GET /api/quiz/leaderboard</code> → QuizManager.get_leaderboard()
          </span>
        </div>

        {/* Table */}
        {loading && entries.length === 0 ? (
          <div className="lb-loading">
            <div className="quiz-spinner" />
            <p>Fetching rankings from server…</p>
          </div>
        ) : error ? (
          <div className="lb-error">
            <span>⚠️</span> {error}
          </div>
        ) : entries.length === 0 ? (
          <div className="lb-empty">
            <span className="lb-empty-icon">📭</span>
            <p>No completed quiz sessions yet.</p>
            <p className="lb-empty-sub">Complete the quiz to appear here!</p>
          </div>
        ) : (
          <div className="lb-table-wrap">
            <table className="lb-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Student</th>
                  <th>Score</th>
                  <th>Percentage</th>
                  <th>Completed At</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, idx) => (
                  <tr
                    key={`${entry.student_name}-${entry.rank}`}
                    className={`lb-row ${idx === 0 ? "lb-row-gold" : idx === 1 ? "lb-row-silver" : idx === 2 ? "lb-row-bronze" : ""}`}
                  >
                    <td className="lb-rank-cell">
                      {idx < 3 ? (
                        <span className="lb-medal">{MEDAL[idx]}</span>
                      ) : (
                        <span className="lb-rank-num">#{entry.rank}</span>
                      )}
                    </td>
                    <td className="lb-name-cell">{entry.student_name}</td>
                    <td className="lb-score-cell">
                      {entry.score} / {entry.total_questions}
                    </td>
                    <td>
                      <div className="lb-pct-bar-wrap">
                        <div className="lb-pct-bar-track">
                          <div
                            className="lb-pct-bar-fill"
                            style={{
                              width: `${entry.percentage}%`,
                              background:
                                entry.percentage >= 90
                                  ? "#22c55e"
                                  : entry.percentage >= 70
                                  ? "#3b82f6"
                                  : entry.percentage >= 50
                                  ? "#f59e0b"
                                  : "#ef4444",
                            }}
                          />
                        </div>
                        <span className="lb-pct-val">{entry.percentage}%</span>
                      </div>
                    </td>
                    <td className="lb-time-cell">
                      {entry.completion_time || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Back button */}
        <button
          className="btn-back-home"
          onClick={onBack}
          id="back-to-home-btn"
        >
          ← Back to Home
        </button>
      </div>
    </div>
  );
}
