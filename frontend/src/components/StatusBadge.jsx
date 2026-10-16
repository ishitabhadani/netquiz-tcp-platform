import React from "react";

export function StatusBadge({ isOnline, isLoading = false }) {
  if (isLoading) {
    return (
      <div className="status-badge status-loading">
        <span className="status-dot dot-loading"></span>
        <span className="status-text">CONNECTING...</span>
      </div>
    );
  }

  return (
    <div className={`status-badge ${isOnline ? "status-online" : "status-offline"}`}>
      <span className={`status-dot ${isOnline ? "dot-online" : "dot-offline"}`}></span>
      <span className="status-text">{isOnline ? "TCP ● ONLINE" : "TCP ● OFFLINE"}</span>
    </div>
  );
}
