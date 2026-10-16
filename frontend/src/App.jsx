import React, { useState, useEffect, useCallback } from "react";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { Home } from "./pages/Home";
import { getHealth, getServerStatus, getQuizInfo } from "./services/api";
import "./App.css";

function App() {
  const [serverStatus, setServerStatus] = useState(null);
  const [quizInfo, setQuizInfo] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorNotice, setErrorNotice] = useState(null);

  const fetchPlatformData = useCallback(async () => {
    setIsLoading(true);
    setErrorNotice(null);

    try {
      // 1. Query FastAPI Health and TCP Server Status concurrently
      const [healthRes, statusRes, infoRes] = await Promise.all([
        getHealth(),
        getServerStatus(),
        getQuizInfo()
      ]);

      if (healthRes.ok && statusRes.ok) {
        setIsOnline(statusRes.data.running ?? true);
        setServerStatus(statusRes.data);
      } else {
        setIsOnline(false);
        setErrorNotice(statusRes.error || healthRes.error || "Cannot reach NetQuiz backend.");
      }

      if (infoRes.ok) {
        setQuizInfo(infoRes.data);
      }
    } catch (err) {
      setIsOnline(false);
      setErrorNotice(err.message || "Failed to load platform data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlatformData();
    // Optional gentle poll every 10 seconds to keep live active client counts in sync
    const interval = setInterval(fetchPlatformData, 10000);
    return () => clearInterval(interval);
  }, [fetchPlatformData]);

  return (
    <div className="netquiz-app">
      {/* Reusable Header Navbar */}
      <Navbar
        isOnline={isOnline}
        isLoading={isLoading}
        onRefresh={fetchPlatformData}
      />

      {/* Global Offline Warning Banner if backend is not reachable */}
      {!isOnline && !isLoading && (
        <div className="offline-banner">
          <div className="offline-banner-content">
            <span className="banner-icon">⚠️</span>
            <span>
              <strong>TCP Socket Server Offline:</strong> FastAPI is unable to reach port 5000. 
              Start the backend via <code>uvicorn backend.main:app --port 8000</code>.
            </span>
            <button className="btn-banner-retry" onClick={fetchPlatformData}>
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area: Landing Page */}
      <main className="main-viewport">
        <Home
          serverStatus={serverStatus}
          quizInfo={quizInfo}
          isOnline={isOnline}
          isLoading={isLoading}
          onRefresh={fetchPlatformData}
        />
      </main>

      {/* Reusable Footer */}
      <Footer isOnline={isOnline} />
    </div>
  );
}

export default App;
