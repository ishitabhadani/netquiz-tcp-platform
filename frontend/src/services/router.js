/**
 * Simple SPA Router utility using window.history.pushState and popstate events.
 * Compatible with Render static site rewrites (/* -> /index.html).
 */

const LISTENERS = new Set();

export function navigateTo(path) {
  if (window.location.pathname !== path) {
    window.history.pushState({}, "", path);
    LISTENERS.forEach((cb) => cb(path));
  }
}

export function subscribeToNavigation(callback) {
  LISTENERS.add(callback);
  const handlePopState = () => {
    callback(window.location.pathname);
  };
  window.addEventListener("popstate", handlePopState);

  return () => {
    LISTENERS.delete(callback);
    window.removeEventListener("popstate", handlePopState);
  };
}

export function parseRoute(pathname = window.location.pathname) {
  const cleanPath = pathname.replace(/\/+$/, "") || "/";

  // /join/:quizId
  const joinMatch = cleanPath.match(/^\/join\/([A-Za-z0-9_-]+)$/);
  if (joinMatch) {
    return { name: "student-custom-quiz", params: { quizId: joinMatch[1] } };
  }

  // /quiz/:quizId (alternative alias for join)
  const quizAliasMatch = cleanPath.match(/^\/quiz\/([A-Za-z0-9_-]+)$/);
  if (quizAliasMatch) {
    return { name: "student-custom-quiz", params: { quizId: quizAliasMatch[1] } };
  }

  // /teacher/login
  if (cleanPath === "/teacher/login") {
    return { name: "teacher-login", params: {} };
  }

  // /teacher/create
  if (cleanPath === "/teacher/create") {
    return { name: "teacher-create", params: {} };
  }

  // /teacher/quiz/:quizId/leaderboard
  const teacherLbMatch = cleanPath.match(/^\/teacher\/quiz\/([A-Za-z0-9_-]+)\/leaderboard$/);
  if (teacherLbMatch) {
    return { name: "teacher-leaderboard", params: { quizId: teacherLbMatch[1] } };
  }

  // /teacher/quiz/:quizId/share
  const teacherShareMatch = cleanPath.match(/^\/teacher\/quiz\/([A-Za-z0-9_-]+)\/share$/);
  if (teacherShareMatch) {
    return { name: "teacher-share", params: { quizId: teacherShareMatch[1] } };
  }

  // /teacher/quiz/:quizId/edit
  const teacherEditMatch = cleanPath.match(/^\/teacher\/quiz\/([A-Za-z0-9_-]+)\/edit$/);
  if (teacherEditMatch) {
    return { name: "teacher-edit", params: { quizId: teacherEditMatch[1] } };
  }

  // /teacher/quiz/:quizId
  const teacherQuizMatch = cleanPath.match(/^\/teacher\/quiz\/([A-Za-z0-9_-]+)$/);
  if (teacherQuizMatch) {
    return { name: "teacher-quiz-details", params: { quizId: teacherQuizMatch[1] } };
  }

  // /teacher
  if (cleanPath === "/teacher" || cleanPath.startsWith("/teacher/")) {
    return { name: "teacher-dashboard", params: {} };
  }

  // Default: generic student platform
  return { name: "home", params: {} };
}
