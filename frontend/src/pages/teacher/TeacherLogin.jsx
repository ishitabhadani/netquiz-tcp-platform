import React, { useState } from "react";
import { teacherLogin, setTeacherToken } from "../../services/api";
import { navigateTo } from "../../services/router";

export function TeacherLogin() {
  const [email, setEmail] = useState("teacher@netquiz.edu");
  const [password, setPassword] = useState("teacher123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password.trim()) {
      setError("Please provide both email and password.");
      return;
    }

    setLoading(true);
    const res = await teacherLogin(email.trim(), password.trim());
    setLoading(false);

    const token = res.data?.token || res.data?.access_token;
    if (res.ok && token) {
      setTeacherToken(token);
      navigateTo("/teacher");
    } else {
      setError(res.error || "Invalid credentials. Please verify your email and password.");
    }
  };

  const handleFillDemo = () => {
    setEmail("teacher@netquiz.edu");
    setPassword("teacher123");
    setError(null);
  };

  return (
    <div className="teacher-login-container">
      <div className="teacher-login-card">
        {/* Brand Header */}
        <div className="teacher-login-header">
          <div className="brand-logo-icon">
            <svg
              width="24"
              height="24"
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
          <div className="teacher-login-title-wrap">
            <span className="teacher-login-badge">FACULTY ACCESS</span>
            <h1 className="teacher-login-title">NetQuiz Teacher Portal</h1>
            <p className="teacher-login-subtitle">
              Manage custom quizzes, publish student links, and supervise live TCP sessions.
            </p>
          </div>
        </div>

        {error && (
          <div className="teacher-login-error">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="teacher-login-form">
          <div className="input-group">
            <label className="input-label" htmlFor="teacher-email">
              TEACHER EMAIL
            </label>
            <div className="input-field-wrap">
              <span className="input-prefix-icon">✉️</span>
              <input
                id="teacher-email"
                type="email"
                className="input-text"
                placeholder="teacher@netquiz.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label" htmlFor="teacher-password">
              PASSWORD
            </label>
            <div className="input-field-wrap">
              <span className="input-prefix-icon">🔒</span>
              <input
                id="teacher-password"
                type="password"
                className="input-text"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn-teacher-primary"
            disabled={loading}
            id="teacher-login-btn"
          >
            {loading ? (
              <>
                <span className="btn-spinner" /> Signing in…
              </>
            ) : (
              <>
                <span>Sign In to Dashboard</span>
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </>
            )}
          </button>
        </form>

        {/* Demo Quick Fill Helper */}
        <div className="teacher-demo-box">
          <div className="demo-box-header">
            <span className="demo-badge">DEMO / EVALUATION CREDENTIALS</span>
          </div>
          <div className="demo-box-credentials">
            <div>
              <strong>Email:</strong> <code>teacher@netquiz.edu</code>
            </div>
            <div>
              <strong>Password:</strong> <code>teacher123</code>
            </div>
          </div>
          <button
            type="button"
            className="btn-demo-fill"
            onClick={handleFillDemo}
            title="Auto-fill demo credentials"
          >
            ⚡ Auto-Fill Demo Credentials
          </button>
        </div>

        {/* Footer Nav */}
        <div className="teacher-login-footer">
          <button
            type="button"
            className="btn-link-student"
            onClick={() => navigateTo("/")}
          >
            ← Return to Student Quiz Platform
          </button>
        </div>
      </div>
    </div>
  );
}
