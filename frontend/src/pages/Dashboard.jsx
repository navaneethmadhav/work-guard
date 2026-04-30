import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMonitor } from "../hooks/useMonitor";

const STATUS_CONFIG = {
  idle: { color: "text-gray-400", bg: "bg-gray-800", label: "Monitoring Off", icon: "⚫" },
  clear: { color: "text-green-400", bg: "bg-green-900/30", label: "All Clear", icon: "🟢" },
  intruder: { color: "text-red-400", bg: "bg-red-900/30", label: "INTRUDER DETECTED", icon: "🔴" },
  no_face: { color: "text-yellow-400", bg: "bg-yellow-900/30", label: "No Authorized User", icon: "🟡" },
  error: { color: "text-orange-400", bg: "bg-orange-900/30", label: "Connection Error", icon: "🟠" },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const username = localStorage.getItem("username") || "User";
  const [monitoringActive, setMonitoringActive] = useState(true);

  const { videoRef, canvasRef, status, faceCount, lastAlert, warnings, wsConnected } =
    useMonitor(monitoringActive);

  const handleLogout = () => {
    setMonitoringActive(false);
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    navigate("/login");
  };

  const statusCfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Navbar */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold">🛡️ WorkGuard</span>
          <span className="text-gray-500 text-sm hidden sm:block">Real-Time Workspace Monitor</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">👤 {username}</span>
          <button
            onClick={() => navigate("/alerts")}
            className="text-sm bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors"
          >
            🔔 Alerts
          </button>
          <button
            onClick={handleLogout}
            className="text-sm bg-red-900/40 hover:bg-red-900/60 text-red-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Warning Overlay */}
      {warnings.length > 0 && (
        <div className="fixed top-16 right-4 z-50 space-y-2 max-w-sm">
          {warnings.map((w) => (
            <div
              key={w.id}
              className="bg-red-600 text-white px-4 py-3 rounded-xl shadow-2xl border border-red-400 animate-pulse"
            >
              <p className="font-semibold text-sm">{w.message}</p>
              <p className="text-xs text-red-200 mt-1">
                {w.timestamp.toLocaleTimeString()}
              </p>
            </div>
          ))}
        </div>
      )}

      <main className="p-6 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Camera Feed */}
          <div className="lg:col-span-2">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
                <span className="font-semibold">📷 Camera Feed</span>
                <div className="flex items-center gap-2">
                  {wsConnected && (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                      Live
                    </span>
                  )}
                  <span className="text-sm text-gray-400">{faceCount} face(s) detected</span>
                </div>
              </div>

              <div className="relative bg-black aspect-video">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />
                <canvas ref={canvasRef} className="hidden" />

                {!monitoringActive && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 gap-4">
                    <p className="text-gray-400">Starting camera...</p>
                  </div>
                )}

                {/* Status badge on video */}
                {monitoringActive && (
                  <div
                    className={`absolute top-3 left-3 px-3 py-1 rounded-lg text-sm font-semibold ${statusCfg.bg} ${statusCfg.color}`}
                  >
                    {statusCfg.icon} {statusCfg.label}
                  </div>
                )}
              </div>

              <div className="px-4 py-3 flex justify-end border-t border-gray-800">
                <button
                  onClick={() => setMonitoringActive(false)}
                  className="bg-red-900/40 hover:bg-red-900/60 text-red-300 px-4 py-2 rounded-lg text-sm transition-colors"
                >
                  ⏹ Stop Monitoring
                </button>
              </div>
            </div>
          </div>

          {/* Status Panel */}
          <div className="space-y-4">
            {/* Current Status */}
            <div className={`rounded-2xl p-5 border ${statusCfg.bg} border-gray-800`}>
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-1">Current Status</p>
              <p className={`text-2xl font-bold ${statusCfg.color}`}>
                {statusCfg.icon} {statusCfg.label}
              </p>
              <p className="text-gray-500 text-sm mt-2">
                {monitoringActive ? "Scanning every 2 seconds" : "Click Start Monitoring"}
              </p>
            </div>

            {/* Stats */}
            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-3">Session Info</p>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">WebSocket</span>
                  <span className={`text-sm font-medium ${wsConnected ? "text-green-400" : "text-gray-500"}`}>
                    {wsConnected ? "Connected" : "Disconnected"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">Faces in Frame</span>
                  <span className="text-sm font-medium text-white">{faceCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">User</span>
                  <span className="text-sm font-medium text-blue-400">{username}</span>
                </div>
              </div>
            </div>

            {/* Last Alert */}
            {lastAlert && (
              <div className="bg-red-900/20 rounded-2xl p-5 border border-red-800">
                <p className="text-xs uppercase tracking-widest text-red-500 mb-2">Last Alert</p>
                {lastAlert.intruder_image && (
                  <img
                    src={`data:image/jpeg;base64,${lastAlert.intruder_image}`}
                    alt="Intruder"
                    className="w-full rounded-lg mb-3 object-cover aspect-video"
                  />
                )}
                <p className="text-red-300 text-sm">
                  Intruder detected — {new Date(lastAlert.timestamp).toLocaleTimeString()}
                </p>
                {lastAlert.alert_sent && (
                  <p className="text-red-400 text-xs mt-1">📧 Email alert sent</p>
                )}
              </div>
            )}

            {/* How It Works */}
            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-3">How It Works</p>
              <ul className="space-y-2 text-xs text-gray-400">
                <li>🟢 <strong className="text-gray-300">Clear</strong> — Registered user detected</li>
                <li>🟡 <strong className="text-gray-300">No Face</strong> — No one at screen</li>
                <li>🔴 <strong className="text-gray-300">Intruder</strong> — Unknown person detected (email sent)</li>
                <li>✅ Multiple people OK if you are present</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}