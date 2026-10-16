import React, { useState, useEffect, useCallback } from "react";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { Home } from "./pages/Home";
import { Quiz } from "./pages/Quiz";
import { Results } from "./pages/Results";
import { Leaderboard } from "./pages/Leaderboard";
import { TeacherLogin } from "./pages/teacher/TeacherLogin";
import { TeacherDashboard } from "./pages/teacher/TeacherDashboard";
import { TeacherCreateQuiz } from "./pages/teacher/TeacherCreateQuiz";
import { TeacherQuizDetails } from "./pages/teacher/TeacherQuizDetails";
import { TeacherQuizLeaderboard } from "./pages/teacher/TeacherQuizLeaderboard";
import { TeacherShareQuiz } from "./pages/teacher/TeacherShareQuiz";
import { StudentCustomQuiz } from "./pages/StudentCustomQuiz";
import { parseRoute, subscribeToNavigation, navigateTo } from "./services/router";
import { getHealth, getServerStatus, getQuizInfo } from "./services/api";
import "./App.css";

/**
 * NetQuiz App — Root component with dual-role routing:
 *  1. Student generic TCP quiz & scoped custom quiz (/join/:quizId)
 *  2. Teacher portal & management dashboard (/teacher/*)
 */
function App() {
  // ── URL Route state ────────────────────────────────────────────────────────
  const [currentRoute, setCurrentRoute] = useState(() => parseRoute());

  useEffect(() => {
    const unsubscribe = subscribeToNavigation(() => {
      setCurrentRoute(parseRoute());
    });
    return unsubscribe;
  }, []);

  // ── Generic Student Page routing ───────────────────────────────────────────
  const [view, setView] = useState("home");
  const [session, setSession] = useState(null);   // { connectionId, studentName, totalQuestions }
  const [summary, setSummary] = useState(null);   // final quiz result from server

  // ── Infrastructure state ───────────────────────────────────────────────────
  const [serverStatus, setServerStatus] = useState(null);
  const [quizInfo, setQuizInfo] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchPlatformData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [healthRes, statusRes, infoRes] = await Promise.all([
        getHealth(),
        getServerStatus(),
        getQuizInfo(),
      ]);

      if (healthRes.ok && statusRes.ok) {
        setIsOnline(statusRes.data.running ?? true);
        setServerStatus(statusRes.data);
      } else {
        setIsOnline(false);
      }

      if (infoRes.ok) {
        setQuizInfo(infoRes.data);
      }
    } catch {
      setIsOnline(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlatformData();
    const interval = setInterval(fetchPlatformData, 10000);
    return () => clearInterval(interval);
  }, [fetchPlatformData]);

  // ── Navigation handlers ────────────────────────────────────────────────────
  const [sessionLostNotice, setSessionLostNotice] = useState(false);

  useEffect(() => {
    // Check if an active quiz session was interrupted by a browser refresh
    const wasActive = sessionStorage.getItem("netquiz_active_session");
    if (wasActive) {
      sessionStorage.removeItem("netquiz_active_session");
      setSessionLostNotice(true);
    }
  }, []);

  /** Called by Home when the student successfully joins the generic quiz */
  const handleJoinSuccess = (newSession) => {
    sessionStorage.setItem("netquiz_active_session", "true");
    setSessionLostNotice(false);
    setSession(newSession);
    setView("quiz");
    window.scrollTo(0, 0);
  };

  /** Called by Quiz when the student completes all questions */
  const handleQuizComplete = (quizSummary) => {
    sessionStorage.removeItem("netquiz_active_session");
    setSummary(quizSummary);
    setView("results");
    window.scrollTo(0, 0);
    fetchPlatformData();
  };

  /** Navigate to generic leaderboard */
  const handleViewLeaderboard = () => {
    setView("leaderboard");
    window.scrollTo(0, 0);
  };

  /** Reset to home for retry */
  const handleRetry = () => {
    sessionStorage.removeItem("netquiz_active_session");
    setSession(null);
    setSummary(null);
    setView("home");
    navigateTo("/");
    window.scrollTo(0, 0);
    fetchPlatformData();
  };

  /** Navigate back to home from any sub-page */
  const handleBackToHome = () => {
    sessionStorage.removeItem("netquiz_active_session");
    setSession(null);
    setView("home");
    navigateTo("/");
    window.scrollTo(0, 0);
    fetchPlatformData();
  };

  // ── ROUTE DISPATCH ─────────────────────────────────────────────────────────

  // 1. Teacher Routes
  if (currentRoute.name === "teacher-login") {
    return <TeacherLogin />;
  }

  if (currentRoute.name === "teacher-create") {
    return <TeacherCreateQuiz />;
  }

  if (currentRoute.name === "teacher-edit") {
    return <TeacherCreateQuiz quizId={currentRoute.params.quizId} />;
  }

  if (currentRoute.name === "teacher-leaderboard") {
    return <TeacherQuizLeaderboard quizId={currentRoute.params.quizId} />;
  }

  if (currentRoute.name === "teacher-share") {
    return <TeacherShareQuiz quizId={currentRoute.params.quizId} />;
  }

  if (currentRoute.name === "teacher-quiz-details") {
    return <TeacherQuizDetails quizId={currentRoute.params.quizId} />;
  }

  if (currentRoute.name === "teacher-dashboard") {
    return <TeacherDashboard />;
  }

  // 2. Student Custom Quiz Route (/join/:quizId or /quiz/:quizId)
  if (currentRoute.name === "student-custom-quiz") {
    return <StudentCustomQuiz quizId={currentRoute.params.quizId} />;
  }

  // 3. Default Generic Student Platform
  return (
    <div className="netquiz-app">
      <Navbar
        isOnline={isOnline}
        isLoading={isLoading}
        onRefresh={fetchPlatformData}
        currentView={view}
        onNavHome={handleBackToHome}
        onNavLeaderboard={handleViewLeaderboard}
        serverStatus={serverStatus}
      />

      {/* Session Expired / Interrupted Notice Banner */}
      {sessionLostNotice && view === "home" && (
        <div className="session-lost-banner">
          <div className="session-lost-content">
            <span className="banner-icon">ℹ️</span>
            <span>Your quiz session is no longer active. Please join again.</span>
            <button
              className="btn-banner-dismiss"
              onClick={() => setSessionLostNotice(false)}
              aria-label="Dismiss notice"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Offline banner — shown only on home page if server is unreachable */}
      {!isOnline && !isLoading && view === "home" && (
        <div className="offline-banner">
          <div className="offline-banner-content">
            <span className="banner-icon">⚠️</span>
            <span>
              <strong>TCP Socket Server Offline:</strong> FastAPI is unable to
              reach the internal TCP socket server. In local development, start the backend via{" "}
              <code>uvicorn backend.main:app --port 8000</code>.
            </span>
            <button className="btn-banner-retry" onClick={fetchPlatformData}>
              Retry Connection
            </button>
          </div>
        </div>
      )}

      <main className="main-viewport">
        {view === "home" && (
          <Home
            serverStatus={serverStatus}
            quizInfo={quizInfo}
            isOnline={isOnline}
            isLoading={isLoading}
            onRefresh={fetchPlatformData}
            onJoinSuccess={handleJoinSuccess}
          />
        )}

        {view === "quiz" && session && (
          <Quiz
            session={session}
            onQuizComplete={handleQuizComplete}
            onBackToHome={handleBackToHome}
          />
        )}

        {view === "results" && summary && (
          <Results
            summary={summary}
            onViewLeaderboard={handleViewLeaderboard}
            onRetry={handleRetry}
          />
        )}

        {view === "leaderboard" && (
          <Leaderboard
            onBack={handleBackToHome}
            currentStudentName={session?.studentName || summary?.student_name}
          />
        )}
      </main>

      <Footer isOnline={isOnline} serverStatus={serverStatus} />
    </div>
  );
}

export default App;
