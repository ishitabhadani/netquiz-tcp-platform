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
} from "../services/api";
import { navigateTo } from "../services/router";

const OPTION_LABELS = ["A", "B", "C", "D"];

export function StudentCustomQuiz({ quizId }) {
  // Navigation / Phase: 'loading' | 'join' | 'question' | 'feedback' | 'results' | 'leaderboard' | 'not_found' | 'ended'
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
  const [answerResult, setAnswerResult] = useState(null);
  const [currentScore, setCurrentScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(30);
  const timerRef = useRef(null);

  // Results state
  const [summary, setSummary] = useState(null);

  // Scoped Leaderboard state
  const [leaderboard, setLeaderboard] = useState([]);
  const [lbLoading, setLbLoading] = useState(false);

  // ── Fetch Server Status & Public Quiz Meta ──────────────────────────────────
  const fetchInitialData = useCallback(async () => {
    setPhase("loading");
    setError(null);

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
        setError(quizRes.error || "Quiz not found or currently unavailable.");
        setPhase("not_found");
        return;
      }

      const qData = quizRes.data;
      setQuiz(qData);
      setTotalQuestions(qData.question_count || qData.questions?.length || 0);

      const status = (qData.status || "draft").toLowerCase();
      if (status === "draft") {
        setError("This quiz is currently in draft mode and has not yet been opened by the instructor.");
        setPhase("not_found");
      } else if (status === "ended") {
        setPhase("ended");
      } else {
        setPhase("join");
      }
    } catch {
      setError("Unable to connect to quiz platform.");
      setPhase("not_found");
    }
  }, [quizId]);

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
      setJoinError(res.error || "Failed to join quiz.");
      return;
    }

    const { connection_id, total_questions } = res.data;
    setConnectionId(connection_id);
    setTotalQuestions(total_questions || quiz?.question_count || 1);
    // Load first question
    loadNextQuestion(connection_id);
  };

  // ── Load Question ──────────────────────────────────────────────────────────
  const loadNextQuestion = async (connId = connectionId) => {
    setPhase("loading");
    setSelectedOption(null);
    setAnswerResult(null);
    clearInterval(timerRef.current);

    const res = await fetchCustomQuestion(quizId, connId);
    if (!res.ok) {
      // If questions are completed, fetch summary
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
    setSubmitting(true);
    // Time expired: submit empty or current choice for evaluation
    const chosen = selectedOption || "A";
    const res = await submitCustomAnswer(quizId, connectionId, question.question_id, chosen, studentName);
    setSubmitting(false);

    if (res.ok) {
      setAnswerResult({ ...res.data, timedOut: true });
      setCurrentScore(res.data.current_score);
      setPhase("feedback");
      if (res.data.quiz_completed) {
        setTimeout(() => handleCompleteQuiz(connectionId), 2500);
      }
    }
  };

  // ── Submit Answer ──────────────────────────────────────────────────────────
  const handleSubmitAnswer = async () => {
    if (!selectedOption || submitting || phase !== "question") return;
    clearInterval(timerRef.current);
    setSubmitting(true);

    const res = await submitCustomAnswer(quizId, connectionId, question.question_id, selectedOption, studentName);
    setSubmitting(false);

    if (!res.ok) {
      alert(res.error || "Failed to submit answer.");
      return;
    }

    setAnswerResult(res.data);
    setCurrentScore(res.data.current_score);
    setPhase("feedback");

    if (res.data.quiz_completed) {
      setTimeout(() => handleCompleteQuiz(connectionId), 2500);
    }
  };

  // ── Complete Quiz & Fetch Summary ──────────────────────────────────────────
  const handleCompleteQuiz = async (connId = connectionId) => {
    setPhase("loading");
    const res = await fetchCustomSummary(quizId, connId);
    if (res.ok) {
      setSummary(res.data);
      setPhase("results");
    } else {
      // Fallback summary
      setSummary({
        student_name: studentName,
        score: currentScore,
        total_questions: totalQuestions,
        percentage: Math.round((currentScore / totalQuestions) * 100),
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
    }
  };

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
        {/* Loading */}
        {phase === "loading" && (
          <div className="custom-quiz-loading">
            <div className="quiz-spinner" />
            <p>Communicating with NetQuiz TCP backend…</p>
          </div>
        )}

        {/* Not Found / Unavailable */}
        {phase === "not_found" && (
          <div className="custom-quiz-error-card">
            <div className="error-icon">⚠️</div>
            <h2>Quiz Not Available</h2>
            <p>{error || "The requested quiz ID does not exist or has expired."}</p>
            <div className="error-actions">
              <button className="btn-secondary-home" onClick={() => navigateTo("/")}>
                ← Go to Student Platform
              </button>
            </div>
          </div>
        )}

        {/* Ended View */}
        {phase === "ended" && (
          <div className="custom-quiz-ended-card">
            <div className="ended-icon">🏁</div>
            <h2>This Quiz Has Ended</h2>
            <p>
              The instructor has concluded submissions for <strong>{quiz?.title}</strong>.
              You can view the final scoped leaderboard below.
            </p>
            <div className="ended-actions">
              <button className="btn-primary-join" onClick={handleLoadLeaderboard}>
                🏆 View Final Quiz Leaderboard
              </button>
              <button className="btn-secondary-home" onClick={() => navigateTo("/")}>
                ← Return Home
              </button>
            </div>
          </div>
        )}

        {/* ── PHASE: JOIN ─────────────────────────────────────────────────── */}
        {phase === "join" && quiz && (
          <div className="custom-quiz-join-container">
            {/* Header info */}
            <div className="custom-quiz-info-hero">
              <div className="join-kicker-row">
                <span className="join-badge-subject">{quiz.subject || "Computer Networks"}</span>
                <span className="join-badge-type">{quiz.type || "Test"}</span>
                <span className="quiz-id-pill">
                  <code>ID: {quiz.quiz_id}</code>
                </span>
              </div>

              <h1 className="custom-quiz-title">{quiz.title}</h1>
              <p className="custom-quiz-desc">
                {quiz.description || "Welcome! Complete all questions and submit for server-side evaluation."}
              </p>

              <div className="custom-quiz-specs-pill">
                <span>❓ {totalQuestions} Questions</span>
                <span>⏱️ {quiz.time_limit ? `${quiz.time_limit}s total` : "Timed per question"}</span>
                <span>🔒 Server-Verified Scoring</span>
              </div>
            </div>

            {/* Join Form Card */}
            <div className="join-card">
              <div className="join-card-header">
                <div className="join-card-title-group">
                  <span className="join-icon">🚀</span>
                  <span className="join-card-title">Enter Student Identifier</span>
                </div>
                <span className="quiz-status-pill pill-active">
                  <span className="pulse-dot" /> OPEN
                </span>
              </div>

              <form className="join-form" onSubmit={handleJoin}>
                <div className="input-group">
                  <label className="input-label" htmlFor="student-name">
                    YOUR FULL NAME / STUDENT ID *
                  </label>
                  <div className="input-field-wrap">
                    <span className="input-prefix-icon">👤</span>
                    <input
                      id="student-name"
                      type="text"
                      className="input-text"
                      placeholder="e.g. Aarav Sharma"
                      value={studentName}
                      onChange={(e) => {
                        setStudentName(e.target.value);
                        if (joinError) setJoinError(null);
                      }}
                      maxLength={50}
                      disabled={joining}
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
          <div className="quiz-container">
            {/* Top Bar with Quiz Title & Progress */}
            <div className="quiz-header-card">
              <div className="quiz-header-top">
                <div className="quiz-info-group">
                  <span className="quiz-tag">{quiz?.title || "Quiz"}</span>
                  <div className="quiz-session-pill">
                    <span className="tcp-live-dot" />
                    <span>Student: {studentName}</span>
                  </div>
                </div>

                <div className="quiz-timer-pill">
                  <span className="timer-icon">⏱️</span>
                  <span className={`timer-seconds ${timeLeft <= 5 ? "timer-urgent" : ""}`}>
                    {timeLeft}s
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="quiz-progress-wrap">
                <div className="progress-labels">
                  <span className="progress-step-text">
                    Question {questionNumber} of {totalQuestions}
                  </span>
                  <span className="progress-score-text">
                    Current Score: {currentScore} pt{currentScore !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${(questionNumber / totalQuestions) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Question Card */}
            <div className="question-card">
              <div className="question-prompt-wrap">
                <span className="question-type-badge">
                  {question.type === "true_false" ? "True / False" : "Multiple Choice"} &bull; {question.points || 1} pt
                </span>
                <h2 className="question-text">{question.question}</h2>
              </div>

              {/* Options */}
              <div className="options-container">
                {(() => {
                  const optionsList = Array.isArray(question.options)
                    ? question.options.map((opt, idx) => ({ letter: OPTION_LABELS[idx], text: opt }))
                    : Object.entries(question.options || {}).map(([key, val]) => ({ letter: key, text: val }));

                  return optionsList.map(({ letter, text }) => {
                    const isSelected = selectedOption === letter;

                    let optClass = "option-btn";
                    if (phase === "question") {
                      if (isSelected) optClass += " option-selected";
                    } else if (phase === "feedback" && answerResult) {
                      if (letter === answerResult.correct_answer) {
                        optClass += " option-correct";
                      } else if (isSelected && !answerResult.correct) {
                        optClass += " option-wrong";
                      }
                    }

                    return (
                      <button
                        key={letter}
                        className={optClass}
                        onClick={() => phase === "question" && setSelectedOption(letter)}
                        disabled={phase !== "question" || submitting}
                      >
                        <span className="opt-letter">{letter}</span>
                        <span className="opt-text">{text}</span>
                        {phase === "feedback" && letter === answerResult?.correct_answer && (
                          <span className="opt-status-badge">✓ Correct</span>
                        )}
                      </button>
                    );
                  });
                })()}
              </div>

              {/* Submit / Next Action */}
              <div className="question-actions-bar">
                {phase === "question" && (
                  <button
                    className="btn-submit-answer"
                    onClick={handleSubmitAnswer}
                    disabled={!selectedOption || submitting}
                    id="btn-submit-custom-answer"
                  >
                    {submitting ? "Evaluating answer…" : "SUBMIT ANSWER"}
                  </button>
                )}

                {phase === "feedback" && (
                  <div className="feedback-result-wrap">
                    <div
                      className={`feedback-banner ${
                        answerResult?.correct ? "feedback-correct" : "feedback-incorrect"
                      }`}
                    >
                      <span className="feedback-icon">
                        {answerResult?.correct ? "✅" : "❌"}
                      </span>
                      <span className="feedback-msg">
                        {answerResult?.correct
                          ? "Correct! Server evaluated your answer."
                          : `Incorrect. The correct answer was option ${answerResult?.correct_answer}.`}
                      </span>
                    </div>

                    {!answerResult?.quiz_completed && (
                      <button
                        className="btn-next-question"
                        onClick={() => loadNextQuestion()}
                      >
                        Next Question →
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── PHASE: RESULTS ──────────────────────────────────────────────── */}
        {phase === "results" && summary && (
          <div className="results-container">
            <div className="results-card">
              <div className="results-hero">
                <span className="results-badge">QUIZ COMPLETED</span>
                <h1 className="results-title">Great Effort, {summary.student_name}!</h1>
                <p className="results-sub">
                  Your responses for <strong>{quiz?.title}</strong> have been evaluated and recorded.
                </p>

                <div className="results-score-circle">
                  <span className="score-big">{summary.score}</span>
                  <span className="score-total">/ {summary.total_questions}</span>
                  <span className="score-pct">{summary.percentage}%</span>
                </div>
              </div>

              <div className="results-actions">
                <button
                  className="btn-primary-join"
                  onClick={handleLoadLeaderboard}
                  id="btn-view-custom-lb"
                >
                  🏆 View Quiz Leaderboard
                </button>
                <button
                  className="btn-secondary-home"
                  onClick={() => navigateTo("/")}
                >
                  ← Home
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── PHASE: LEADERBOARD ──────────────────────────────────────────── */}
        {phase === "leaderboard" && (
          <div className="leaderboard-page">
            <div className="leaderboard-card">
              <div className="lb-header">
                <div className="lb-title-row">
                  <span className="lb-icon">🏆</span>
                  <div>
                    <h2 className="lb-title">{quiz?.title || "Quiz"} Leaderboard</h2>
                    <p className="lb-subtitle">
                      Scoped to Quiz ID: <code>{quizId}</code> &bull; Independent student cohort
                    </p>
                  </div>
                </div>

                <div className="lb-refresh-row">
                  <button
                    className="btn-refresh-lb"
                    onClick={handleLoadLeaderboard}
                    disabled={lbLoading}
                  >
                    {lbLoading ? "↻ Loading…" : "↻ Refresh"}
                  </button>
                </div>
              </div>

              {lbLoading ? (
                <div className="lb-loading">
                  <div className="quiz-spinner" />
                  <p>Loading quiz leaderboard…</p>
                </div>
              ) : leaderboard.length === 0 ? (
                <div className="lb-empty">
                  <span className="lb-empty-icon">📭</span>
                  <p>No completed submissions yet for this quiz.</p>
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
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((entry, idx) => {
                        const rank = idx + 1;
                        const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;
                        const isCurrent = entry.student_name === studentName;

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
                              {entry.time_taken ? `${entry.time_taken}s` : "-"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="lb-footer-actions">
                <button
                  className="btn-secondary-home"
                  onClick={() => navigateTo("/")}
                >
                  ← Return to NetQuiz Home
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
