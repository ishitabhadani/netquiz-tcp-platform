import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchCurrentQuestion,
  submitAnswer,
  fetchQuizSummary,
} from "../services/api";

const OPTION_LABELS = ["A", "B", "C", "D"];

/**
 * Quiz Page — Interactive question-and-answer flow.
 *
 * Academic note: Each question is fetched from the server (FastAPI → QuizManager).
 * The correct answer is NEVER sent in the question payload — only evaluated after
 * the student submits, demonstrating server-side truth enforcement.
 */
export function Quiz({ session, onQuizComplete, onBackToHome }) {
  const { connectionId, studentName, totalQuestions } = session;

  // ── State ─────────────────────────────────────────────────────────────────
  const [phase, setPhase] = useState("loading"); // loading | question | feedback | done
  const [question, setQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [answerResult, setAnswerResult] = useState(null);
  const [currentScore, setCurrentScore] = useState(0);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Timer
  const [timeLeft, setTimeLeft] = useState(30);
  const timerRef = useRef(null);

  // ── Fetch question ─────────────────────────────────────────────────────────
  const loadQuestion = useCallback(async () => {
    setPhase("loading");
    setSelectedOption(null);
    setAnswerResult(null);
    setError(null);
    setSubmitError(null);
    setTimeLeft(30);

    const res = await fetchCurrentQuestion(connectionId);
    if (!res.ok) {
      setError(res.error || "Failed to load question.");
      setPhase("error");
      return;
    }
    setQuestion(res.data);
    setQuestionNumber(res.data.question_number);
    setPhase("question");
  }, [connectionId]);

  // Load first question on mount
  useEffect(() => {
    loadQuestion();
  }, [loadQuestion]);

  // ── Countdown timer ────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "question") {
      clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          // Auto-submit with a dummy answer "X" to move to next question
          handleTimeUp();
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [phase, question]);

  const handleTimeUp = useCallback(async () => {
    if (!question || submitting) return;
    clearInterval(timerRef.current);
    setSubmitting(true);
    setSubmitError(null);
    // Submit a time-expired placeholder — server will mark incorrect
    const res = await submitAnswer(connectionId, question.question_id, "A", studentName);
    setSubmitting(false);
    if (res.ok) {
      setAnswerResult({ ...res.data, timedOut: true });
      setCurrentScore(res.data.current_score);
      setPhase("feedback");
      if (res.data.quiz_completed) {
        setTimeout(() => handleQuizDone(), 2000);
      }
    } else {
      setSubmitError(res.error || "Unable to submit your answer. Please try again.");
    }
  }, [question, connectionId, submitting, studentName]);

  // ── Submit answer ──────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!selectedOption || submitting || phase !== "question") return;
    clearInterval(timerRef.current);
    setSubmitting(true);
    setSubmitError(null);

    const res = await submitAnswer(
      connectionId,
      question.question_id,
      selectedOption,
      studentName
    );
    setSubmitting(false);

    if (!res.ok) {
      setSubmitError(res.error || "Unable to submit your answer. Please try again.");
      return;
    }

    setAnswerResult(res.data);
    setCurrentScore(res.data.current_score);
    setPhase("feedback");

    if (res.data.quiz_completed) {
      setTimeout(() => handleQuizDone(), 2500);
    }
  };

  const handleNextQuestion = () => {
    if (answerResult?.quiz_completed) {
      handleQuizDone();
    } else {
      loadQuestion();
    }
  };

  const handleQuizDone = async () => {
    const summaryRes = await fetchQuizSummary(connectionId);
    if (summaryRes.ok) {
      onQuizComplete(summaryRes.data);
    } else {
      // Fallback: construct summary from last answer result
      onQuizComplete({
        student_name: studentName,
        score: currentScore,
        total_questions: totalQuestions,
        correct_answers: currentScore,
        incorrect_answers: totalQuestions - currentScore,
        percentage: Math.round((currentScore / totalQuestions) * 100 * 10) / 10,
        completion_time: new Date().toLocaleTimeString(),
      });
    }
  };

  // ── Progress bar ───────────────────────────────────────────────────────────
  const progressPercent = Math.round(((questionNumber - 1) / totalQuestions) * 100);
  const timerPercent = Math.round((timeLeft / 30) * 100);
  const timerColor =
    timeLeft > 15 ? "#22c55e" : timeLeft > 7 ? "#f59e0b" : "#ef4444";

  // ── Render: Loading ────────────────────────────────────────────────────────
  if (phase === "loading") {
    return (
      <div className="quiz-loading-screen">
        <div className="quiz-spinner" />
        <p className="quiz-loading-text">Fetching question from server…</p>
        <p className="quiz-loading-sub">
          GET /api/quiz/question → QuizManager → Response
        </p>
      </div>
    );
  }

  // ── Render: Error ──────────────────────────────────────────────────────────
  if (phase === "error") {
    const isSessionExpired =
      error?.toLowerCase().includes("not found") ||
      error?.toLowerCase().includes("session") ||
      error?.toLowerCase().includes("expired") ||
      error?.toLowerCase().includes("invalid");

    return (
      <div className="quiz-error-screen">
        <span className="quiz-error-icon">⚠️</span>
        <h3>{isSessionExpired ? "Quiz Session Expired" : "Connection Issue"}</h3>
        <p className="quiz-error-msg">
          {isSessionExpired
            ? "Your quiz session is no longer active. Please join again."
            : error || "Unable to connect to NetQuiz server."}
        </p>
        <div className="quiz-error-btn-group">
          {!isSessionExpired && (
            <button className="btn-primary-join" onClick={loadQuestion}>
              Retry Connection
            </button>
          )}
          <button className="btn-secondary-home" onClick={onBackToHome} id="error-back-home-btn">
            Return to Home
          </button>
        </div>
      </div>
    );
  }

  // ── Render: Question ───────────────────────────────────────────────────────
  return (
    <div className="quiz-page">
      {/* Header Bar */}
      <div className="quiz-header">
        <div className="quiz-header-info">
          <span className="quiz-student-chip">👤 {studentName}</span>
          <span className="quiz-conn-chip">
            <span className="tcp-live-dot" /> TCP :5000 &bull; {connectionId.slice(0, 16)}…
          </span>
        </div>
        <div className="quiz-score-chip">
          Score: {currentScore} / {totalQuestions}
        </div>
      </div>

      {/* Progress bar */}
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

      {/* Question card */}
      {phase === "question" && question && (
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
            <span
              className="quiz-timer-count"
              style={{ color: timerColor }}
            >
              {timeLeft}s
            </span>
          </div>

          {/* Question text */}
          <div className="quiz-question-number">
            Question {question.question_number} of {question.total_questions}
          </div>
          <h2 className="quiz-question-text">{question.question}</h2>

          {/* Options */}
          <div className="quiz-options-grid">
            {OPTION_LABELS.map((label) => {
              const isSelected = selectedOption === label;
              return (
                <button
                  key={label}
                  className={`quiz-option-btn ${isSelected ? "option-selected" : ""}`}
                  onClick={() => {
                    setSelectedOption(label);
                    if (submitError) setSubmitError(null);
                  }}
                  disabled={submitting}
                  id={`option-${label}`}
                >
                  <span className="option-label-badge">{label}</span>
                  <span className="option-text">{question.options[label]}</span>
                </button>
              );
            })}
          </div>

          {/* Submission Error Banner if any */}
          {submitError && (
            <div className="quiz-inline-error">
              <span className="error-icon">⚠️</span>
              <span className="error-text">{submitError}</span>
            </div>
          )}

          {/* Submit */}
          <button
            className="btn-quiz-submit"
            onClick={handleSubmit}
            disabled={!selectedOption || submitting}
            id="submit-answer-btn"
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
            📡 Answer sent via HTTP POST → FastAPI → QuizManager (server-side evaluation)
          </p>
        </div>
      )}

      {/* Feedback card */}
      {phase === "feedback" && answerResult && (
        <div className={`quiz-feedback-card ${answerResult.correct ? "feedback-correct" : "feedback-incorrect"}`}>
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
              <span className={`fb-val ${answerResult.correct ? "val-correct" : "val-wrong"}`}>
                {answerResult.timedOut ? "Time Expired" : answerResult.submitted_answer}
              </span>
            </div>
            <div className="feedback-detail-row">
              <span className="fb-label">Correct Answer</span>
              <span className="fb-val val-correct">{answerResult.correct_answer}</span>
            </div>
            <div className="feedback-detail-row">
              <span className="fb-label">Current Score</span>
              <span className="fb-val">{answerResult.current_score} / {answerResult.total_questions}</span>
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
              onClick={handleNextQuestion}
              id="next-question-btn"
            >
              Next Question →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
