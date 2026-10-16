import React from "react";

const GRADE_MAP = [
  { min: 90, label: "Distinction", color: "#22c55e", icon: "🏆" },
  { min: 70, label: "First Class", color: "#3b82f6", icon: "🥇" },
  { min: 50, label: "Pass", color: "#f59e0b", icon: "📘" },
  { min: 0,  label: "Fail",  color: "#ef4444", icon: "📉" },
];

function getGrade(percentage) {
  return GRADE_MAP.find((g) => percentage >= g.min);
}

/**
 * Results Page — Final score display with grade classification.
 *
 * Academic note: The score displayed here comes from the server-side
 * QuizManager, not from any client-computed value.
 */
export function Results({ summary, onViewLeaderboard, onRetry }) {
  const {
    student_name,
    score,
    total_questions,
    correct_answers,
    incorrect_answers,
    percentage,
    completion_time,
  } = summary;

  const grade = getGrade(percentage);
  const circumference = 2 * Math.PI * 54; // r=54
  const dashOffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="results-page">
      <div className="results-card">
        {/* Header */}
        <div className="results-header">
          <span className="results-grade-icon">{grade.icon}</span>
          <h2 className="results-title">Quiz Complete!</h2>
          <p className="results-student">{student_name}</p>
        </div>

        {/* Circular score ring */}
        <div className="results-ring-wrap">
          <svg width="140" height="140" viewBox="0 0 140 140">
            {/* Track */}
            <circle
              cx="70" cy="70" r="54"
              fill="none"
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="10"
            />
            {/* Progress */}
            <circle
              cx="70" cy="70" r="54"
              fill="none"
              stroke={grade.color}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              transform="rotate(-90 70 70)"
              style={{ transition: "stroke-dashoffset 1s ease" }}
            />
            <text x="70" y="66" textAnchor="middle" className="ring-score-text">
              {score}/{total_questions}
            </text>
            <text x="70" y="84" textAnchor="middle" className="ring-pct-text">
              {percentage}%
            </text>
          </svg>
        </div>

        {/* Grade badge */}
        <div className="results-grade-badge" style={{ borderColor: grade.color, color: grade.color }}>
          {grade.label}
        </div>

        {/* Stat grid */}
        <div className="results-stats-grid">
          <div className="results-stat">
            <span className="rs-icon">✅</span>
            <span className="rs-value">{correct_answers}</span>
            <span className="rs-label">Correct</span>
          </div>
          <div className="results-stat">
            <span className="rs-icon">❌</span>
            <span className="rs-value">{incorrect_answers}</span>
            <span className="rs-label">Incorrect</span>
          </div>
          <div className="results-stat">
            <span className="rs-icon">📊</span>
            <span className="rs-value">{percentage}%</span>
            <span className="rs-label">Score</span>
          </div>
        </div>

        {/* Academic note */}
        <div className="results-academic-note">
          <span className="note-icon">🔒</span>
          <span>
            Score evaluated strictly server-side by Python QuizManager.
            No client-side score computation.
          </span>
        </div>

        {completion_time && (
          <p className="results-time">Completed at: {completion_time}</p>
        )}

        {/* Actions */}
        <div className="results-actions">
          <button
            className="btn-leaderboard"
            onClick={onViewLeaderboard}
            id="view-leaderboard-btn"
          >
            🏅 View Leaderboard
          </button>
          <button
            className="btn-retry"
            onClick={onRetry}
            id="retry-quiz-btn"
          >
            🔄 Try Again
          </button>
        </div>
      </div>
    </div>
  );
}
