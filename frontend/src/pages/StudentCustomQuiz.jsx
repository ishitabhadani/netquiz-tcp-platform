import React, { useState, useEffect, useCallback, useRef } from "react";
import { Navbar } from "../components/Navbar";
import { Footer } from "../components/Footer";
import {
  getHealth,
  getServerStatus,
  getPublicQuiz,
  joinCustomQuiz,
  fetchCustomQuestion,
  submitCustomAnswer,
  fetchCustomSummary,
  fetchCustomLeaderboard,
  formatApiError,
} from "../services/api";
import { navigateTo } from "../services/router";

const OPTION_LABELS = ["A", "B", "C", "D"];

const GRADE_MAP = [
  { min: 90, label: "Distinction", color: "#22c55e", icon: "🏆" },
  { min: 70, label: "First Class", color: "#3b82f6", icon: "🥇" },
  { min: 50, label: "Pass", color: "#f59e0b", icon: "📘" },
  { min: 0, label: "Fail", color: "#ef4444", icon: "📉" },
];

function getGrade(percentage) {
  return GRADE_MAP.find((g) => percentage >= g.min) || GRADE_MAP[GRADE_MAP.length - 1];
}

export function StudentCustomQuiz({ quizId }) {
  const sessionKey = `netquiz_custom_session_${quizId}`;

  // Phase: 'loading' | 'join' | 'question' | 'feedback' | 'results' | 'leaderboard' | 'not_found' | 'ended'
  const [phase, setPhase] = useState("loading");
  const [quiz, setQuiz] = useState(null);
  const [error, setError] = useState(null);

  // System & Infrastructure status
  const [serverStatus, setServerStatus] = useState(null);
  const [isOnline, setIsOnline] = useState(true);

  // Join form state
  const [studentName, setStudentName] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState(null);

  // Active session
  const [connectionId, setConnectionId] = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(0);

  // Question state
  const [question, setQuestion] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [selectedOption, setSelectedOption] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [answerResult, setAnswerResult] = useState(null);
  const [currentScore, setCurrentScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(30);
  const timerRef = useRef(null);

  // Results state
  const [summary, setSummary] = useState(null);

  // Scoped Leaderboard state
  const [leaderboard, setLeaderboard] = useState([]);
  const [lbLoading, setLbLoading] = useState(false);
  const [lbRefreshed, setLbRefreshed] = useState(null);

  // ── Fetch Server Status & Public Quiz Meta ──────────────────────────────────
  const fetchInitialData = useCallback(async () => {
    setPhase("loading");
    setError(null);
    setSubmitError(null);

    try {
      const [healthRes, statusRes, quizRes] = await Promise.all([
        getHealth(),
        getServerStatus(),
        getPublicQuiz(quizId),
      ]);

      if (healthRes.ok && statusRes.ok) {
        setIsOnline(statusRes.data?.running ?? true);
        setServerStatus(statusRes.data);
      }

      if (!quizRes.ok) {
        setError(formatApiError(quizRes.error) || "Quiz not found or currently unavailable.");
        setPhase("not_found");
        return;
      }

      const qData = quizRes.data;
      setQuiz(qData);
      const totalQ = qData.question_count || qData.questions?.length || 0;
      setTotalQuestions(totalQ);

      const status = (qData.status || "draft").toLowerCase();
      if (status === "draft") {
        setError("This quiz is currently in draft mode and has not yet been opened by the instructor.");
        setPhase("not_found");
        return;
      } else if (status === "ended") {
        setPhase("ended");
        return;
      }

      // Check if there is a saved active session for this specific quiz
      const saved = sessionStorage.getItem(sessionKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed?.connectionId && parsed?.studentName) {
            const qRes = await fetchCustomQuestion(quizId, parsed.connectionId);
            if (qRes.ok) {
              setConnectionId(parsed.connectionId);
              setStudentName(parsed.studentName);
              setTotalQuestions(parsed.totalQuestions || totalQ || 1);
              setCurrentScore(parsed.currentScore || 0);
              setQuestion(qRes.data);
              setQuestionNumber(qRes.data.question_number || 1);
              setTimeLeft(qRes.data.time_limit || 30);
              setPhase("question");
              return;
            } else {
              sessionStorage.removeItem(sessionKey);
            }
          }
        } catch (_) {
          sessionStorage.removeItem(sessionKey);
        }
      }

      setPhase("join");
    } catch (err) {
      setError(formatApiError(err) || "Unable to connect to quiz platform.");
      setPhase("not_found");
    }
  }, [quizId, sessionKey]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // ── Join Quiz Handler ──────────────────────────────────────────────────────
  const handleJoin = async (e) => {
    e.preventDefault();
    const trimmed = studentName.trim();
    if (!trimmed) {
      setJoinError("Please enter your name or student ID to continue.");
      return;
    }

    setJoining(true);
    setJoinError(null);

    const res = await joinCustomQuiz(quizId, trimmed);
    setJoining(false);

    if (!res.ok) {
      setJoinError(formatApiError(res.error) || "Failed to join quiz.");
      return;
    }

    const { connection_id, total_questions } = res.data;
    const finalTotal = total_questions || quiz?.question_count || 1;

    setConnectionId(connection_id);
    setTotalQuestions(finalTotal);
    setCurrentScore(0);

    // Persist session to survive browser reloads
    sessionStorage.setItem(
      sessionKey,
      JSON.stringify({
        connectionId: connection_id,
        studentName: trimmed,
        totalQuestions: finalTotal,
        currentScore: 0,
      })
    );

    // Load first question
    loadNextQuestion(connection_id);
  };

  // ── Load Question ──────────────────────────────────────────────────────────
  const loadNextQuestion = async (connId = connectionId) => {
    setPhase("loading");
    setSelectedOption(null);
    setAnswerResult(null);
    setSubmitError(null);
    clearInterval(timerRef.current);

    const res = await fetchCustomQuestion(quizId, connId);
    if (!res.ok) {
      // If questions are completed or no more questions exist, fetch summary
      handleCompleteQuiz(connId);
      return;
    }

    const qData = res.data;
    setQuestion(qData);
    setQuestionNumber(qData.question_number);
    const limit = qData.time_limit || 30;
    setTimeLeft(limit);
    setPhase("question");
  };

  // ── Countdown Timer ────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "question") {
      clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          handleTimeExpire();
          return 0;
        }
        return t - 1;
      });
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, [phase, question]);

  const handleTimeExpire = async () => {
    if (!question || submitting) return;
    const qid = question.id || question.question_id;
    if (!qid) return;

    setSubmitting(true);
    setSubmitError(null);
    const chosen = selectedOption || "A";

    const res = await submitCustomAnswer(quizId, connectionId, qid, chosen, studentName);
    setSubmitting(false);

    if (res.ok) {
      setAnswerResult({ ...res.data, timedOut: true });
      setCurrentScore(res.data.current_score);
      setPhase("feedback");

      // Update session storage
      try {
        const saved = JSON.parse(sessionStorage.getItem(sessionKey) || "{}");
        saved.currentScore = res.data.current_score;
        sessionStorage.setItem(sessionKey, JSON.stringify(saved));
      } catch (_) {}

      if (res.data.quiz_completed) {
        setTimeout(() => handleCompleteQuiz(connectionId), 2500);
      }
    } else {
      setSubmitError(formatApiError(res.error) || "Time expired, unable to evaluate answer.");
    }
  };

  // ── Submit Answer ──────────────────────────────────────────────────────────
  const handleSubmitAnswer = async () => {
    if (!selectedOption || submitting || phase !== "question") return;
    const qid = question?.id || question?.question_id;
    if (!qid) {
      setSubmitError("Question identifier missing. Please refresh and try again.");
      return;
    }

    clearInterval(timerRef.current);
    setSubmitting(true);
    setSubmitError(null);

    const res = await submitCustomAnswer(quizId, connectionId, qid, selectedOption, studentName);
    setSubmitting(false);

    if (!res.ok) {
      setSubmitError(formatApiError(res.error) || "Failed to submit answer. Please try again.");
      return;
    }

    setAnswerResult(res.data);
    setCurrentScore(res.data.current_score);
    setPhase("feedback");

    // Update stored score
    try {
      const saved = JSON.parse(sessionStorage.getItem(sessionKey) || "{}");
      saved.currentScore = res.data.current_score;
      sessionStorage.setItem(sessionKey, JSON.stringify(saved));
    } catch (_) {}

    if (res.data.quiz_completed) {
      setTimeout(() => handleCompleteQuiz(connectionId), 2500);
    }
  };

  // ── Complete Quiz & Fetch Summary ──────────────────────────────────────────
  const handleCompleteQuiz = async (connId = connectionId) => {
    setPhase("loading");
    sessionStorage.removeItem(sessionKey);

    const res = await fetchCustomSummary(quizId, connId);
    if (res.ok) {
      const data = res.data;
      setSummary({
        student_name: data.student_name || studentName,
        score: data.score,
        total_questions: data.total_questions || totalQuestions,
        correct_answers: data.score,
        incorrect_answers: Math.max(0, (data.total_questions || totalQuestions) - data.score),
        percentage: Math.round(data.percentage * 10) / 10,
        completion_time: data.completion_time || new Date().toLocaleTimeString(),
      });
      setPhase("results");
    } else {
      // Fallback summary from client session tracking
      const finalPct = totalQuestions > 0 ? Math.round((currentScore / totalQuestions) * 100) : 0;
      setSummary({
        student_name: studentName,
        score: currentScore,
        total_questions: totalQuestions,
        correct_answers: currentScore,
        incorrect_answers: Math.max(0, totalQuestions - currentScore),
        percentage: finalPct,
        completion_time: new Date().toLocaleTimeString(),
      });
      setPhase("results");
    }
  };

  // ── Scoped Leaderboard ─────────────────────────────────────────────────────
  const handleLoadLeaderboard = async () => {
    setLbLoading(true);
    setPhase("leaderboard");
    const res = await fetchCustomLeaderboard(quizId);
    setLbLoading(false);
    if (res.ok) {
      setLeaderboard(res.data?.leaderboard || []);
      setLbRefreshed(new Date().toLocaleTimeString());
    }
  };

  // ── Options normalization helper ───────────────────────────────────────────
  const getNormalizedOptions = (opts) => {
    if (!opts) return [];
    if (Array.isArray(opts)) {
      return opts.map((opt, idx) => ({
        letter: OPTION_LABELS[idx] || String.fromCharCode(65 + idx),
        text: String(opt),
      }));
    }
    return Object.entries(opts).map(([key, val]) => ({
      letter: String(key).toUpperCase(),
      text: String(val),
    }));
  };

  // Progress metrics
  const progressPercent =
    totalQuestions > 0 ? Math.round(((questionNumber - 1) / totalQuestions) * 100) : 0;
  const timeLimit = question?.time_limit || 30;
  const timerPercent = Math.round((timeLeft / timeLimit) * 100);
  const timerColor = timeLeft > 15 ? "#22c55e" : timeLeft > 7 ? "#f59e0b" : "#ef4444";

  return (
    <div className="netquiz-app">
      <Navbar
        isOnline={isOnline}
        isLoading={false}
        onRefresh={fetchInitialData}
        currentView="custom-quiz"
        onNavHome={() => navigateTo("/")}
        onNavLeaderboard={() => handleLoadLeaderboard()}
        serverStatus={serverStatus}
      />

      <main className="main-viewport">
        {/* ── PHASE: LOADING ──────────────────────────────────────────────── */}
        {phase === "loading" && (
          <div className="quiz-loading-screen">
            <div className="quiz-spinner" />
            <p className="quiz-loading-text">Communicating with NetQuiz TCP backend…</p>
            <p className="quiz-loading-sub">
              FastAPI Bridge &bull; Port 8000 &bull; Quiz ID: {quizId}
            </p>
          </div>
        )}

        {/* ── PHASE: NOT FOUND / ERROR ─────────────────────────────────────── */}
        {phase === "not_found" && (
          <div className="quiz-error-screen">
            <span className="quiz-error-icon">⚠️</span>
            <h3>Quiz Unavailable</h3>
            <p className="quiz-error-msg">
              {error || "The requested quiz ID does not exist or has not been published yet."}
            </p>
            <div className="quiz-error-btn-group">
              <button className="btn-primary-join" onClick={fetchInitialData}>
                Retry Connection
              </button>
              <button className="btn-secondary-home" onClick={() => navigateTo("/")}>
                Return to Home
              </button>
            </div>
          </div>
        )}

        {/* ── PHASE: ENDED ─────────────────────────────────────────────────── */}
        {phase === "ended" && (
          <div className="quiz-error-screen">
            <span className="quiz-error-icon">🏁</span>
            <h3>This Quiz Has Ended</h3>
            <p className="quiz-error-msg">
              The instructor has concluded submissions for <strong>{quiz?.title || quizId}</strong>.
              You can still review the final rankings.
            </p>
            <div className="quiz-error-btn-group">
              <button className="btn-primary-join" onClick={handleLoadLeaderboard}>
                🏆 View Quiz Leaderboard
              </button>
              <button className="btn-secondary-home" onClick={() => navigateTo("/")}>
                Return to Home
              </button>
            </div>
          </div>
        )}

        {/* ── PHASE: JOIN ─────────────────────────────────────────────────── */}
        {phase === "join" && quiz && (
          <div className="custom-quiz-join-container">
            {/* Header / Hero */}
            <div className="custom-quiz-info-hero">
              <div className="join-kicker-row">
                <span className="join-badge-subject">{quiz.category || "Computer Networks"}</span>
                <span className="join-badge-type">{quiz.type || "Assessment"}</span>
                <span className="quiz-id-pill">
                  <code>ID: {quiz.quiz_id}</code>
                </span>
              </div>

              <h1 className="custom-quiz-title">{quiz.title}</h1>
              <p className="custom-quiz-desc">
                {quiz.description || "Welcome! Enter your name below to begin your server-evaluated quiz attempt."}
              </p>

              <div className="custom-quiz-specs-pill">
                <span>❓ {totalQuestions} Questions</span>
                <span>⏱️ {quiz.time_limit_minutes ? `${quiz.time_limit_minutes} min total` : "Timed per question"}</span>
                <span>🔒 Server-Side Truth Enforcement</span>
              </div>
            </div>

            {/* Join Form Card */}
            <div className="join-card">
              <div className="join-card-header">
                <div className="join-card-title-group">
                  <span className="join-icon">🚀</span>
                  <span className="join-card-title">Join Live Quiz Session</span>
                </div>
                <span className="quiz-status-pill pill-active">
                  <span className="pulse-dot" /> ACTIVE
                </span>
              </div>

              <form className="join-form" onSubmit={handleJoin}>
                <div className="input-group">
                  <label className="input-label" htmlFor="custom-student-name">
                    YOUR FULL NAME / STUDENT ID *
                  </label>
                  <div className="input-field-wrap">
                    <span className="input-prefix-icon">👤</span>
                    <input
                      id="custom-student-name"
                      type="text"
                      className="input-text"
                      placeholder="e.g. Ishita Bhadani"
                      value={studentName}
                      onChange={(e) => {
                        setStudentName(e.target.value);
                        if (joinError) setJoinError(null);
                      }}
                      maxLength={50}
                      disabled={joining}
                      autoFocus
                      required
                    />
                  </div>
                </div>

                {joinError && (
                  <div className="join-alert alert-error">
                    <span>⚠️ {joinError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  className="btn-primary-join"
                  disabled={joining}
                  id="btn-start-custom-quiz"
                >
                  {joining ? (
                    <>
                      <span className="btn-spinner" /> Connecting to Quiz Session…
                    </>
                  ) : (
                    <>
                      <span>START THIS QUIZ</span>
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

              <div className="join-card-footer">
                <div className="footer-spec-item">
                  <span className="spec-label">Quiz Cohort</span>
                  <span className="spec-val">Isolated ({quiz.quiz_id})</span>
                </div>
                <div className="footer-spec-item">
                  <span className="spec-label">Evaluation Engine</span>
                  <span className="spec-val">FastAPI Bridge / Server Truth</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── PHASE: QUESTION & FEEDBACK ──────────────────────────────────── */}
        {(phase === "question" || phase === "feedback") && question && (
          <div className="quiz-page">
            {/* Header Bar */}
            <div className="quiz-header">
              <div className="quiz-header-info">
                <span className="quiz-tag-chip">📝 {quiz?.title || "Custom Quiz"}</span>
                <span className="quiz-student-chip">👤 {studentName}</span>
                <span className="quiz-conn-chip">
                  <span className="tcp-live-dot" /> TCP :5000 &bull; {connectionId ? connectionId.slice(0, 16) + "…" : "Connected"}
                </span>
              </div>
              <div className="quiz-score-chip">
                Score: {currentScore} / {totalQuestions}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="quiz-progress-wrap">
              <div className="quiz-progress-track">
                <div
                  className="quiz-progress-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <span className="quiz-progress-label">
                Q {questionNumber} of {totalQuestions}
              </span>
            </div>

            {/* Question Card */}
            {phase === "question" && (
              <div className="quiz-card">
                {/* Timer row */}
                <div className="quiz-timer-row">
                  <span className="quiz-timer-label">⏱ Time Left</span>
                  <div className="quiz-timer-bar-track">
                    <div
                      className="quiz-timer-bar-fill"
                      style={{
                        width: `${timerPercent}%`,
                        background: timerColor,
                      }}
                    />
                  </div>
                  <span className="quiz-timer-count" style={{ color: timerColor }}>
                    {timeLeft}s
                  </span>
                </div>

                {/* Metadata Row */}
                <div className="quiz-question-meta-row">
                  <div className="quiz-question-number">
                    Question {question.question_number || questionNumber} of {totalQuestions}
                  </div>
                  <span className="quiz-type-badge">
                    {question.type === "true_false" ? "True / False" : "Multiple Choice"} &bull; {question.points || 1} pt
                  </span>
                </div>

                {/* Question text */}
                <h2 className="quiz-question-text">{question.question}</h2>

                {/* Options Grid */}
                <div className="quiz-options-grid">
                  {getNormalizedOptions(question.options).map(({ letter, text }) => {
                    const isSelected = selectedOption === letter;
                    return (
                      <button
                        key={letter}
                        className={`quiz-option-btn ${isSelected ? "option-selected" : ""}`}
                        onClick={() => {
                          setSelectedOption(letter);
                          if (submitError) setSubmitError(null);
                        }}
                        disabled={submitting}
                        id={`option-${letter}`}
                      >
                        <span className="option-label-badge">{letter}</span>
                        <span className="option-text">{text}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Submission Error Banner */}
                {submitError && (
                  <div className="quiz-inline-error">
                    <span className="error-icon">⚠️</span>
                    <span className="error-text">{submitError}</span>
                  </div>
                )}

                {/* Submit button */}
                <button
                  className="btn-quiz-submit"
                  onClick={handleSubmitAnswer}
                  disabled={!selectedOption || submitting}
                  id="btn-submit-custom-answer"
                >
                  {submitting ? (
                    <>
                      <span className="btn-spinner" /> Evaluating on Server…
                    </>
                  ) : (
                    <>Submit Answer →</>
                  )}
                </button>

                {/* Academic Note */}
                <p className="quiz-academic-note">
                  📡 Answer sent via HTTP POST → FastAPI → CustomQuizManager (isolated session {quizId})
                </p>
              </div>
            )}

            {/* Feedback Card */}
            {phase === "feedback" && answerResult && (
              <div
                className={`quiz-feedback-card ${
                  answerResult.correct ? "feedback-correct" : "feedback-incorrect"
                }`}
              >
                {answerResult.timedOut ? (
                  <div className="feedback-verdict-row">
                    <span className="verdict-icon">⏰</span>
                    <span className="verdict-text">Time's Up!</span>
                  </div>
                ) : (
                  <div className="feedback-verdict-row">
                    <span className="verdict-icon">
                      {answerResult.correct ? "✅" : "❌"}
                    </span>
                    <span className="verdict-text">
                      {answerResult.correct ? "Correct!" : "Incorrect"}
                    </span>
                  </div>
                )}

                <div className="feedback-detail-grid">
                  <div className="feedback-detail-row">
                    <span className="fb-label">Your Answer</span>
                    <span
                      className={`fb-val ${
                        answerResult.correct ? "val-correct" : "val-wrong"
                      }`}
                    >
                      {answerResult.timedOut ? "Time Expired" : answerResult.submitted_answer}
                    </span>
                  </div>
                  <div className="feedback-detail-row">
                    <span className="fb-label">Correct Answer</span>
                    <span className="fb-val val-correct">{answerResult.correct_answer}</span>
                  </div>
                  <div className="feedback-detail-row">
                    <span className="fb-label">Current Score</span>
                    <span className="fb-val">
                      {answerResult.current_score} / {totalQuestions}
                    </span>
                  </div>
                </div>

                {answerResult.explanation && (
                  <div className="feedback-explanation">
                    <span className="explanation-icon">💡</span>
                    <p>{answerResult.explanation}</p>
                  </div>
                )}

                {answerResult.quiz_completed ? (
                  <div className="feedback-complete-notice">
                    🎉 Quiz complete! Calculating final results…
                  </div>
                ) : (
                  <button
                    className="btn-next-question"
                    onClick={() => loadNextQuestion()}
                    id="next-question-btn"
                  >
                    Next Question →
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── PHASE: RESULTS ──────────────────────────────────────────────── */}
        {phase === "results" && summary && (() => {
          const grade = getGrade(summary.percentage);
          const circumference = 2 * Math.PI * 54;
          const dashOffset = circumference - (summary.percentage / 100) * circumference;

          return (
            <div className="results-page">
              <div className="results-card">
                <div className="results-header">
                  <span className="results-grade-icon">{grade.icon}</span>
                  <h2 className="results-title">Quiz Complete!</h2>
                  <p className="results-student">{summary.student_name}</p>
                </div>

                {/* Circular Score Ring */}
                <div className="results-ring-wrap">
                  <svg width="140" height="140" viewBox="0 0 140 140">
                    <circle
                      cx="70"
                      cy="70"
                      r="54"
                      fill="none"
                      stroke="rgba(0,0,0,0.06)"
                      strokeWidth="10"
                    />
                    <circle
                      cx="70"
                      cy="70"
                      r="54"
                      fill="none"
                      stroke={grade.color}
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={circumference}
                      strokeDashoffset={dashOffset}
                      transform="rotate(-90 70 70)"
                      style={{ transition: "stroke-dashoffset 1s ease" }}
                    />
                    <text x="70" y="66" textAnchor="middle" className="ring-score-text">
                      {summary.score}/{summary.total_questions}
                    </text>
                    <text x="70" y="84" textAnchor="middle" className="ring-pct-text">
                      {summary.percentage}%
                    </text>
                  </svg>
                </div>

                {/* Grade Badge */}
                <div
                  className="results-grade-badge"
                  style={{ borderColor: grade.color, color: grade.color }}
                >
                  {grade.label}
                </div>

                {/* Stats Grid */}
                <div className="results-stats-grid">
                  <div className="results-stat">
                    <span className="rs-icon">✅</span>
                    <span className="rs-value">{summary.correct_answers}</span>
                    <span className="rs-label">Correct</span>
                  </div>
                  <div className="results-stat">
                    <span className="rs-icon">❌</span>
                    <span className="rs-value">{summary.incorrect_answers}</span>
                    <span className="rs-label">Incorrect</span>
                  </div>
                  <div className="results-stat">
                    <span className="rs-icon">📊</span>
                    <span className="rs-value">{summary.percentage}%</span>
                    <span className="rs-label">Score</span>
                  </div>
                </div>

                {/* Academic Note */}
                <div className="results-academic-note">
                  <span className="note-icon">🔒</span>
                  <span>
                    Score evaluated strictly server-side by CustomQuizManager for quiz{" "}
                    <code>{quizId}</code>. No client-side evaluation.
                  </span>
                </div>

                {summary.completion_time && (
                  <p className="results-time">Completed at: {summary.completion_time}</p>
                )}

                {/* Actions */}
                <div className="results-actions">
                  <button
                    className="btn-leaderboard"
                    onClick={handleLoadLeaderboard}
                    id="view-custom-lb-btn"
                  >
                    🏅 View Quiz Leaderboard
                  </button>
                  <button
                    className="btn-retry"
                    onClick={() => {
                      sessionStorage.removeItem(sessionKey);
                      setPhase("join");
                    }}
                    id="retry-custom-quiz-btn"
                  >
                    ↻ Try Again
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {/* ── PHASE: LEADERBOARD ──────────────────────────────────────────── */}
        {phase === "leaderboard" && (
          <div className="leaderboard-page">
            <div className="leaderboard-card">
              <div className="lb-header">
                <div className="lb-title-row">
                  <span className="lb-icon">🏆</span>
                  <div>
                    <h2 className="lb-title">{quiz?.title || "Custom Quiz"} Leaderboard</h2>
                    <p className="lb-subtitle">
                      Scoped to Quiz ID: <code>{quizId}</code> &bull; Independent student cohort
                    </p>
                  </div>
                </div>

                <div className="lb-refresh-row">
                  {lbRefreshed && (
                    <span className="lb-refresh-time">Updated {lbRefreshed}</span>
                  )}
                  <button
                    className="btn-refresh-lb"
                    onClick={handleLoadLeaderboard}
                    disabled={lbLoading}
                    id="refresh-custom-lb-btn"
                  >
                    {lbLoading ? "↻ Loading…" : "↻ Refresh"}
                  </button>
                </div>
              </div>

              <div className="lb-academic-note">
                <span>📡</span>
                <span>
                  Rankings fetched from <code>GET /api/quizzes/{quizId}/leaderboard</code> &bull; Strictly isolated to this quiz
                </span>
              </div>

              {lbLoading && leaderboard.length === 0 ? (
                <div className="lb-loading">
                  <div className="quiz-spinner" />
                  <p>Fetching rankings from server…</p>
                </div>
              ) : leaderboard.length === 0 ? (
                <div className="lb-empty">
                  <span className="lb-empty-icon">📭</span>
                  <p>No completed submissions yet for this quiz.</p>
                  <p className="lb-empty-sub">Complete the quiz to appear here!</p>
                </div>
              ) : (
                <div className="lb-table-wrap">
                  <table className="lb-table">
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Student</th>
                        <th>Score</th>
                        <th>Percentage</th>
                        <th>Completed At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((entry, idx) => {
                        const rank = idx + 1;
                        const medal =
                          rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;
                        const isCurrent =
                          studentName &&
                          entry.student_name?.trim().toLowerCase() ===
                            studentName.trim().toLowerCase();

                        return (
                          <tr
                            key={entry.student_name + idx}
                            className={`lb-row ${isCurrent ? "lb-row-current" : ""}`}
                          >
                            <td className="lb-cell-rank">{medal}</td>
                            <td className="lb-cell-name">
                              {entry.student_name}
                              {isCurrent && <span className="lb-you-badge">YOU</span>}
                            </td>
                            <td className="lb-cell-score">
                              <strong>{entry.score}</strong> / {entry.total_questions}
                            </td>
                            <td className="lb-cell-pct">{entry.percentage}%</td>
                            <td className="lb-cell-time">
                              {entry.submitted_at || entry.time_taken || "-"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="results-actions" style={{ marginTop: "1.5rem" }}>
                {summary && (
                  <button
                    className="btn-retry"
                    onClick={() => setPhase("results")}
                  >
                    ← Back to Results
                  </button>
                )}
                <button
                  className="btn-leaderboard"
                  style={{ background: "var(--secondary)" }}
                  onClick={() => navigateTo("/")}
                >
                  Return to Home
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer isOnline={isOnline} serverStatus={serverStatus} />
    </div>
  );
}
