import React, { useState } from "react";
import { NetworkStatCards } from "../components/NetworkStatCards";
import { NetworkArchitecture } from "../components/NetworkArchitecture";
import { joinQuiz } from "../services/api";

/**
 * Home Page — Landing screen with join form, network stats, and architecture diagram.
 *
 * On successful join: calls onJoinSuccess(session) to navigate to the Quiz page.
 * Session contains: { connectionId, studentName, totalQuestions }
 */
export function Home({ serverStatus, quizInfo, isOnline, isLoading, onRefresh, onJoinSuccess }) {
  const [studentName, setStudentName] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinMessage, setJoinMessage] = useState(null);

  const handleJoinClick = async (e) => {
    e.preventDefault();
    const trimmed = studentName.trim();

    if (!trimmed) {
      setJoinMessage({ type: "error", text: "Please enter your name to join the quiz." });
      return;
    }
    if (!isOnline) {
      setJoinMessage({
        type: "error",
        text: "Cannot join: The Python TCP Server is offline. Please start the backend.",
      });
      return;
    }

    setJoining(true);
    setJoinMessage(null);

    // POST /api/quiz/join → FastAPI → QuizManager.start_quiz()
    const res = await joinQuiz(trimmed);
    setJoining(false);

    if (!res.ok) {
      setJoinMessage({ type: "error", text: res.error || "Failed to join quiz. Try again." });
      return;
    }

    const { connection_id, total_questions } = res.data;
    // Navigate to the quiz page
    onJoinSuccess({
      connectionId: connection_id,
      studentName: trimmed,
      totalQuestions: total_questions,
    });
  };

  return (
    <div className="home-container">
      {/* Hero Header */}
      <section className="hero-section">
        <div className="hero-kicker-badge">
          <span className="kicker-icon">📡</span>
          <span>Computer Networks Capstone Mini-Project</span>
        </div>

        <h1 className="hero-title">
          NET<span className="hero-highlight">QUIZ</span>
        </h1>
        <p className="hero-subtitle">Multi-User TCP Quiz Platform</p>
        <p className="hero-description">
          Test your Computer Networks knowledge over a genuine TCP client-server
          architecture. Multiple students connect concurrently over IPv4,
          exchanging framed JSON byte streams evaluated strictly server-side.
        </p>

        {/* Primary Student Join Card */}
        <div className="join-card">
          <div className="join-card-header">
            <div className="join-card-title-group">
              <span className="join-icon">🚀</span>
              <span className="join-card-title">Join Live Quiz Session</span>
            </div>
            <div
              className={`server-status-pill ${
                isOnline ? "pill-online" : "pill-offline"
              }`}
            >
              <span className="status-dot" />
              <span>{isOnline ? "TCP SERVER ONLINE" : "TCP SERVER OFFLINE"}</span>
            </div>
          </div>

          <form className="join-form" onSubmit={handleJoinClick}>
            <div className="input-group">
              <label htmlFor="student-name-input" className="input-label">
                STUDENT IDENTIFIER
              </label>
              <div className="input-field-wrap">
                <span className="input-prefix-icon">👤</span>
                <input
                  id="student-name-input"
                  type="text"
                  className="input-text"
                  placeholder="Enter student name (e.g. Ishita)"
                  value={studentName}
                  onChange={(e) => {
                    setStudentName(e.target.value);
                    if (joinMessage) setJoinMessage(null);
                  }}
                  disabled={isLoading || joining}
                  maxLength={50}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary-join"
              disabled={isLoading || !isOnline || joining}
              id="join-quiz-btn"
            >
              {joining ? (
                <>
                  <span className="btn-spinner" /> Connecting to server…
                </>
              ) : (
                <>
                  <span>CONNECT &amp; JOIN QUIZ</span>
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

          {joinMessage && (
            <div
              className={`join-alert ${
                joinMessage.type === "success" ? "alert-success" : "alert-error"
              }`}
            >
              <span className="alert-icon">
                {joinMessage.type === "success" ? "✅" : "⚠️"}
              </span>
              <span className="alert-text">{joinMessage.text}</span>
            </div>
          )}

          <div className="join-card-footer">
            <div className="footer-spec-item">
              <span className="spec-label">Target Protocol</span>
              <span className="spec-val">TCP (127.0.0.1:5000)</span>
            </div>
            <div className="footer-spec-item">
              <span className="spec-label">Session Scope</span>
              <span className="spec-val">Independent Client Thread</span>
            </div>
            <div className="footer-spec-item">
              <span className="spec-label">Evaluation Mode</span>
              <span className="spec-val">Server-Side Source of Truth</span>
            </div>
          </div>
        </div>
      </section>

      {/* Network Stat Cards Grid */}
      <section className="section-block">
        <div className="section-header-compact">
          <h3 className="section-sub-title">Live Networking &amp; Quiz Parameters</h3>
          <span className="section-tag">Queried from FastAPI Port 8000</span>
        </div>
        <NetworkStatCards serverStatus={serverStatus} quizInfo={quizInfo} />
      </section>

      {/* Visual Network Architecture Diagram */}
      <NetworkArchitecture isOnline={isOnline} />

      {/* Live Server Terminal Status Card */}
      <section className="section-block">
        <div className="terminal-card">
          <div className="terminal-header">
            <div className="terminal-dots">
              <span className="t-dot dot-red" />
              <span className="t-dot dot-yellow" />
              <span className="t-dot dot-green" />
            </div>
            <span className="terminal-title">
              TCP SOCKET SERVER RUNTIME &bull; 127.0.0.1:5000
            </span>
            <span className="terminal-badge">LIVE METRICS</span>
          </div>
          <div className="terminal-body">
            <div className="terminal-row">
              <span className="t-key">SOCKET_DESCRIPTOR</span>
              <span className="t-val">socket.socket(AF_INET, SOCK_STREAM)</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">LISTEN_INTERFACE</span>
              <span className="t-val">127.0.0.1:5000 (SO_REUSEADDR Active)</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">STREAM_FRAMING</span>
              <span className="t-val">Newline-Delimited JSON (JSON Lines '\n')</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">ACTIVE_CLIENT_SOCKETS</span>
              <span className="t-val t-highlight">
                {serverStatus?.active_clients ?? 0} Concurrent Clients
              </span>
            </div>
            <div className="terminal-row">
              <span className="t-key">TOTAL_CONNECTIONS_ACCEPTED</span>
              <span className="t-val">{serverStatus?.total_connections ?? 0}</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">QUESTIONS_DELIVERED</span>
              <span className="t-val">{serverStatus?.questions_sent ?? 0}</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">CANDIDATE_ANSWERS_EVALUATED</span>
              <span className="t-val">{serverStatus?.answers_received ?? 0}</span>
            </div>
            <div className="terminal-row">
              <span className="t-key">COMPLETED_QUIZ_SESSIONS</span>
              <span className="t-val">{serverStatus?.completed_quizzes ?? 0}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
