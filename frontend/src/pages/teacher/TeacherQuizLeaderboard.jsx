import React, { useState, useEffect, useCallback } from "react";
import { TeacherLayout } from "./TeacherLayout";
import {
  getTeacherQuiz,
  getTeacherQuizLeaderboard,
  getTeacherQuizParticipants,
} from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherQuizLeaderboard({ quizId }) {
  const [quiz, setQuiz] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [sortBy, setSortBy] = useState("score"); // 'score' | 'time' | 'name'
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [quizRes, lbRes, partRes] = await Promise.all([
        getTeacherQuiz(quizId),
        getTeacherQuizLeaderboard(quizId),
        getTeacherQuizParticipants(quizId),
      ]);

      if (quizRes.ok) setQuiz(quizRes.data);
      if (lbRes.ok) setLeaderboard(lbRes.data?.leaderboard || []);
      if (partRes.ok) setParticipants(partRes.data || []);

      setLastUpdated(new Date().toLocaleTimeString());
    } catch {
      setError("Failed to fetch live leaderboard data.");
    } finally {
      setLoading(false);
    }
  }, [quizId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Live polling interval
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  // Sorting
  const sortedEntries = [...leaderboard].sort((a, b) => {
    if (sortBy === "score") {
      return (b.score ?? 0) - (a.score ?? 0);
    } else if (sortBy === "time") {
      return (a.time_taken ?? 999999) - (b.time_taken ?? 999999);
    } else if (sortBy === "name") {
      return (a.student_name || "").localeCompare(b.student_name || "");
    }
    return 0;
  });

  // CSV Export
  const handleExportCSV = () => {
    if (sortedEntries.length === 0) {
      alert("No submissions available to export.");
      return;
    }

    const headers = ["Rank", "Student Name", "Score", "Total", "Percentage", "Time Taken (s)", "Submitted At"];
    const rows = sortedEntries.map((entry, idx) => [
      idx + 1,
      `"${entry.student_name}"`,
      entry.score,
      entry.total_questions,
      `${entry.percentage}%`,
      entry.time_taken ?? "-",
      `"${entry.completed_at || entry.submitted_at || ""}"`,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `quiz_${quizId}_leaderboard.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalQuestions = quiz?.questions?.length || 1;
  const avgScore =
    leaderboard.length > 0
      ? (
          leaderboard.reduce((acc, curr) => acc + (curr.score || 0), 0) /
          leaderboard.length
        ).toFixed(1)
      : 0;

  return (
    <TeacherLayout currentTab="leaderboard" activeQuizId={quizId}>
      <div className="teacher-lb-root">
        {/* Header */}
        <div className="teacher-lb-header">
          <div className="lb-header-info">
            <div className="lb-badge-row">
              <span className="quiz-id-pill">
                <code>{quizId}</code>
              </span>
              <span
                className={`quiz-status-pill pill-${(
                  quiz?.status || "draft"
                ).toLowerCase()}`}
              >
                {quiz?.status?.toUpperCase() || "PUBLISHED"}
              </span>
            </div>
            <h1 className="teacher-lb-title">
              {quiz?.title || "Quiz Leaderboard"}
            </h1>
            <p className="teacher-lb-sub">
              Live scoped leaderboard &bull; Strictly isolates participants to Quiz ID{" "}
              <code>{quizId}</code>
            </p>
          </div>

          <div className="lb-controls-wrap">
            <div className="lb-live-indicator">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                <span className="toggle-slider" />
                <span className="toggle-text">
                  {autoRefresh ? "🟢 Live Polling (5s)" : "⏸️ Polling Paused"}
                </span>
              </label>
              {lastUpdated && (
                <span className="lb-last-updated">Updated {lastUpdated}</span>
              )}
            </div>

            <div className="lb-action-buttons">
              <button
                className="btn-lb-action"
                onClick={fetchData}
                disabled={loading}
                title="Refresh rankings immediately"
              >
                ↻ Refresh
              </button>

              <button
                className="btn-lb-action btn-export"
                onClick={handleExportCSV}
                title="Download CSV report"
              >
                📥 Export CSV
              </button>
            </div>
          </div>
        </div>

        {/* Scoped Metrics Bar */}
        <div className="lb-metrics-grid">
          <div className="lb-metric-card">
            <span className="metric-icon">👥</span>
            <div>
              <span className="metric-val">{participants.length}</span>
              <span className="metric-lbl">Total Joined</span>
            </div>
          </div>

          <div className="lb-metric-card">
            <span className="metric-icon">✅</span>
            <div>
              <span className="metric-val">{leaderboard.length}</span>
              <span className="metric-lbl">Submissions Received</span>
            </div>
          </div>

          <div className="lb-metric-card">
            <span className="metric-icon">📊</span>
            <div>
              <span className="metric-val">
                {avgScore} / {totalQuestions}
              </span>
              <span className="metric-lbl">Average Score</span>
            </div>
          </div>

          <div className="lb-metric-card">
            <span className="metric-icon">🏆</span>
            <div>
              <span className="metric-val">
                {leaderboard[0] ? `${leaderboard[0].score}/${leaderboard[0].total_questions}` : "-"}
              </span>
              <span className="metric-lbl">Top Score</span>
            </div>
          </div>
        </div>

        {/* Sort Bar */}
        <div className="lb-sort-bar">
          <span className="sort-label">Sort By:</span>
          <button
            className={`btn-sort-pill ${sortBy === "score" ? "active" : ""}`}
            onClick={() => setSortBy("score")}
          >
            Highest Score
          </button>
          <button
            className={`btn-sort-pill ${sortBy === "time" ? "active" : ""}`}
            onClick={() => setSortBy("time")}
          >
            Fastest Time
          </button>
          <button
            className={`btn-sort-pill ${sortBy === "name" ? "active" : ""}`}
            onClick={() => setSortBy("name")}
          >
            Student Name
          </button>
        </div>

        {/* Leaderboard Table */}
        <div className="teacher-lb-table-card">
          {loading && leaderboard.length === 0 ? (
            <div className="teacher-loading-card">
              <div className="quiz-spinner" />
              <p>Fetching rankings from server…</p>
            </div>
          ) : error ? (
            <div className="teacher-error-card">
              <span>⚠️ {error}</span>
            </div>
          ) : sortedEntries.length === 0 ? (
            <div className="teacher-empty-card">
              <span className="empty-icon">📭</span>
              <h3>No Submissions Yet</h3>
              <p>
                Share the student link to invite students:{" "}
                <code>{window.location.origin}/join/{quizId}</code>
              </p>
              <button
                className="btn-create-quiz-cta"
                onClick={() => navigateTo(`/teacher/quiz/${quizId}/share`)}
              >
                🔗 Get Share Link
              </button>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="teacher-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Student</th>
                    <th>Score</th>
                    <th>Percentage</th>
                    <th>Time Taken</th>
                    <th>Submission Status</th>
                    <th>Submitted At</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEntries.map((entry, idx) => {
                    const rank = idx + 1;
                    const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;
                    const timeDisplay = entry.time_taken
                      ? `${Math.floor(entry.time_taken / 60)}m ${entry.time_taken % 60}s`
                      : "-";

                    return (
                      <tr key={entry.student_name + idx} className={`rank-row-${rank}`}>
                        <td className="cell-rank">
                          <span className="rank-badge">{medal}</span>
                        </td>
                        <td className="cell-student">
                          <span className="student-name-text">{entry.student_name}</span>
                        </td>
                        <td className="cell-score">
                          <strong>{entry.score}</strong> / {entry.total_questions}
                        </td>
                        <td className="cell-percentage">
                          <div className="percent-bar-wrap">
                            <div
                              className="percent-fill"
                              style={{ width: `${entry.percentage}%` }}
                            />
                            <span>{entry.percentage}%</span>
                          </div>
                        </td>
                        <td className="cell-time">{timeDisplay}</td>
                        <td className="cell-status">
                          <span className="status-badge-submitted">Completed</span>
                        </td>
                        <td className="cell-date">
                          {entry.completed_at
                            ? new Date(entry.completed_at).toLocaleTimeString()
                            : "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </TeacherLayout>
  );
}
