import React, { useState, useEffect, useCallback } from "react";
import { TeacherLayout } from "./TeacherLayout";
import {
  getTeacherQuiz,
  publishTeacherQuiz,
  startTeacherQuiz,
  endTeacherQuiz,
} from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherQuizDetails({ quizId }) {
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const loadQuiz = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await getTeacherQuiz(quizId);
    setLoading(false);
    if (res.ok) {
      setQuiz(res.data);
    } else {
      setError(res.error || "Quiz not found.");
    }
  }, [quizId]);

  useEffect(() => {
    loadQuiz();
  }, [loadQuiz]);

  const handlePublish = async () => {
    setActionLoading(true);
    const res = await publishTeacherQuiz(quizId);
    setActionLoading(false);
    if (res.ok) {
      setActionMessage("Quiz published successfully.");
      loadQuiz();
    } else {
      setActionMessage(res.error || "Failed to publish.");
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    const res = await startTeacherQuiz(quizId);
    setActionLoading(false);
    if (res.ok) {
      setActionMessage("Quiz is now ACTIVE for students.");
      loadQuiz();
    } else {
      setActionMessage(res.error || "Failed to start quiz.");
    }
  };

  const handleEnd = async () => {
    if (!window.confirm("Are you sure you want to end this quiz? Students will no longer be able to submit.")) {
      return;
    }
    setActionLoading(true);
    const res = await endTeacherQuiz(quizId);
    setActionLoading(false);
    if (res.ok) {
      setActionMessage("Quiz ended. Results preserved.");
      loadQuiz();
    } else {
      setActionMessage(res.error || "Failed to end quiz.");
    }
  };

  const status = (quiz?.status || "draft").toUpperCase();

  return (
    <TeacherLayout currentTab="details" activeQuizId={quizId}>
      <div className="teacher-details-root">
        {loading ? (
          <div className="teacher-loading-card">
            <div className="quiz-spinner" />
            <p>Loading quiz details…</p>
          </div>
        ) : error ? (
          <div className="teacher-error-card">
            <span>⚠️ {error}</span>
            <button className="btn-secondary-sm" onClick={() => navigateTo("/teacher")}>
              Back to Dashboard
            </button>
          </div>
        ) : (
          <>
            {/* Header / Hero */}
            <div className="details-hero-card">
              <div className="details-hero-top">
                <div className="details-hero-badges">
                  <span className={`quiz-status-pill pill-${status.toLowerCase()}`}>
                    {status === "ACTIVE" && <span className="pulse-dot" />}
                    {status}
                  </span>
                  <span className="quiz-type-pill">{quiz.type || "Unit Test"}</span>
                  {quiz.subject && <span className="quiz-category-pill">{quiz.subject}</span>}
                </div>

                <div className="quiz-id-pill">
                  <span>ID: </span>
                  <code>{quiz.quiz_id}</code>
                </div>
              </div>

              <h1 className="details-hero-title">{quiz.title}</h1>
              <p className="details-hero-desc">
                {quiz.description || "No description or instructions provided."}
              </p>

              {/* Action Toolbar */}
              <div className="details-action-bar">
                <div className="action-bar-left">
                  <button
                    className="btn-action-primary"
                    onClick={() => navigateTo(`/teacher/quiz/${quizId}/share`)}
                  >
                    <span>🔗 Share Link</span>
                  </button>

                  <button
                    className="btn-action-outline"
                    onClick={() => navigateTo(`/teacher/quiz/${quizId}/leaderboard`)}
                  >
                    <span>🏆 Leaderboard</span>
                  </button>

                  <button
                    className="btn-action-outline"
                    onClick={() => navigateTo(`/teacher/quiz/${quizId}/edit`)}
                  >
                    <span>✏️ Edit Quiz</span>
                  </button>
                </div>

                <div className="action-bar-right">
                  {status === "DRAFT" && (
                    <button
                      className="btn-status-cta btn-publish"
                      onClick={handlePublish}
                      disabled={actionLoading}
                    >
                      Publish Quiz
                    </button>
                  )}

                  {status === "PUBLISHED" && (
                    <button
                      className="btn-status-cta btn-start"
                      onClick={handleStart}
                      disabled={actionLoading}
                    >
                      ▶ Start / Activate Quiz
                    </button>
                  )}

                  {status === "ACTIVE" && (
                    <button
                      className="btn-status-cta btn-end"
                      onClick={handleEnd}
                      disabled={actionLoading}
                    >
                      ⏹ End Quiz
                    </button>
                  )}
                </div>
              </div>

              {actionMessage && (
                <div className="details-alert-banner">
                  <span>ℹ️ {actionMessage}</span>
                </div>
              )}
            </div>

            {/* Quick Metrics */}
            <div className="details-metrics-row">
              <div className="metric-box">
                <span className="metric-num">{quiz.questions?.length || 0}</span>
                <span className="metric-text">Questions</span>
              </div>
              <div className="metric-box">
                <span className="metric-num">{quiz.participants?.length || 0}</span>
                <span className="metric-text">Participants</span>
              </div>
              <div className="metric-box">
                <span className="metric-num">{quiz.leaderboard?.length || 0}</span>
                <span className="metric-text">Submissions</span>
              </div>
              <div className="metric-box">
                <span className="metric-num">
                  {new Date(quiz.created_at).toLocaleDateString()}
                </span>
                <span className="metric-text">Created On</span>
              </div>
            </div>

            {/* Questions List preview */}
            <div className="details-questions-section">
              <div className="section-title-wrap">
                <h2>Quiz Questions ({quiz.questions?.length || 0})</h2>
                <p>Teacher View: correct answers are visible below for grading verification.</p>
              </div>

              <div className="details-questions-list">
                {quiz.questions?.map((q, idx) => (
                  <div key={q.id || idx} className="details-q-card">
                    <div className="details-q-header">
                      <span className="q-badge">Question {idx + 1}</span>
                      <span className="q-meta">
                        {q.points || 1} pt &bull; ⏱️ {q.time_limit || 30}s &bull; Type: {q.type}
                      </span>
                    </div>

                    <p className="details-q-prompt">{q.question}</p>

                    <div className="details-options-list">
                      {q.options?.map((opt, oIdx) => {
                        const letter = String.fromCharCode(65 + oIdx);
                        const isCorrect = q.correct_answer === letter;

                        return (
                          <div
                            key={letter}
                            className={`details-opt-item ${isCorrect ? "opt-correct" : ""}`}
                          >
                            <span className="details-opt-letter">{letter}</span>
                            <span className="details-opt-text">{opt}</span>
                            {isCorrect && (
                              <span className="details-correct-badge">✓ Correct Answer</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </TeacherLayout>
  );
}
