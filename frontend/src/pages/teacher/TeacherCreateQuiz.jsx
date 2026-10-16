import React, { useState, useEffect } from "react";
import { TeacherLayout } from "./TeacherLayout";
import {
  createTeacherQuiz,
  getTeacherQuiz,
  updateTeacherQuiz,
  publishTeacherQuiz,
} from "../../services/api";
import { navigateTo } from "../../services/router";

const QUIZ_TYPES = [
  "Unit Test",
  "Class Test",
  "Practice Quiz",
  "Assignment",
  "Mock Test",
  "Midterm Exam",
  "Final Exam",
];

const DEFAULT_CATEGORIES = [
  "Computer Networks",
  "TCP/IP & OSI Model",
  "Data Link Layer",
  "Network Security",
  "Routing Protocols",
  "Socket Programming",
];

export function TeacherCreateQuiz({ quizId = null }) {
  const isEditing = Boolean(quizId);

  // Stepper: 1: Details, 2: Questions, 3: Preview & Publish
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1: Details
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [subject, setSubject] = useState("Computer Networks");
  const [quizType, setQuizType] = useState("Unit Test");
  const [overallTimeLimit, setOverallTimeLimit] = useState(0); // 0 = unlimited

  // Step 2: Questions
  const [questions, setQuestions] = useState([
    {
      id: "q_001",
      question: "Which transport layer protocol provides connection-oriented, reliable byte stream delivery?",
      type: "mcq",
      options: [
        "User Datagram Protocol (UDP)",
        "Transmission Control Protocol (TCP)",
        "Internet Protocol (IP)",
        "Address Resolution Protocol (ARP)",
      ],
      correct_answer: "B",
      points: 1,
      time_limit: 30,
    },
  ]);

  // Loading & Submission
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [createdQuizId, setCreatedQuizId] = useState(null);

  // Load existing quiz if in edit mode
  useEffect(() => {
    if (isEditing && quizId) {
      setLoading(true);
      getTeacherQuiz(quizId).then((res) => {
        setLoading(false);
        if (res.ok && res.data) {
          const q = res.data;
          setTitle(q.title || "");
          setDescription(q.description || "");
          setSubject(q.subject || "Computer Networks");
          setQuizType(q.type || "Unit Test");
          setOverallTimeLimit(q.time_limit || 0);
          if (q.questions && q.questions.length > 0) {
            setQuestions(
              q.questions.map((item) => ({
                ...item,
                options: Array.isArray(item.options)
                  ? item.options
                  : [
                      item.options?.A || "",
                      item.options?.B || "",
                      item.options?.C || "",
                      item.options?.D || "",
                    ].filter((x, idx) => item.type === "true_false" ? idx < 2 : true),
              }))
            );
          }
        } else {
          setError(res.error || "Failed to load quiz details.");
        }
      });
    }
  }, [isEditing, quizId]);

  // Helper to generate next unique question ID
  const generateNextQuestionId = () => {
    const num = questions.length + 1;
    return `q_${String(num).padStart(3, "0")}`;
  };

  // ── Question Manipulations ────────────────────────────────────────────────
  const handleAddQuestion = () => {
    const newQ = {
      id: generateNextQuestionId(),
      question: "",
      type: "mcq",
      options: ["", "", "", ""],
      correct_answer: "A",
      points: 1,
      time_limit: 30,
    };
    setQuestions([...questions, newQ]);
  };

  const handleUpdateQuestion = (index, field, value) => {
    const updated = [...questions];
    updated[index] = { ...updated[index], [field]: value };

    // If changing to true_false, automatically configure options
    if (field === "type" && value === "true_false") {
      updated[index].options = ["True", "False"];
      if (updated[index].correct_answer !== "A" && updated[index].correct_answer !== "B") {
        updated[index].correct_answer = "A";
      }
    } else if (field === "type" && value === "mcq") {
      if (updated[index].options.length < 4) {
        updated[index].options = ["Option A", "Option B", "Option C", "Option D"];
      }
    }

    setQuestions(updated);
  };

  const handleUpdateOption = (qIndex, optIndex, val) => {
    const updated = [...questions];
    const newOptions = [...updated[qIndex].options];
    newOptions[optIndex] = val;
    updated[qIndex].options = newOptions;
    setQuestions(updated);
  };

  const handleDeleteQuestion = (index) => {
    if (questions.length <= 1) {
      alert("A quiz must have at least one question.");
      return;
    }
    const updated = questions.filter((_, i) => i !== index);
    setQuestions(updated);
  };

  const handleDuplicateQuestion = (index) => {
    const target = questions[index];
    const duplicate = {
      ...target,
      id: generateNextQuestionId() + "_" + Math.floor(Math.random() * 1000),
      question: `${target.question} (Copy)`,
      options: [...target.options],
    };
    const updated = [...questions];
    updated.splice(index + 1, 0, duplicate);
    setQuestions(updated);
  };

  const handleMoveUp = (index) => {
    if (index === 0) return;
    const updated = [...questions];
    const temp = updated[index - 1];
    updated[index - 1] = updated[index];
    updated[index] = temp;
    setQuestions(updated);
  };

  const handleMoveDown = (index) => {
    if (index === questions.length - 1) return;
    const updated = [...questions];
    const temp = updated[index + 1];
    updated[index + 1] = updated[index];
    updated[index] = temp;
    setQuestions(updated);
  };

  // ── Validation ─────────────────────────────────────────────────────────────
  const validateForm = () => {
    const errs = [];

    if (!title.trim()) {
      errs.push("Quiz title cannot be empty.");
    }

    if (!questions || questions.length === 0) {
      errs.push("You must include at least one question in the quiz.");
    }

    questions.forEach((q, idx) => {
      const qNum = idx + 1;
      if (!q.question.trim()) {
        errs.push(`Question #${qNum} has empty question text.`);
      }

      if (q.type === "mcq") {
        if (!q.options || q.options.length < 2) {
          errs.push(`Question #${qNum} must provide at least 2 options.`);
        } else {
          q.options.forEach((opt, oIdx) => {
            if (!opt.trim()) {
              errs.push(`Question #${qNum}: Option ${String.fromCharCode(65 + oIdx)} cannot be blank.`);
            }
          });
        }
      }

      if (!q.correct_answer) {
        errs.push(`Question #${qNum} does not have a correct answer selected.`);
      }

      if (Number(q.points) <= 0) {
        errs.push(`Question #${qNum} points must be greater than 0.`);
      }

      if (Number(q.time_limit) <= 0) {
        errs.push(`Question #${qNum} time limit must be greater than 0 seconds.`);
      }
    });

    setValidationErrors(errs);
    return errs.length === 0;
  };

  // ── Navigation between steps ──────────────────────────────────────────────
  const handleProceedToQuestions = () => {
    if (!title.trim()) {
      setError("Please provide a quiz title before proceeding.");
      return;
    }
    setError(null);
    setCurrentStep(2);
    window.scrollTo(0, 0);
  };

  const handleProceedToPreview = () => {
    setError(null);
    if (!validateForm()) {
      return;
    }
    setCurrentStep(3);
    window.scrollTo(0, 0);
  };

  // ── Save or Publish ────────────────────────────────────────────────────────
  const handleSaveDraft = async () => {
    if (!title.trim()) {
      setError("Quiz title is required to save.");
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      title: title.trim(),
      description: description.trim(),
      type: quizType,
      subject: subject.trim(),
      time_limit: Number(overallTimeLimit) || 0,
      questions: questions.map((q, idx) => ({
        id: q.id || `q_${String(idx + 1).padStart(3, "0")}`,
        question: q.question.trim(),
        type: q.type || "mcq",
        options: Array.isArray(q.options)
          ? q.options.reduce((acc, opt, oIdx) => {
              acc[String.fromCharCode(65 + oIdx)] = opt.trim();
              return acc;
            }, {})
          : q.options,
        correct_answer: q.correct_answer,
        points: Number(q.points) || 1,
        time_limit: Number(q.time_limit) || 30,
      })),
    };

    let res;
    if (isEditing) {
      res = await updateTeacherQuiz(quizId, payload);
    } else {
      res = await createTeacherQuiz(payload);
    }
    setLoading(false);

    if (res.ok) {
      const savedId = res.data?.quiz_id || quizId;
      navigateTo(`/teacher/quiz/${savedId}`);
    } else {
      setError(res.error || "Failed to save quiz draft.");
    }
  };

  const handlePublishQuiz = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      title: title.trim(),
      description: description.trim(),
      type: quizType,
      subject: subject.trim(),
      time_limit: Number(overallTimeLimit) || 0,
      questions: questions.map((q, idx) => ({
        id: q.id || `q_${String(idx + 1).padStart(3, "0")}`,
        question: q.question.trim(),
        type: q.type || "mcq",
        options: Array.isArray(q.options)
          ? q.options.reduce((acc, opt, oIdx) => {
              acc[String.fromCharCode(65 + oIdx)] = opt.trim();
              return acc;
            }, {})
          : q.options,
        correct_answer: q.correct_answer,
        points: Number(q.points) || 1,
        time_limit: Number(q.time_limit) || 30,
      })),
    };

    let targetId = quizId;
    if (isEditing) {
      const updateRes = await updateTeacherQuiz(quizId, payload);
      if (!updateRes.ok) {
        setLoading(false);
        setError(updateRes.error || "Failed to update quiz.");
        return;
      }
    } else {
      const createRes = await createTeacherQuiz(payload);
      if (!createRes.ok) {
        setLoading(false);
        setError(createRes.error || "Failed to create quiz.");
        return;
      }
      targetId = createRes.data?.quiz_id;
    }

    // Now publish the quiz
    const pubRes = await publishTeacherQuiz(targetId);
    setLoading(false);

    if (pubRes.ok) {
      navigateTo(`/teacher/quiz/${targetId}/share`);
    } else {
      setError(pubRes.error || "Quiz was saved, but publishing failed.");
    }
  };

  return (
    <TeacherLayout currentTab="create" activeQuizId={quizId}>
      <div className="teacher-builder-root">
        {/* Stepper Header */}
        <div className="builder-stepper-header">
          <div className="stepper-title-wrap">
            <h1 className="builder-title">
              {isEditing ? "Edit Quiz" : "Multi-Step Quiz Builder"}
            </h1>
            <p className="builder-sub">
              Build isolated TCP network tests with custom time limits, options, and server grading.
            </p>
          </div>

          <div className="builder-stepper-steps">
            <div
              className={`step-pill ${currentStep >= 1 ? "active" : ""}`}
              onClick={() => setCurrentStep(1)}
            >
              <span className="step-num">1</span>
              <span className="step-label">Quiz Details</span>
            </div>
            <div className="step-arrow">→</div>
            <div
              className={`step-pill ${currentStep >= 2 ? "active" : ""}`}
              onClick={() => handleProceedToQuestions()}
            >
              <span className="step-num">2</span>
              <span className="step-label">Questions ({questions.length})</span>
            </div>
            <div className="step-arrow">→</div>
            <div
              className={`step-pill ${currentStep >= 3 ? "active" : ""}`}
              onClick={() => handleProceedToPreview()}
            >
              <span className="step-num">3</span>
              <span className="step-label">Preview &amp; Publish</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="builder-error-banner">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {validationErrors.length > 0 && currentStep === 2 && (
          <div className="builder-validation-box">
            <h4>Please fix the following issues before publishing:</h4>
            <ul>
              {validationErrors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* ── STEP 1: QUIZ DETAILS ────────────────────────────────────────── */}
        {currentStep === 1 && (
          <div className="builder-step-card">
            <div className="step-card-header">
              <h2>Step 1 — Quiz Details &amp; Instructions</h2>
              <p>Configure general test information visible to students on the join screen.</p>
            </div>

            <div className="builder-form-grid">
              <div className="input-group full-width">
                <label className="input-label" htmlFor="quiz-title">
                  QUIZ TITLE *
                </label>
                <input
                  id="quiz-title"
                  type="text"
                  className="input-text"
                  placeholder="e.g. Computer Networks Unit 2 Test"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={100}
                  required
                />
              </div>

              <div className="input-group full-width">
                <label className="input-label" htmlFor="quiz-description">
                  DESCRIPTION &amp; INSTRUCTIONS FOR STUDENTS
                </label>
                <textarea
                  id="quiz-description"
                  className="input-textarea"
                  rows={4}
                  placeholder="Enter exam rules, topic coverage, or instructions (e.g. Each question is timed at 30s. Submissions are graded immediately upon completion)."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="input-group">
                <label className="input-label" htmlFor="quiz-category">
                  SUBJECT / CATEGORY
                </label>
                <input
                  id="quiz-category"
                  type="text"
                  className="input-text"
                  list="category-options"
                  placeholder="e.g. Computer Networks"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
                <datalist id="category-options">
                  {DEFAULT_CATEGORIES.map((c) => (
                    <option key={c} value={c} />
                  ))}
                </datalist>
              </div>

              <div className="input-group">
                <label className="input-label" htmlFor="quiz-type">
                  QUIZ TYPE
                </label>
                <select
                  id="quiz-type"
                  className="input-select"
                  value={quizType}
                  onChange={(e) => setQuizType(e.target.value)}
                >
                  {QUIZ_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="step-actions-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => navigateTo("/teacher")}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary-action"
                onClick={handleProceedToQuestions}
              >
                <span>Continue to Question Builder →</span>
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: QUESTION BUILDER ────────────────────────────────────── */}
        {currentStep === 2 && (
          <div className="builder-step-card">
            <div className="step-card-header">
              <div className="header-flex-between">
                <div>
                  <h2>Step 2 — Question Builder</h2>
                  <p>Add, reorder, duplicate, or delete questions. Each question has server-side answer evaluation.</p>
                </div>
                <button
                  type="button"
                  className="btn-add-question-top"
                  onClick={handleAddQuestion}
                >
                  <span>+ Add Question</span>
                </button>
              </div>
            </div>

            <div className="questions-builder-list">
              {questions.map((q, idx) => {
                const qNum = idx + 1;
                const isFirst = idx === 0;
                const isLast = idx === questions.length - 1;

                return (
                  <div key={q.id || idx} className="question-editor-card">
                    {/* Top bar of question editor */}
                    <div className="question-editor-top">
                      <div className="q-badge-wrap">
                        <span className="q-number-badge">QUESTION {qNum}</span>
                        <code className="q-id-pill">{q.id}</code>
                      </div>

                      <div className="q-control-buttons">
                        <button
                          type="button"
                          className="btn-icon-control"
                          title="Move Question Up"
                          onClick={() => handleMoveUp(idx)}
                          disabled={isFirst}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="btn-icon-control"
                          title="Move Question Down"
                          onClick={() => handleMoveDown(idx)}
                          disabled={isLast}
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          className="btn-icon-control"
                          title="Duplicate Question"
                          onClick={() => handleDuplicateQuestion(idx)}
                        >
                          📋
                        </button>
                        <button
                          type="button"
                          className="btn-icon-control btn-danger-control"
                          title="Delete Question"
                          onClick={() => handleDeleteQuestion(idx)}
                          disabled={questions.length <= 1}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    {/* Question text textarea */}
                    <div className="input-group">
                      <label className="input-label">QUESTION PROMPT *</label>
                      <textarea
                        className="input-textarea"
                        rows={3}
                        placeholder="e.g. In TCP socket programming, what does a return value of 0 from socket.recv() signify?"
                        value={q.question}
                        onChange={(e) => handleUpdateQuestion(idx, "question", e.target.value)}
                      />
                    </div>

                    {/* Question Type, Points, Time Limit Row */}
                    <div className="question-meta-row">
                      <div className="input-group">
                        <label className="input-label">QUESTION TYPE</label>
                        <select
                          className="input-select"
                          value={q.type}
                          onChange={(e) => handleUpdateQuestion(idx, "type", e.target.value)}
                        >
                          <option value="mcq">Multiple Choice (MCQ)</option>
                          <option value="true_false">True / False</option>
                        </select>
                      </div>

                      <div className="input-group">
                        <label className="input-label">POINTS</label>
                        <input
                          type="number"
                          className="input-text"
                          min={1}
                          max={100}
                          value={q.points}
                          onChange={(e) =>
                            handleUpdateQuestion(idx, "points", parseInt(e.target.value) || 1)
                          }
                        />
                      </div>

                      <div className="input-group">
                        <label className="input-label">TIME LIMIT (SECONDS)</label>
                        <input
                          type="number"
                          className="input-text"
                          min={5}
                          max={300}
                          value={q.time_limit}
                          onChange={(e) =>
                            handleUpdateQuestion(idx, "time_limit", parseInt(e.target.value) || 30)
                          }
                        />
                      </div>
                    </div>

                    {/* Options Editor */}
                    <div className="question-options-section">
                      <label className="input-label">
                        ANSWER CHOICES &amp; MARK THE CORRECT ANSWER
                      </label>

                      {q.type === "mcq" ? (
                        <div className="options-grid">
                          {["A", "B", "C", "D"].map((letter, optIdx) => (
                            <div
                              key={letter}
                              className={`option-input-row ${
                                q.correct_answer === letter ? "option-correct-selected" : ""
                              }`}
                            >
                              <label className="option-radio-label">
                                <input
                                  type="radio"
                                  name={`correct-answer-${q.id || idx}`}
                                  checked={q.correct_answer === letter}
                                  onChange={() => handleUpdateQuestion(idx, "correct_answer", letter)}
                                />
                                <span className="option-letter">{letter}</span>
                              </label>

                              <input
                                type="text"
                                className="input-text option-text-field"
                                placeholder={`Option ${letter} text`}
                                value={q.options[optIdx] || ""}
                                onChange={(e) => handleUpdateOption(idx, optIdx, e.target.value)}
                              />

                              {q.correct_answer === letter && (
                                <span className="correct-check-badge">✓ CORRECT</span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="true-false-options-row">
                          <label
                            className={`tf-choice-card ${
                              q.correct_answer === "A" ? "tf-selected" : ""
                            }`}
                          >
                            <input
                              type="radio"
                              name={`correct-tf-${q.id || idx}`}
                              checked={q.correct_answer === "A"}
                              onChange={() => handleUpdateQuestion(idx, "correct_answer", "A")}
                            />
                            <div className="tf-choice-content">
                              <span className="tf-label">True</span>
                              {q.correct_answer === "A" && (
                                <span className="correct-check-badge">✓ CORRECT</span>
                              )}
                            </div>
                          </label>

                          <label
                            className={`tf-choice-card ${
                              q.correct_answer === "B" ? "tf-selected" : ""
                            }`}
                          >
                            <input
                              type="radio"
                              name={`correct-tf-${q.id || idx}`}
                              checked={q.correct_answer === "B"}
                              onChange={() => handleUpdateQuestion(idx, "correct_answer", "B")}
                            />
                            <div className="tf-choice-content">
                              <span className="tf-label">False</span>
                              {q.correct_answer === "B" && (
                                <span className="correct-check-badge">✓ CORRECT</span>
                              )}
                            </div>
                          </label>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="add-question-footer-cta">
              <button
                type="button"
                className="btn-add-question-dashed"
                onClick={handleAddQuestion}
              >
                <span>➕ Add Another Question</span>
              </button>
            </div>

            <div className="step-actions-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setCurrentStep(1)}
              >
                ← Back to Details
              </button>

              <div className="footer-right-buttons">
                <button
                  type="button"
                  className="btn-save-draft"
                  onClick={handleSaveDraft}
                  disabled={loading}
                >
                  💾 Save as Draft
                </button>

                <button
                  type="button"
                  className="btn-primary-action"
                  onClick={handleProceedToPreview}
                >
                  <span>Preview Quiz &amp; Publish →</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 3: PREVIEW & PUBLISH ────────────────────────────────────── */}
        {currentStep === 3 && (
          <div className="builder-step-card">
            <div className="step-card-header">
              <h2>Step 3 — Preview &amp; Publish</h2>
              <p>
                Review how your quiz will appear to students. Correct answers are highlighted here
                for your verification, but are strictly hidden from students until submitted.
              </p>
            </div>

            {/* Quiz Header Preview */}
            <div className="preview-quiz-hero">
              <div className="preview-kicker">
                <span className="badge-preview">STUDENT VIEW PREVIEW</span>
                <span className="badge-type">{quizType}</span>
                <span className="badge-subject">{subject}</span>
              </div>
              <h1 className="preview-title">{title}</h1>
              <p className="preview-desc">{description || "No special instructions provided."}</p>

              <div className="preview-specs-bar">
                <div>
                  <strong>Questions:</strong> {questions.length}
                </div>
                <div>
                  <strong>Total Points:</strong>{" "}
                  {questions.reduce((acc, q) => acc + (Number(q.points) || 1), 0)}
                </div>
                <div>
                  <strong>Avg Time Limit:</strong>{" "}
                  {Math.round(
                    questions.reduce((acc, q) => acc + (Number(q.time_limit) || 30), 0) /
                      questions.length
                  )}
                  s / question
                </div>
              </div>
            </div>

            {/* Questions Preview List */}
            <div className="preview-questions-list">
              {questions.map((q, idx) => (
                <div key={idx} className="preview-question-card">
                  <div className="preview-q-top">
                    <span className="preview-q-num">Question {idx + 1} of {questions.length}</span>
                    <span className="preview-q-points">{q.points} pt{q.points > 1 ? "s" : ""} &bull; ⏱️ {q.time_limit}s</span>
                  </div>

                  <p className="preview-q-text">{q.question}</p>

                  <div className="preview-options-grid">
                    {q.options.map((opt, oIdx) => {
                      const letter = String.fromCharCode(65 + oIdx);
                      const isCorrect = q.correct_answer === letter;

                      return (
                        <div
                          key={letter}
                          className={`preview-option-pill ${isCorrect ? "preview-correct-opt" : ""}`}
                        >
                          <span className="preview-letter">{letter}</span>
                          <span className="preview-opt-text">{opt}</span>
                          {isCorrect && (
                            <span className="teacher-truth-badge">
                              ✓ Correct Answer (Server Truth)
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Publishing Validation & Actions */}
            <div className="preview-publish-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setCurrentStep(2)}
              >
                ← Back to Edit
              </button>

              <div className="publish-buttons-right">
                <button
                  type="button"
                  className="btn-save-draft"
                  onClick={handleSaveDraft}
                  disabled={loading}
                >
                  💾 Save Draft
                </button>

                <button
                  type="button"
                  className="btn-publish-final"
                  onClick={handlePublishQuiz}
                  disabled={loading}
                  id="btn-publish-quiz"
                >
                  {loading ? (
                    <>
                      <span className="btn-spinner" /> Publishing Quiz…
                    </>
                  ) : (
                    <>
                      <span>🚀 Publish &amp; Generate Link</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </TeacherLayout>
  );
}
