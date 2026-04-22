import { useState, useRef, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authAPI } from "../utils/api";

export default function Signup() {
    const navigate = useNavigate();
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);

    const [step, setStep] = useState(1); // 1: form, 2: capture face
    const [form, setForm] = useState({ username: "", email: "", password: "" });
    const [capturedImages, setCapturedImages] = useState([]);
    const [cameraOn, setCameraOn] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [capturing, setCapturing] = useState(false);

    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            streamRef.current = stream;
            videoRef.current.srcObject = stream;
            setCameraOn(true);
        } catch {
            setError("Camera access required for face registration.");
        }
    };

    const stopCamera = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setCameraOn(false);
    };

    const capturePhoto = useCallback(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        const b64 = canvas.toDataURL("image/jpeg", 0.8);
        setCapturedImages((prev) => [...prev, b64]);
    }, []);

    // Auto capture 5 photos with countdown
    const autoCapture = async () => {
        setCapturing(true);
        for (let i = 0; i < 5; i++) {
            await new Promise((r) => setTimeout(r, 800));
            capturePhoto();
        }
        setCapturing(false);
    };

    const handleSubmit = async () => {
        if (capturedImages.length < 3) {
            setError("Please capture at least 3 face images.");
            return;
        }
        setLoading(true);
        setError("");

        try {
            const formData = new FormData();
            formData.append("username", form.username);
            formData.append("email", form.email);
            formData.append("password", form.password);
            formData.append("face_images", JSON.stringify(capturedImages));

            const res = await authAPI.signup(formData);
            localStorage.setItem("token", res.data.token);
            localStorage.setItem("username", res.data.username);
            stopCamera();
            navigate("/dashboard");
        } catch (err) {
            setError(err.response?.data?.detail || "Signup failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center p-4">
            <div className="w-full max-w-lg bg-gray-900 rounded-2xl p-8 border border-gray-800">
                <h1 className="text-2xl font-bold mb-2 text-center">Create Account</h1>
                <p className="text-gray-400 text-center mb-6 text-sm">
                    Workspace Monitor — Secure Your Session
                </p>

                {error && (
                    <div className="bg-red-900/40 border border-red-500 rounded-lg p-3 mb-4 text-red-300 text-sm">
                        {error}
                    </div>
                )}

                {step === 1 && (
                    <div className="space-y-4">
                        <input
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500"
                            placeholder="Username"
                            value={form.username}
                            onChange={(e) => setForm({ ...form, username: e.target.value })}
                        />
                        <input
                            type="email"
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500"
                            placeholder="Email"
                            value={form.email}
                            onChange={(e) => setForm({ ...form, email: e.target.value })}
                        />
                        <input
                            type="password"
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500"
                            placeholder="Password"
                            value={form.password}
                            onChange={(e) => setForm({ ...form, password: e.target.value })}
                        />
                        <button
                            className="w-full bg-blue-600 hover:bg-blue-500 py-2.5 rounded-lg font-semibold transition-colors"
                            onClick={() => {
                                if (!form.username || !form.email || !form.password) {
                                    setError("All fields required");
                                    return;
                                }
                                setError("");
                                setStep(2);
                                setTimeout(startCamera, 300);
                            }}
                        >
                            Next: Register Face →
                        </button>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-4">
                        <p className="text-sm text-gray-400 text-center">
                            Look at the camera. We'll capture your face to secure your account.
                        </p>

                        {/* Video Preview */}
                        <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
                            <video
                                ref={videoRef}
                                autoPlay
                                muted
                                playsInline
                                className="w-full h-full object-cover"
                            />
                            <canvas ref={canvasRef} className="hidden" />
                            {!cameraOn && (
                                <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                                    Camera loading...
                                </div>
                            )}
                        </div>

                        {/* Captured thumbnails */}
                        <div className="flex gap-2 flex-wrap">
                            {capturedImages.map((img, i) => (
                                <img
                                    key={i}
                                    src={img}
                                    alt={`capture-${i}`}
                                    className="w-16 h-16 rounded-lg object-cover border-2 border-green-500"
                                />
                            ))}
                            {Array.from({ length: Math.max(0, 5 - capturedImages.length) }).map((_, i) => (
                                <div
                                    key={`empty-${i}`}
                                    className="w-16 h-16 rounded-lg border-2 border-dashed border-gray-600 flex items-center justify-center text-gray-600 text-xs"
                                >
                                    {i + capturedImages.length + 1}
                                </div>
                            ))}
                        </div>

                        <div className="flex gap-3">
                            <button
                                className="flex-1 bg-gray-700 hover:bg-gray-600 py-2.5 rounded-lg transition-colors"
                                onClick={capturePhoto}
                                disabled={capturing || !cameraOn}
                            >
                                📷 Capture
                            </button>
                            <button
                                className="flex-1 bg-blue-700 hover:bg-blue-600 py-2.5 rounded-lg transition-colors"
                                onClick={autoCapture}
                                disabled={capturing || !cameraOn}
                            >
                                {capturing ? "Capturing..." : "⚡ Auto Capture (5)"}
                            </button>
                        </div>

                        {capturedImages.length >= 3 && (
                            <button
                                className="w-full bg-green-600 hover:bg-green-500 py-2.5 rounded-lg font-semibold transition-colors disabled:opacity-50"
                                onClick={handleSubmit}
                                disabled={loading}
                            >
                                {loading ? "Processing face data..." : "✅ Complete Registration"}
                            </button>
                        )}

                        <button
                            className="w-full text-gray-500 hover:text-gray-300 text-sm"
                            onClick={() => {
                                stopCamera();
                                setStep(1);
                                setCapturedImages([]);
                            }}
                        >
                            ← Back
                        </button>
                    </div>
                )}

                <p className="text-center text-gray-500 text-sm mt-4">
                    Already have an account?{" "}
                    <Link to="/login" className="text-blue-400 hover:underline">
                        Login
                    </Link>
                </p>
            </div>
        </div>
    );
}