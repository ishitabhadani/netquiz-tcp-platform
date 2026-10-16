import React from "react";

export function NetworkArchitecture({ isOnline = true }) {
  return (
    <section className="architecture-container">
      <div className="section-header-block">
        <span className="section-kicker">Computer Networks Demonstration</span>
        <h2 className="section-heading">Multi-User TCP Client-Server Architecture</h2>
        <p className="section-subheading">
          A central multithreaded Python TCP socket server accepts concurrent student connections, 
          managing independent quiz states across isolated execution threads.
        </p>
      </div>

      <div className="diagram-canvas">
        {/* Top: Central Server Node */}
        <div className="diagram-server-node">
          <div className="server-node-inner">
            <div className="server-header">
              <span className="server-icon">🖥️</span>
              <div>
                <div className="server-title">NETQUIZ TCP SERVER</div>
                <div className="server-coords">127.0.0.1 : 5000</div>
              </div>
              <span className={`server-pill ${isOnline ? "pill-online" : "pill-offline"}`}>
                {isOnline ? "ACTIVE LISTENER" : "OFFLINE"}
              </span>
            </div>
            <div className="server-tags">
              <span className="tech-tag">AF_INET (IPv4)</span>
              <span className="tech-tag">SOCK_STREAM (TCP)</span>
              <span className="tech-tag">SO_REUSEADDR</span>
              <span className="tech-tag">Multithreading</span>
            </div>
          </div>
        </div>

        {/* Middle: Trunk Cable & Stream Protocol */}
        <div className="diagram-trunk">
          <div className="trunk-line"></div>
          <div className="protocol-badge">
            <span className="protocol-pulse"></span>
            <span>Reliable TCP Byte Stream (Newline-Delimited JSON Lines)</span>
          </div>
          <div className="trunk-split-lines">
            <div className="branch-line branch-left"></div>
            <div className="branch-line branch-mid"></div>
            <div className="branch-line branch-right"></div>
          </div>
        </div>

        {/* Bottom: Concurrent Student Client Threads */}
        <div className="diagram-clients-grid">
          <div className="client-node">
            <div className="client-node-header">
              <span className="client-icon">👤</span>
              <div>
                <div className="client-name">Student A (Ishita)</div>
                <div className="client-thread">Thread-Client-857735</div>
              </div>
            </div>
            <div className="client-state">
              <span>State: <strong>Independent</strong></span>
              <span>Score: <strong>Evaluated Server-Side</strong></span>
            </div>
          </div>

          <div className="client-node client-node-highlight">
            <div className="client-node-header">
              <span className="client-icon">👤</span>
              <div>
                <div className="client-name">Student B (Aarav)</div>
                <div className="client-thread">Thread-Client-233c9b</div>
              </div>
            </div>
            <div className="client-state">
              <span>State: <strong>Independent</strong></span>
              <span>Score: <strong>Evaluated Server-Side</strong></span>
            </div>
          </div>

          <div className="client-node">
            <div className="client-node-header">
              <span className="client-icon">👤</span>
              <div>
                <div className="client-name">Student C (Riya)</div>
                <div className="client-thread">Thread-Client-bd5173</div>
              </div>
            </div>
            <div className="client-state">
              <span>State: <strong>Independent</strong></span>
              <span>Score: <strong>Evaluated Server-Side</strong></span>
            </div>
          </div>
        </div>
      </div>

      <div className="bridge-notice-card">
        <div className="bridge-icon">ℹ️</div>
        <div className="bridge-text">
          <strong>Academic Viva Note:</strong> Browsers communicate with <code>FastAPI (Port 8000)</code> via HTTP REST to fetch live metrics and leaderboards. 
          The actual student quiz messaging executes over <code>Python TCP Sockets (Port 5000)</code> using connection-oriented byte streams.
        </div>
      </div>
    </section>
  );
}
