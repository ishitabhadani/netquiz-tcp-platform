import React, { useState, useEffect } from "react";
import { TeacherLayout } from "./TeacherLayout";
import { getTeacherQuiz, startTeacherQuiz } from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherShareQuiz({ quizId }) {
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [starting, setStarting] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const studentJoinUrl = `${window.location.origin}/join/${quizId}`;

  useEffect(() => {
    setLoading(true);
    getTeacherQuiz(quizId).then((res) => {
      setLoading(false);
      if (res.ok) {
        setQuiz(res.data);
      } else {
        setError(res.error || "Quiz not found.");
      }
    });
  }, [quizId]);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(studentJoinUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // Fallback
      const input = document.createElement("input");
      input.value = studentJoinUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  const handleStartQuiz = async () => {
    setStarting(true);
    const res = await startTeacherQuiz(quizId);
    setStarting(false);
    if (res.ok) {
      setActionMessage("Quiz is now ACTIVE! Students can join and submit answers.");
      setQuiz((prev) => ({ ...prev, status: "active" }));
    } else {
      setActionMessage(`Error starting quiz: ${res.error}`);
    }
  };

  return (
    <TeacherLayout currentTab="share" activeQuizId={quizId}>
      <div className="teacher-share-root">
        {loading ? (
          <div className="teacher-loading-card">
            <div className="quiz-spinner" />
            <p>Loading quiz share link…</p>
          </div>
        ) : error ? (
          <div className="teacher-error-card">
            <span>⚠️ {error}</span>
            <button className="btn-secondary-sm" onClick={() => navigateTo("/teacher")}>
              Return to Dashboard
            </button>
          </div>
        ) : (
          <div className="share-card-container">
            {/* Header Badge */}
            <div className="share-status-banner">
              <span className="share-check-icon">✓</span>
              <span>Quiz Ready for Students</span>
            </div>

            <div className="share-card-inner">
              <div className="share-quiz-header">
                <span className="share-type-badge">{quiz.type || "Unit Test"}</span>
                <h1 className="share-quiz-title">{quiz.title}</h1>
                <p className="share-quiz-desc">
                  {quiz.description || "Share the unique student link below to begin testing."}
                </p>
              </div>

              {/* Unique Quiz ID Box */}
              <div className="share-quiz-id-box">
                <span className="quiz-id-label">UNIQUE QUIZ IDENTIFIER</span>
                <div className="quiz-id-display">
                  <span className="quiz-id-code">{quiz.quiz_id}</span>
                </div>
                <span className="quiz-id-hint">
                  Students connecting with this ID are strictly isolated to this test cohort.
                </span>
              </div>

              {/* Shareable Student Link Box */}
              <div className="share-link-box">
                <label className="share-link-label">STUDENT ACCESS LINK</label>
                <div className="share-link-input-group">
                  <input
                    type="text"
                    readOnly
                    className="share-link-input"
                    value={studentJoinUrl}
                    onClick={(e) => e.target.select()}
                  />
                  <button
                    className={`btn-copy-link ${copied ? "copied" : ""}`}
                    onClick={handleCopyLink}
                    id="btn-copy-student-link"
                  >
                    {copied ? (
                      <>
                        <span>✓ Copied!</span>
                      </>
                    ) : (
                      <>
                        <span>📋 Copy Link</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Lifecycle Control Status */}
              <div className="share-lifecycle-box">
                <div className="lifecycle-status-row">
                  <span className="lifecycle-label">CURRENT STATUS:</span>
                  <span
                    className={`quiz-status-pill pill-${(
                      quiz.status || "draft"
                    ).toLowerCase()}`}
                  >
                    {quiz.status?.toUpperCase() || "DRAFT"}
                  </span>
                </div>

                {quiz.status === "published" && (
                  <div className="lifecycle-prompt">
                    <p>
                      The quiz is published. To allow students to begin taking the test, start the quiz.
                    </p>
                    <button
                      className="btn-start-quiz-cta"
                      onClick={handleStartQuiz}
                      disabled={starting}
                    >
                      {starting ? "Starting…" : "▶ Start / Activate Quiz Now"}
                    </button>
                  </div>
                )}

                {actionMessage && (
                  <div className="lifecycle-alert alert-success">
                    <span>ℹ️ {actionMessage}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="share-actions-row">
                <button
                  className="btn-share-action btn-open-student"
                  onClick={() => window.open(studentJoinUrl, "_blank")}
                >
                  <span>🎓 Open Student View ↗</span>
                </button>

                <button
                  className="btn-share-action"
                  onClick={() => navigateTo(`/teacher/quiz/${quizId}/leaderboard`)}
                >
                  <span>🏆 Live Leaderboard</span>
                </button>

                <button
                  className="btn-share-action btn-secondary-action"
                  onClick={() => navigateTo(`/teacher/quiz/${quizId}`)}
                >
                  <span>ℹ️ Quiz Details</span>
                </button>

                <button
                  className="btn-share-action btn-secondary-action"
                  onClick={() => navigateTo("/teacher")}
                >
                  <span>📊 Dashboard</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </TeacherLayout>
  );
}
