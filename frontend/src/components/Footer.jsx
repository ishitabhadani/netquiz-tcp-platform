import React from "react";

export function Footer({ isOnline = true }) {
  return (
    <footer className="footer-container">
      <div className="footer-top-row">
        <div className="footer-pills">
          <span className="footer-pill">
            <span className="pill-dot"></span>
            TCP Port: <strong>5000</strong>
          </span>
          <span className="footer-pill">
            <span className="pill-dot"></span>
            FastAPI Bridge: <strong>8000</strong>
          </span>
          <span className="footer-pill">
            <span className="pill-dot"></span>
            Address Family: <strong>IPv4 (AF_INET)</strong>
          </span>
          <span className="footer-pill">
            <span className="pill-dot"></span>
            Socket Type: <strong>SOCK_STREAM</strong>
          </span>
          <span className={`footer-pill ${isOnline ? "pill-online-text" : "pill-offline-text"}`}>
            Status: <strong>{isOnline ? "Connected" : "Disconnected"}</strong>
          </span>
        </div>
      </div>

      <div className="footer-bottom-row">
        <p className="footer-main-text">
          NETQUIZ &bull; Design and Implementation of a Multi-User Quiz Platform Using TCP Client-Server Architecture
        </p>
        <p className="footer-sub-text">
          B.Tech Computer Networks Mini-Project &bull; Demonstrating Sockets, Concurrency, Message Framing & Reliable Transport
        </p>
      </div>
    </footer>
  );
}
