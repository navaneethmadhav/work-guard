import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = "ws://localhost:8000/ws/monitor";
const FRAME_INTERVAL_MS = 2000; // Send frame every 2 seconds

export function useMonitor(isActive) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const wsRef = useRef(null);
    const intervalRef = useRef(null);
    const streamRef = useRef(null);

    const [status, setStatus] = useState("idle"); // idle | clear | intruder | no_face | error
    const [faceCount, setFaceCount] = useState(0);
    const [lastAlert, setLastAlert] = useState(null);
    const [warnings, setWarnings] = useState([]);
    const [wsConnected, setWsConnected] = useState(false);

    const captureFrame = useCallback(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas || video.readyState !== 4) return null;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0);
        // Return JPEG base64 (smaller than PNG)
        return canvas.toDataURL("image/jpeg", 0.6);
    }, []);

    const addWarning = useCallback((message) => {
        const warning = { id: Date.now(), message, timestamp: new Date() };
        setWarnings((prev) => [warning, ...prev].slice(0, 5));
        // Auto-dismiss after 8 seconds
        setTimeout(() => {
            setWarnings((prev) => prev.filter((w) => w.id !== warning.id));
        }, 8000);
    }, []);

    // Start camera
    const startCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: "user" },
                audio: false,
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            return true;
        } catch (err) {
            console.error("Camera error:", err);
            addWarning("Camera access denied. Monitoring cannot start.");
            return false;
        }
    }, [addWarning]);

    // Stop camera
    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
    }, []);

    // Connect WebSocket
    const connectWS = useCallback(() => {
        const token = localStorage.getItem("token");
        if (!token) return;

        const ws = new WebSocket(`${WS_URL}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsConnected(true);
            console.log("[Monitor] WebSocket connected");

            // Start sending frames
            intervalRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    const frame = captureFrame();
                    if (frame) {
                        ws.send(JSON.stringify({ type: "frame", frame }));
                    }
                }
            }, FRAME_INTERVAL_MS);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setStatus(data.status);
            setFaceCount(data.face_count || 0);

            if (data.status === "intruder") {
                setLastAlert(data);
                addWarning(
                    `⚠️ Unauthorized person detected! ${data.alert_sent ? "Email alert sent." : ""}`
                );
            } else if (data.status === "no_face") {
                addWarning("⚠️ No authorized user detected at workstation.");
            }
        };

        ws.onclose = (event) => {
            setWsConnected(false);
            console.log("[Monitor] WebSocket closed:", event.code);
        };

        ws.onerror = (err) => {
            console.error("[Monitor] WebSocket error:", err);
            setStatus("error");
        };
    }, [captureFrame, addWarning]);

    const disconnectWS = useCallback(() => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        if (wsRef.current) wsRef.current.close();
        setWsConnected(false);
        setStatus("idle");
    }, []);

    // Start/stop monitoring based on isActive
    useEffect(() => {
        if (isActive) {
            startCamera().then((ok) => {
                if (ok) connectWS();
            });
        } else {
            disconnectWS();
            stopCamera();
        }

        return () => {
            disconnectWS();
            stopCamera();
        };
    }, [isActive]);

    return {
        videoRef,
        canvasRef,
        status,
        faceCount,
        lastAlert,
        warnings,
        wsConnected,
    };
}