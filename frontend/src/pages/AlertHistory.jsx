import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { alertsAPI } from "../utils/api";

export default function AlertHistory() {
    const navigate = useNavigate();
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);

    useEffect(() => {
        alertsAPI
            .getAlerts(50)
            .then((res) => setAlerts(res.data.alerts))
            .catch(() => navigate("/login"))
            .finally(() => setLoading(false));
    }, []);

    const deleteAlert = async (id) => {
        await alertsAPI.deleteAlert(id);
        setAlerts((prev) => prev.filter((a) => a._id !== id));
        if (selected?._id === id) setSelected(null);
    };

    const viewDetail = async (id) => {
        const res = await alertsAPI.getAlertDetail(id);
        setSelected(res.data);
    };

    return (
        <div className="min-h-screen bg-gray-950 text-white">
            <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
                <button
                    onClick={() => navigate("/dashboard")}
                    className="text-gray-400 hover:text-white transition-colors"
                >
                    ← Back to Dashboard
                </button>
                <h1 className="font-bold text-lg">🔔 Alert History</h1>
                <span className="text-gray-500 text-sm">{alerts.length} total</span>
            </nav>

            <main className="max-w-5xl mx-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
                    </div>
                ) : alerts.length === 0 ? (
                    <div className="text-center py-20 text-gray-500">
                        <p className="text-4xl mb-3">✅</p>
                        <p>No security alerts. Your workspace is secure.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {/* Alert List */}
                        <div className="space-y-3">
                            {alerts.map((alert) => (
                                <div
                                    key={alert._id}
                                    className={`bg-gray-900 rounded-xl p-4 border cursor-pointer transition-colors ${selected?._id === alert._id
                                            ? "border-red-500"
                                            : "border-gray-800 hover:border-gray-600"
                                        }`}
                                    onClick={() => viewDetail(alert._id)}
                                >
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <p className="text-red-400 font-semibold text-sm">⚠️ Unauthorized Access</p>
                                            <p className="text-gray-500 text-xs mt-1">
                                                {new Date(alert.timestamp).toLocaleString()}
                                            </p>
                                            <p className="text-gray-400 text-xs mt-1">
                                                {alert.face_count} face(s) detected
                                            </p>
                                        </div>
                                        {alert.intruder_image && (
                                            <img
                                                src={`data:image/jpeg;base64,${alert.intruder_image}`}
                                                alt="Intruder"
                                                className="w-14 h-14 rounded-lg object-cover ml-3 flex-shrink-0"
                                            />
                                        )}
                                    </div>
                                    <div className="flex gap-2 mt-3">
                                        <button
                                            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                viewDetail(alert._id);
                                            }}
                                        >
                                            View Details
                                        </button>
                                        <button
                                            className="text-xs text-red-500 hover:text-red-300 transition-colors ml-auto"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                deleteAlert(alert._id);
                                            }}
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Detail Panel */}
                        {selected && (
                            <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 sticky top-4 h-fit">
                                <h2 className="font-semibold mb-4">Alert Detail</h2>
                                <p className="text-gray-400 text-sm mb-4">
                                    {new Date(selected.timestamp).toLocaleString()}
                                </p>

                                {selected.intruder_image && (
                                    <div className="mb-4">
                                        <p className="text-xs text-gray-500 mb-2">Intruder Face</p>
                                        <img
                                            src={`data:image/jpeg;base64,${selected.intruder_image}`}
                                            alt="Intruder"
                                            className="rounded-xl w-full object-cover border border-red-900"
                                        />
                                    </div>
                                )}

                                {selected.frame_snapshot && (
                                    <div>
                                        <p className="text-xs text-gray-500 mb-2">Full Frame Snapshot</p>
                                        <img
                                            src={`data:image/jpeg;base64,${selected.frame_snapshot}`}
                                            alt="Frame"
                                            className="rounded-xl w-full object-cover border border-gray-700"
                                        />
                                    </div>
                                )}

                                <button
                                    className="mt-4 w-full text-red-400 hover:text-red-300 text-sm py-2 border border-red-900 rounded-lg transition-colors"
                                    onClick={() => deleteAlert(selected._id)}
                                >
                                    Delete This Alert
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}