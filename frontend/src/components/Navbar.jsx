import React from "react";
import { StatusBadge } from "./StatusBadge";

export function Navbar({ isOnline, isLoading, onRefresh, currentView, onNavHome, onNavLeaderboard, serverStatus }) {
  const tcpAddr = serverStatus?.host && serverStatus?.port
    ? `${serverStatus.host}:${serverStatus.port}`
    : "127.0.0.1:5000";

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand */}
        <div className="navbar-brand" onClick={onNavHome} style={{ cursor: "pointer" }}>
          <div className="brand-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
          </div>
          <div>
            <div className="brand-title-wrap">
              <span className="brand-title">NETQUIZ</span>
              <span className="brand-badge">TCP SOCKETS</span>
            </div>
            <p className="brand-subtitle">Multi-User Computer Networks Platform</p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="navbar-nav">
          <button
            className={`nav-link ${currentView === "home" ? "nav-link-active" : ""}`}
            onClick={onNavHome}
            id="nav-home-btn"
          >
            Home
          </button>
          <button
            className={`nav-link ${currentView === "leaderboard" ? "nav-link-active" : ""}`}
            onClick={onNavLeaderboard}
            id="nav-leaderboard-btn"
          >
            🏆 Leaderboard
          </button>
          <button
            className="nav-link nav-link-teacher"
            onClick={() => {
              window.history.pushState({}, "", "/teacher");
              window.dispatchEvent(new PopStateEvent("popstate"));
            }}
            id="nav-teacher-portal-btn"
            title="Faculty & Teacher Portal"
          >
            👨‍🏫 Teacher Portal
          </button>
        </nav>

        {/* Actions */}
        <div className="navbar-actions">
          <div className="endpoint-pill">
            <span className="endpoint-proto">IPv4 TCP</span>
            <span className="endpoint-addr">{tcpAddr}</span>
          </div>

          <StatusBadge isOnline={isOnline} isLoading={isLoading} />

          <button
            className="btn-refresh"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh Server Connection Status"
            id="nav-refresh-btn"
          >
            <svg
              className={isLoading ? "spin" : ""}
              width="15" height="15" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round"
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span>{isLoading ? "Checking..." : "Refresh"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
