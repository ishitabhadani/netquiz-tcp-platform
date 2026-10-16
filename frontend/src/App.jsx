import { useState, useEffect } from "react";
import { checkBackendHealth } from "./services/api";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [backendInfo, setBackendInfo] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const performHealthCheck = async () => {
    setIsRefreshing(true);
    const result = await checkBackendHealth();
    if (result.ok) {
      setBackendStatus("online");
      setBackendInfo(result.data);
    } else {
      setBackendStatus("offline");
      setBackendInfo(null);
    }
    setLastChecked(new Date().toLocaleTimeString());
    setIsRefreshing(false);
  };

  useEffect(() => {
    performHealthCheck();
  }, []);

  return (
    <div className="app-container">
      {/* Header Section */}
      <header className="header-banner">
        <span className="badge-tag">Computer Networks Mini-Project</span>
        <h1 className="title-main">NETQUIZ</h1>
        <p className="subtitle-main">
          Multi-User TCP Quiz Platform
        </p>
        <p style={{ marginTop: "0.4rem", fontSize: "0.95rem", color: "#64748b" }}>
          TCP-powered Computer Networks Quiz Platform
        </p>
      </header>

      {/* Backend API Health Status Card */}
      <section className="status-card">
        <div className="card-header-flex">
          <div className="card-title">
            <span>FastAPI Application Layer</span>
          </div>
          <div className={`status-indicator ${backendStatus === "online" ? "online" : "offline"}`}>
            <span className={`status-dot ${backendStatus === "online" ? "pulse" : ""}`}></span>
            <span>{backendStatus === "online" ? "ONLINE" : "OFFLINE"}</span>
          </div>
        </div>

        <div className="info-grid">
          <div className="info-item">
            <div className="info-label">API Endpoint</div>
            <div className="info-value">http://127.0.0.1:8000/api/health</div>
          </div>
          <div className="info-item">
            <div className="info-label">Service Name</div>
            <div className="info-value">
              {backendInfo ? backendInfo.service : "Unknown / Unreachable"}
            </div>
          </div>
          <div className="info-item">
            <div className="info-label">HTTP Health Status</div>
            <div className="info-value">
              {backendInfo ? backendInfo.status.toUpperCase() : "DISCONNECTED"}
            </div>
          </div>
          <div className="info-item">
            <div className="info-label">Last Checked</div>
            <div className="info-value">{lastChecked || "Checking..."}</div>
          </div>
        </div>

        <div className="action-bar">
          <button
            className="btn-secondary"
            onClick={performHealthCheck}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Checking Status..." : "Refresh Backend Status"}
          </button>
        </div>
      </section>

      {/* Architecture Overview Card */}
      <section className="architecture-preview">
        <div className="card-header-flex">
          <div className="card-title">
            <span>System Layer Architecture</span>
          </div>
          <span style={{ fontSize: "0.8125rem", color: "#64748b", fontWeight: 500 }}>
            Academic Design
          </span>
        </div>

        <div className="arch-steps">
          <div className="arch-node active-stage">
            <span className="arch-node-badge">LAYER 1</span>
            <div className="arch-node-info">
              <h4>React Frontend (Vite)</h4>
              <p>User interface running in the browser on port 5173</p>
            </div>
            <span className="stage-badge">Stage 1 Active</span>
          </div>

          <div className="arch-node active-stage">
            <span className="arch-node-badge">LAYER 2</span>
            <div className="arch-node-info">
              <h4>FastAPI Application Bridge</h4>
              <p>HTTP REST bridge on port 8000 coordinating UI state</p>
            </div>
            <span className="stage-badge">Stage 1 Active</span>
          </div>

          <div className="arch-node">
            <span className="arch-node-badge">LAYER 3</span>
            <div className="arch-node-info">
              <h4>Quiz Manager & State Engine</h4>
              <p>Session management, score evaluation, and question bank</p>
            </div>
            <span className="stage-badge" style={{ color: "#94a3b8" }}>Stage 3</span>
          </div>

          <div className="arch-node">
            <span className="arch-node-badge">LAYER 4</span>
            <div className="arch-node-info">
              <h4>Python TCP Socket Server</h4>
              <p>AF_INET / SOCK_STREAM socket layer on port 5000 with multithreading</p>
            </div>
            <span className="stage-badge" style={{ color: "#94a3b8" }}>Stage 2</span>
          </div>

          <div className="arch-node">
            <span className="arch-node-badge">LAYER 5</span>
            <div className="arch-node-info">
              <h4>Concurrent TCP Clients</h4>
              <p>Independent student threads communicating via framed JSON messages</p>
            </div>
            <span className="stage-badge" style={{ color: "#94a3b8" }}>Stage 2 / 7</span>
          </div>
        </div>
      </section>

      {/* Academic Footer */}
      <footer className="academic-footer">
        <p>
          B.Tech Computer Networks Mini-Project &bull; NetQuiz Platform
        </p>
        <p style={{ marginTop: "0.25rem", color: "#94a3b8" }}>
          Demonstrating TCP Socket Programming, IPv4, Concurrency & Client-Server Architecture
        </p>
      </footer>
    </div>
  );
}

export default App;
