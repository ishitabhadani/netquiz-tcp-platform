import React, { useState, useEffect, useCallback } from "react";
import { TeacherLayout } from "./TeacherLayout";
import {
  getTeacherStats,
  getTeacherQuizzes,
  publishTeacherQuiz,
  startTeacherQuiz,
  endTeacherQuiz,
} from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherDashboard() {
  const [stats, setStats] = useState({
    total_quizzes: 0,
    active_quizzes: 0,
    total_participants: 0,
    total_questions: 0,
  });
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [toast, setToast] = useState(null);
  const [filter, setFilter] = useState("all"); // 'all' | 'active' | 'published' | 'draft' | 'ended'

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, quizzesRes] = await Promise.all([
        getTeacherStats(),
        getTeacherQuizzes(),
      ]);

      if (statsRes.ok) {
        setStats(statsRes.data);
      }
      if (quizzesRes.ok) {
        setQuizzes(quizzesRes.data || []);
      } else {
        setError(quizzesRes.error || "Failed to load quizzes.");
      }
    } catch {
      setError("An unexpected error occurred while fetching dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePublish = async (quizId, title) => {
    setActionLoadingId(quizId);
    const res = await publishTeacherQuiz(quizId);
    setActionLoadingId(null);
    if (res.ok) {
      showToast(`Quiz "${title}" published successfully.`);
      loadData();
    } else {
      showToast(res.error || "Failed to publish quiz.", "error");
    }
  };

  const handleStart = async (quizId, title) => {
    setActionLoadingId(quizId);
    const res = await startTeacherQuiz(quizId);
    setActionLoadingId(null);
    if (res.ok) {
      showToast(`Quiz "${title}" is now ACTIVE for students!`);
      loadData();
    } else {
      showToast(res.error || "Failed to start quiz.", "error");
    }
  };

  const handleEnd = async (quizId, title) => {
    if (!window.confirm(`Are you sure you want to end "${title}"? Students will no longer be able to start new attempts.`)) {
      return;
    }
    setActionLoadingId(quizId);
    const res = await endTeacherQuiz(quizId);
    setActionLoadingId(null);
    if (res.ok) {
      showToast(`Quiz "${title}" ended. Leaderboard preserved.`);
      loadData();
    } else {
      showToast(res.error || "Failed to end quiz.", "error");
    }
  };

  const filteredQuizzes = quizzes.filter((q) => {
    if (filter === "all") return true;
    return q.status.toLowerCase() === filter.toLowerCase();
  });

  return (
    <TeacherLayout currentTab="dashboard">
      {/* Toast Banner */}
      {toast && (
        <div className={`teacher-toast toast-${toast.type}`}>
          <span>{toast.type === "success" ? "✅" : "⚠️"}</span>
          <span>{toast.message}</span>
        </div>
      )}

      {/* Dashboard Header */}
      <div className="teacher-page-header">
        <div>
          <h1 className="teacher-page-title">NetQuiz Teacher Dashboard</h1>
          <p className="teacher-page-desc">
            Monitor quizzes, manage independent student cohorts, and supervise live TCP sessions.
          </p>
        </div>
        <button
          className="btn-create-quiz-cta"
          onClick={() => navigateTo("/teacher/create")}
          id="btn-create-new-quiz"
        >
          <span>➕ Create New Quiz</span>
        </button>
      </div>

      {/* KPI Metric Cards */}
      <div className="teacher-stats-grid">
        <div className="teacher-stat-card">
          <div className="stat-card-icon stat-blue">📚</div>
          <div className="stat-card-body">
            <span className="stat-label">Total Quizzes</span>
            <span className="stat-value">{stats.total_quizzes}</span>
            <span className="stat-sub">Across all subjects</span>
          </div>
        </div>

        <div className="teacher-stat-card">
          <div className="stat-card-icon stat-green">⚡</div>
          <div className="stat-card-body">
            <span className="stat-label">Active Quizzes</span>
            <span className="stat-value">{stats.active_quizzes}</span>
            <span className="stat-sub">Open for live submission</span>
          </div>
        </div>

        <div className="teacher-stat-card">
          <div className="stat-card-icon stat-indigo">👥</div>
          <div className="stat-card-body">
            <span className="stat-label">Total Participants</span>
            <span className="stat-value">{stats.total_participants}</span>
            <span className="stat-sub">Tracked across all quizzes</span>
          </div>
        </div>

        <div className="teacher-stat-card">
          <div className="stat-card-icon stat-amber">❓</div>
          <div className="stat-card-body">
            <span className="stat-label">Total Questions</span>
            <span className="stat-value">{stats.total_questions}</span>
            <span className="stat-sub">Configured in question banks</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Recent Quizzes Section */}
      <div className="teacher-section-block">
        <div className="section-toolbar">
          <div>
            <h2 className="teacher-section-heading">Recent Quizzes</h2>
            <p className="teacher-section-sub">
              Each quiz operates on its own isolated Quiz ID and scoped leaderboard.
            </p>
          </div>

          <div className="filter-pill-group">
            {[
              { id: "all", label: "All" },
              { id: "active", label: "Active" },
              { id: "published", label: "Published" },
              { id: "draft", label: "Draft" },
              { id: "ended", label: "Ended" },
            ].map((f) => (
              <button
                key={f.id}
                className={`filter-pill ${filter === f.id ? "active" : ""}`}
                onClick={() => setFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="teacher-loading-card">
            <div className="quiz-spinner" />
            <p>Loading teacher quizzes…</p>
          </div>
        ) : error ? (
          <div className="teacher-error-card">
            <span>⚠️ {error}</span>
            <button className="btn-secondary-sm" onClick={loadData}>
              Retry
            </button>
          </div>
        ) : filteredQuizzes.length === 0 ? (
          <div className="teacher-empty-card">
            <span className="empty-icon">📝</span>
            <h3>No {filter !== "all" ? filter : ""} quizzes found</h3>
            <p>Get started by creating your first custom quiz for your students.</p>
            <button
              className="btn-create-quiz-cta"
              onClick={() => navigateTo("/teacher/create")}
            >
              + Create Quiz
            </button>
          </div>
        ) : (
          <div className="teacher-quiz-grid">
            {filteredQuizzes.map((quiz) => {
              const status = (quiz.status || "draft").toUpperCase();
              const isActionLoading = actionLoadingId === quiz.quiz_id;

              return (
                <div key={quiz.quiz_id} className={`teacher-quiz-card card-status-${status.toLowerCase()}`}>
                  {/* Card Header */}
                  <div className="quiz-card-top">
                    <div className="quiz-card-badge-row">
                      <span className={`quiz-status-pill pill-${status.toLowerCase()}`}>
                        {status === "ACTIVE" && <span className="pulse-dot" />}
                        {status}
                      </span>
                      <span className="quiz-type-pill">{quiz.type || "Test"}</span>
                      {quiz.subject && <span className="quiz-category-pill">{quiz.subject}</span>}
                    </div>

                    <div className="quiz-id-pill" title="Unique Quiz Identifier">
                      <code>{quiz.quiz_id}</code>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <div className="quiz-card-body">
                    <h3 className="quiz-card-title">{quiz.title}</h3>
                    <p className="quiz-card-desc">
                      {quiz.description || "No description provided."}
                    </p>
                  </div>

                  {/* Card Stats */}
                  <div className="quiz-card-meta-row">
                    <div className="meta-item">
                      <span className="meta-icon">❓</span>
                      <span>{quiz.question_count ?? quiz.questions?.length ?? 0} Questions</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-icon">👥</span>
                      <span>{quiz.participant_count ?? quiz.participants?.length ?? 0} Participants</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-icon">📅</span>
                      <span>{new Date(quiz.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Actions Toolbar */}
                  <div className="quiz-card-actions">
                    <div className="action-buttons-left">
                      <button
                        className="btn-quiz-action"
                        onClick={() => navigateTo(`/teacher/quiz/${quiz.quiz_id}`)}
                        title="View details and questions"
                      >
                        👁️ View
                      </button>

                      <button
                        className="btn-quiz-action"
                        onClick={() => navigateTo(`/teacher/quiz/${quiz.quiz_id}/edit`)}
                        title="Edit quiz"
                      >
                        ✏️ Edit
                      </button>

                      <button
                        className="btn-quiz-action"
                        onClick={() => navigateTo(`/teacher/quiz/${quiz.quiz_id}/leaderboard`)}
                        title="View scoped quiz leaderboard"
                      >
                        🏆 Leaderboard
                      </button>

                      <button
                        className="btn-quiz-action"
                        onClick={() => navigateTo(`/teacher/quiz/${quiz.quiz_id}/share`)}
                        title="Get shareable student link"
                      >
                        🔗 Share
                      </button>
                    </div>

                    {/* Status transition button */}
                    <div className="action-buttons-right">
                      {status === "DRAFT" && (
                        <button
                          className="btn-status-action btn-publish"
                          onClick={() => handlePublish(quiz.quiz_id, quiz.title)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? "..." : "Publish"}
                        </button>
                      )}

                      {status === "PUBLISHED" && (
                        <button
                          className="btn-status-action btn-start"
                          onClick={() => handleStart(quiz.quiz_id, quiz.title)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? "..." : "▶ Start Quiz"}
                        </button>
                      )}

                      {status === "ACTIVE" && (
                        <button
                          className="btn-status-action btn-end"
                          onClick={() => handleEnd(quiz.quiz_id, quiz.title)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? "..." : "⏹ End Quiz"}
                        </button>
                      )}

                      {status === "ENDED" && (
                        <span className="badge-ended-tag">Ended</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </TeacherLayout>
  );
}
