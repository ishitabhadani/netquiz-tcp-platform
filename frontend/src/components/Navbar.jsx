import React from "react";
import { StatusBadge } from "./StatusBadge";

export function Navbar({ isOnline, isLoading, onRefresh }) {
  return (
    <header className="navbar-container">
      <div className="navbar-content">
        <div className="navbar-brand">
          <div className="brand-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
              <line x1="6" y1="6" x2="6.01" y2="6"></line>
              <line x1="6" y1="18" x2="6.01" y2="18"></line>
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

        <div className="navbar-actions">
          <div className="endpoint-pill">
            <span className="endpoint-proto">IPv4 TCP</span>
            <span className="endpoint-addr">127.0.0.1:5000</span>
          </div>

          <StatusBadge isOnline={isOnline} isLoading={isLoading} />

          <button 
            className="btn-refresh" 
            onClick={onRefresh} 
            disabled={isLoading}
            title="Refresh Server Connection Status"
          >
            <svg className={isLoading ? "spin" : ""} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>{isLoading ? "Checking..." : "Refresh"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
