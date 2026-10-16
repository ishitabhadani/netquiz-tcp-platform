import React from "react";

export function NetworkStatCards({ serverStatus, quizInfo }) {
  const isRunning = serverStatus?.running ?? false;
  const activeClients = serverStatus?.active_clients ?? 0;
  const completedQuizzes = serverStatus?.completed_quizzes ?? 0;
  const totalQuestions = quizInfo?.total_questions_available ?? 15;
  const questionsPerQuiz = quizInfo?.questions_per_quiz ?? 10;
  const tcpPort = serverStatus?.port ? `Port ${serverStatus.port}` : "Port 5000";
  const tcpHost = serverStatus?.host || "127.0.0.1";

  const cards = [
    {
      title: "TCP Transport",
      value: tcpPort,
      subtext: "SOCK_STREAM • Byte Stream",
      badge: "Transport Layer",
      icon: "🔌"
    },
    {
      title: "IPv4 Network",
      value: tcpHost,
      subtext: "AF_INET • 32-Bit Address",
      badge: "Network Layer",
      icon: "🌐"
    },
    {
      title: "Concurrency",
      value: "Multithreaded",
      subtext: "Thread-Per-Client Isolation",
      badge: "OS / Runtime",
      icon: "⚡"
    },
    {
      title: "Question Bank",
      value: `${totalQuestions} Questions`,
      subtext: `${questionsPerQuiz} Selected Per Quiz`,
      badge: "Application Layer",
      icon: "📚"
    },
    {
      title: "Active Connections",
      value: `${activeClients} Connected`,
      subtext: isRunning ? "Live Sockets Accepted" : "Server Offline",
      badge: "Socket Registry",
      icon: "👥"
    },
    {
      title: "Quizzes Completed",
      value: `${completedQuizzes} Finished`,
      subtext: "Server-Evaluated Scores",
      badge: "Quiz Engine",
      icon: "🏆"
    }
  ];

  return (
    <div className="stat-cards-grid">
      {cards.map((c, i) => (
        <div key={i} className="stat-card">
          <div className="stat-card-header">
            <span className="stat-icon">{c.icon}</span>
            <span className="stat-badge">{c.badge}</span>
          </div>
          <div className="stat-title">{c.title}</div>
          <div className="stat-value">{c.value}</div>
          <div className="stat-subtext">{c.subtext}</div>
        </div>
      ))}
    </div>
  );
}
