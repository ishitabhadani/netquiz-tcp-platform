import React, { useEffect } from "react";
import { getTeacherToken, removeTeacherToken } from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherLayout({ currentTab = "dashboard", activeQuizId = null, children }) {
  useEffect(() => {
    const token = getTeacherToken();
    if (!token) {
      navigateTo("/teacher/login");
    }
  }, []);

  const handleLogout = () => {
    removeTeacherToken();
    navigateTo("/teacher/login");
  };

  return (
    <div className="teacher-layout-root">
      {/* Sidebar */}
      <aside className="teacher-sidebar">
        <div className="teacher-sidebar-brand" onClick={() => navigateTo("/teacher")}>
          <div className="brand-logo-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
          </div>
          <div>
            <div className="teacher-brand-name">
              <span>NETQUIZ</span>
              <span className="teacher-faculty-badge">TEACHER</span>
            </div>
            <p className="teacher-brand-sub">Faculty Dashboard</p>
          </div>
        </div>

        <nav className="teacher-nav-menu">
          <button
            className={`teacher-nav-item ${currentTab === "dashboard" ? "active" : ""}`}
            onClick={() => navigateTo("/teacher")}
          >
            <span className="teacher-nav-icon">📊</span>
            <span>Dashboard</span>
          </button>

          <button
            className={`teacher-nav-item ${currentTab === "my-quizzes" ? "active" : ""}`}
            onClick={() => navigateTo("/teacher")}
          >
            <span className="teacher-nav-icon">📚</span>
            <span>My Quizzes</span>
          </button>

          <button
            className={`teacher-nav-item ${currentTab === "create" ? "active" : ""}`}
            onClick={() => navigateTo("/teacher/create")}
          >
            <span className="teacher-nav-icon">➕</span>
            <span>Create Quiz</span>
          </button>

          <button
            className={`teacher-nav-item ${currentTab === "active" ? "active" : ""}`}
            onClick={() => navigateTo("/teacher")}
          >
            <span className="teacher-nav-icon">⚡</span>
            <span>Active Quizzes</span>
          </button>

          {activeQuizId && (
            <div className="teacher-nav-subgroup">
              <span className="subgroup-label">CURRENT QUIZ ({activeQuizId})</span>
              <button
                className={`teacher-nav-subitem ${currentTab === "details" ? "active" : ""}`}
                onClick={() => navigateTo(`/teacher/quiz/${activeQuizId}`)}
              >
                <span>ℹ️ Details</span>
              </button>
              <button
                className={`teacher-nav-subitem ${currentTab === "leaderboard" ? "active" : ""}`}
                onClick={() => navigateTo(`/teacher/quiz/${activeQuizId}/leaderboard`)}
              >
                <span>🏆 Leaderboard</span>
              </button>
              <button
                className={`teacher-nav-subitem ${currentTab === "share" ? "active" : ""}`}
                onClick={() => navigateTo(`/teacher/quiz/${activeQuizId}/share`)}
              >
                <span>🔗 Share Link</span>
              </button>
            </div>
          )}

          <div className="teacher-nav-divider" />

          <button
            className="teacher-nav-item teacher-nav-student-link"
            onClick={() => navigateTo("/")}
            title="Open Student Interface"
          >
            <span className="teacher-nav-icon">🎓</span>
            <span>Student Platform</span>
          </button>

          <button
            className="teacher-nav-item teacher-nav-logout"
            onClick={handleLogout}
            id="teacher-logout-btn"
          >
            <span className="teacher-nav-icon">🚪</span>
            <span>Sign Out</span>
          </button>
        </nav>

        <div className="teacher-sidebar-footer">
          <div className="teacher-profile-pill">
            <span className="profile-dot online" />
            <div className="profile-text">
              <span className="profile-role">Instructor</span>
              <span className="profile-email">teacher@netquiz.edu</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Panel */}
      <div className="teacher-main-panel">
        <header className="teacher-topbar">
          <div className="topbar-left">
            <span className="topbar-crumb">Faculty Control Center</span>
            <span className="topbar-sep">/</span>
            <span className="topbar-current">
              {currentTab === "create"
                ? "Quiz Builder"
                : currentTab === "leaderboard"
                ? "Quiz Leaderboard"
                : currentTab === "details"
                ? "Quiz Overview"
                : currentTab === "share"
                ? "Share Quiz"
                : "Dashboard Home"}
            </span>
          </div>

          <div className="topbar-right">
            <button
              className="btn-topbar-create"
              onClick={() => navigateTo("/teacher/create")}
            >
              <span>+ New Quiz</span>
            </button>
            <button
              className="btn-topbar-student"
              onClick={() => window.open("/", "_blank")}
              title="Open Student Portal in new tab"
            >
              <span>Student View ↗</span>
            </button>
          </div>
        </header>

        <main className="teacher-content-area">{children}</main>
      </div>
    </div>
  );
}
