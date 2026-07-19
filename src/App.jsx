import React, { useEffect, useState, useRef, Suspense, lazy } from 'react';

import {
    useSocket,
    useChat,
    useAuth,
    useCadState,
    useBrowserState,
    useKasaState,
    usePrinterState,
    useMediaDevices,
    useModularLayout,
    useHandTracking
} from './hooks';

import Visualizer from './components/Visualizer';

const Visualizer3D = lazy(() => import('./components/Visualizer3D'));
import TopAudioBar from './components/TopAudioBar';
import CadWindow from './components/CadWindow';
import BrowserWindow from './components/BrowserWindow';
import DraggableWindow from './components/DraggableWindow';
import ChatModule from './components/ChatModule';
import ToolsModule from './components/ToolsModule';
import { Mic, MicOff, Settings, X, Minus, Power, Video, VideoOff, Layout, Hand, Printer, Clock } from 'lucide-react';
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';
// MemoryPrompt removed - memory is now actively saved to project
import ConfirmationPopup from './components/ConfirmationPopup';
import AuthLock from './components/AuthLock';
import KasaWindow from './components/KasaWindow';
import PrinterWindow from './components/PrinterWindow';
import SettingsWindow from './components/SettingsWindow';



const atlasBridge = window.atlasBridge || { send: () => {} };

function App() {
    const { socket, status, setStatus, socketConnected } = useSocket('http://localhost:8000');
    const layout = useModularLayout();
    const { elementPositions, setElementPositions, elementSizes, zIndexOrder, activeDragElement, setActiveDragElement,
        elementPositionsRef, activeDragElementRef, lastActiveDragElementRef, isModularMode, setIsModularMode,
        clampToViewport, getZIndex, bringToFront, updateElementPosition, handleMouseDown } = layout;
    const hand = useHandTracking();
    const { cursorPos, setCursorPos, isPinching, setIsPinching, isHandTrackingEnabled, setIsHandTrackingEnabled,
        cursorSensitivity, setCursorSensitivity, isCameraFlipped, setIsCameraFlipped,
        handLandmarkerRef, lastCursorPosRef, lastWristPosRef, smoothedCursorPosRef, snapStateRef,
        isHandTrackingEnabledRef, cursorSensitivityRef, isCameraFlippedRef } = hand;
    const auth = useAuth(socket, { setCameraFlipped: hand.setIsCameraFlipped });
    const { isAuthenticated, isLockScreenVisible, faceAuthEnabled, setFaceAuthEnabled } = auth;
    const chat = useChat(socket, setStatus);
    const { messages, inputValue, setInputValue, addMessage, handleSend } = chat;
    const cad = useCadState(socket, setElementPositions, clampToViewport);
    const { cadData, setCadData, cadThoughts, cadRetryInfo, showCadWindow, setShowCadWindow } = cad;
    const browser = useBrowserState(socket, setElementPositions, clampToViewport);
    const { browserData, showBrowserWindow, setShowBrowserWindow } = browser;
    const kasa = useKasaState(socket);
    const { kasaDevices, showKasaWindow, setShowKasaWindow } = kasa;
    const printer = usePrinterState(socket, setElementPositions, clampToViewport);
    const { slicingStatus, activePrintStatus, printerCount, showPrinterWindow, setShowPrinterWindow } = printer;
    const media = useMediaDevices();
    const { micDevices, speakerDevices, webcamDevices, selectedMicId, setSelectedMicId, selectedSpeakerId, setSelectedSpeakerId, selectedWebcamId, setSelectedWebcamId } = media;

    const [isConnected, setIsConnected] = useState(true);
    const [isMuted, setIsMuted] = useState(true);
    const [isVideoOn, setIsVideoOn] = useState(false);
    const [confirmationRequest, setConfirmationRequest] = useState(null);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
    const [micAudioData, setMicAudioData] = useState(new Array(32).fill(0));
    const [fps, setFps] = useState(0);
    const [showSettings, setShowSettings] = useState(false);
    const [currentProject, setCurrentProject] = useState('default');
    const [ripples, setRipples] = useState([]);

    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const animationFrameRef = useRef(null);
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const transmissionCanvasRef = useRef(null);
    const videoIntervalRef = useRef(null);
    const lastFrameTimeRef = useRef(0);
    const frameCountRef = useRef(0);
    const lastVideoTimeRef = useRef(-1);
    const isVideoOnRef = useRef(false);

    // Live Clock Update
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    // Ref to track if model has been auto-connected (prevents duplicate connections)
    const hasAutoConnectedRef = useRef(false);

    // Auto-Connect Model on Start (Only after Auth and devices loaded)
    useEffect(() => {
        // Only auto-connect once: when socket connected, authenticated, and devices loaded
        if (isConnected && isAuthenticated && socketConnected && micDevices.length > 0 && !hasAutoConnectedRef.current) {
            hasAutoConnectedRef.current = true;

            // Trigger Kasa and Printer Discovery
            socket.emit('discover_kasa');
            socket.emit('discover_printers');

            // Connect to model with small delay for socket stability
            const timer = setTimeout(() => {
                const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
                const queryDevice = micDevices.find(d => d.deviceId === selectedMicId);
                const deviceName = queryDevice ? queryDevice.label : null;
                console.log("Auto-connecting to model with device:", deviceName, "Index:", index);

                setStatus('Connecting...');
                socket.emit('start_audio', {
                    device_index: index >= 0 ? index : null,
                    device_name: deviceName,
                    muted: isMuted
                });
            }, 500);
        }
    }, [isConnected, isAuthenticated, socketConnected, micDevices, selectedMicId]);

    useEffect(() => {
        socket.on('audio_data', (data) => setAiAudioData(data.data));
        socket.on('tool_confirmation_request', (data) => {
            console.log("Received Confirmation Request:", data);
            setConfirmationRequest(data);
        });
        socket.on('project_update', (data) => {
            console.log("Project Update:", data.project);
            setCurrentProject(data.project);
            addMessage('System', `Switched to project: ${data.project}`);
        });

        const initHandLandmarker = async () => {
            try {
                console.log("Initializing HandLandmarker...");
                const response = await fetch('/hand_landmarker.task');
                if (!response.ok) {
                    throw new Error(`Failed to fetch model: ${response.status} ${response.statusText}`);
                }
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
                );
                handLandmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: `/hand_landmarker.task`,
                        delegate: "GPU"
                    },
                    runningMode: "VIDEO",
                    numHands: 1
                });
                addMessage('System', 'Hand Tracking Ready');
            } catch (error) {
                console.error("Failed to initialize HandLandmarker:", error);
                addMessage('System', `Hand Tracking Error: ${error.message}`);
            }
        };
        initHandLandmarker();

        return () => {
            socket.off('audio_data');
            socket.off('tool_confirmation_request');
            socket.off('project_update');
            stopMicVisualizer();
            stopVideo();
        };
    }, [socket, addMessage]);

    useEffect(() => {
        if (socket && socket.connected) {
            setStatus('Connected');
            socket.emit('get_settings');
        }
    }, [socket]);

    // Start/Stop Mic Visualizer
    useEffect(() => {
        if (selectedMicId) {
            startMicVisualizer(selectedMicId);
        }
    }, [selectedMicId]);

    const startMicVisualizer = async (deviceId) => {
        stopMicVisualizer();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { deviceId: { exact: deviceId } }
            });

            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 64;

            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
            sourceRef.current.connect(analyserRef.current);

            const updateMicData = () => {
                if (!analyserRef.current) return;
                const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(dataArray);
                setMicAudioData(Array.from(dataArray));
                animationFrameRef.current = requestAnimationFrame(updateMicData);
            };

            updateMicData();
        } catch (err) {
            console.error("Error accessing microphone:", err);
        }
    };

    const stopMicVisualizer = () => {
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        if (sourceRef.current) sourceRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
    };

    const startVideo = async () => {
        try {
            // Request 1080p resolution with selected webcam
            const constraints = {
                video: {
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    aspectRatio: 16 / 9
                }
            };

            // Use selected webcam if available
            if (selectedWebcamId) {
                constraints.video.deviceId = { exact: selectedWebcamId };
            }

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
            }

            // Initialize the transmission canvas
            if (!transmissionCanvasRef.current) {
                transmissionCanvasRef.current = document.createElement('canvas');
                transmissionCanvasRef.current.width = 640;
                transmissionCanvasRef.current.height = 360;
                console.log("Initialized transmission canvas (640x360)");
            }

            setIsVideoOn(true);
            isVideoOnRef.current = true; // Update ref for loop

            console.log("Starting video loop with webcam:", selectedWebcamId || "default");
            requestAnimationFrame(predictWebcam);

        } catch (err) {
            console.error("Error accessing camera:", err);
            addMessage('System', 'Error accessing camera');
        }
    };

    const predictWebcam = () => {
        // Use ref for checking state to avoid closure staleness
        if (!videoRef.current || !canvasRef.current || !isVideoOnRef.current) {
            return;
        }

        // Check if video has valid dimensions to prevent MediaPipe crash
        if (videoRef.current.readyState < 2 || videoRef.current.videoWidth === 0 || videoRef.current.videoHeight === 0) {
            requestAnimationFrame(predictWebcam);
            return;
        }

        // 1. Draw Video to Local Display Canvas (Native Resolution)
        const ctx = canvasRef.current.getContext('2d');

        // Ensure canvas matches video dimensions
        if (canvasRef.current.width !== videoRef.current.videoWidth || canvasRef.current.height !== videoRef.current.videoHeight) {
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
        }

        ctx.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);

        // 2. Send Frame to Backend (Throttled & Resized)
        // Only send if connected
        if (isConnected) {
            // Simple throttle: every 5th frame roughly
            if (frameCountRef.current % 5 === 0) {

                // Use dedicated transmission canvas for resizing
                const transCanvas = transmissionCanvasRef.current;
                if (transCanvas) {
                    const transCtx = transCanvas.getContext('2d');
                    // Draw resized image
                    transCtx.drawImage(videoRef.current, 0, 0, transCanvas.width, transCanvas.height);

                    // Convert resized image to blob
                    transCanvas.toBlob((blob) => {
                        if (blob) {
                            socket.emit('video_frame', { image: blob });
                        }
                    }, 'image/jpeg', 0.6); // Slightly higher compression for speed
                }
            }
        }


        // 3. Hand Tracking
        let startTimeMs = performance.now();
        // Use Ref for toggle check
        if (isHandTrackingEnabledRef.current && handLandmarkerRef.current && videoRef.current.currentTime !== lastVideoTimeRef.current) {
            lastVideoTimeRef.current = videoRef.current.currentTime;
            const results = handLandmarkerRef.current.detectForVideo(videoRef.current, startTimeMs);

            // Log every 100 frames to confirm loop is running
            if (frameCountRef.current % 100 === 0) {
                console.log("Tracking loop running... Last result:", results.landmarks.length > 0 ? "Hand Found" : "No Hand");
            }

            if (results.landmarks && results.landmarks.length > 0) {
                const landmarks = results.landmarks[0];

                // Log on first detection
                if (cursorPos.x === 0 && cursorPos.y === 0) {
                    console.log("First hand detection!", landmarks);
                }

                // Index Finger Tip (8)
                const indexTip = landmarks[8];
                // Thumb Tip (4)
                const thumbTip = landmarks[4];

                // Map to Screen Coords with Sensitivity Scaling
                // Sensitivity: Map center 50% of camera to 100% of screen.
                const SENSITIVITY = cursorSensitivityRef.current;

                // Apply camera flip if enabled (horizontal mirror)
                const rawX = isCameraFlippedRef.current ? (1 - indexTip.x) : indexTip.x;

                // 1. Normalize and Scale X
                let normX = (rawX - 0.5) * SENSITIVITY + 0.5;
                // Clamp to [0, 1]
                normX = Math.max(0, Math.min(1, normX));

                // 2. Normalize and Scale Y
                let normY = (indexTip.y - 0.5) * SENSITIVITY + 0.5;
                normY = Math.max(0, Math.min(1, normY));

                const targetX = (1 - normX) * window.innerWidth;
                const targetY = normY * window.innerHeight;

                // 1. Smoothing (Lerp)
                // Factor 0.2 = smooth but responsive. Lower = smoother/slower.
                const lerpFactor = 0.2;
                smoothedCursorPosRef.current.x = smoothedCursorPosRef.current.x + (targetX - smoothedCursorPosRef.current.x) * lerpFactor;
                smoothedCursorPosRef.current.y = smoothedCursorPosRef.current.y + (targetY - smoothedCursorPosRef.current.y) * lerpFactor;

                let finalX = smoothedCursorPosRef.current.x;
                let finalY = smoothedCursorPosRef.current.y;

                // 2. Snap-to-Button Logic
                const SNAP_THRESHOLD = 50; // Pixels to snap
                const UNSNAP_THRESHOLD = 100; // Pixels to unsnap (Hysteresis)

                if (snapStateRef.current.isSnapped) {
                    // Check if we should unsnap
                    const dist = Math.sqrt(
                        Math.pow(finalX - snapStateRef.current.snapPos.x, 2) +
                        Math.pow(finalY - snapStateRef.current.snapPos.y, 2)
                    );

                    if (dist > UNSNAP_THRESHOLD) {
                        // REMOVE HIGHLIGHT
                        if (snapStateRef.current.element) {
                            snapStateRef.current.element.classList.remove('snap-highlight');
                            snapStateRef.current.element.style.boxShadow = '';
                            snapStateRef.current.element.style.backgroundColor = '';
                            snapStateRef.current.element.style.borderColor = '';
                        }

                        snapStateRef.current = { isSnapped: false, element: null, snapPos: { x: 0, y: 0 } };
                    } else {
                        // Stay snapped
                        finalX = snapStateRef.current.snapPos.x;
                        finalY = snapStateRef.current.snapPos.y;
                    }
                } else {
                    // Check if we should snap
                    // Find all interactive elements
                    const targets = Array.from(document.querySelectorAll('button, input, select, .draggable'));
                    let closest = null;
                    let minDist = Infinity;

                    for (const el of targets) {
                        const rect = el.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        const dist = Math.sqrt(Math.pow(finalX - centerX, 2) + Math.pow(finalY - centerY, 2));

                        if (dist < minDist) {
                            minDist = dist;
                            closest = { el, centerX, centerY };
                        }
                    }

                    if (closest && minDist < SNAP_THRESHOLD) {
                        snapStateRef.current = {
                            isSnapped: true,
                            element: closest.el,
                            snapPos: { x: closest.centerX, y: closest.centerY }
                        };
                        finalX = closest.centerX;
                        finalY = closest.centerY;

                        // SNAP HIGHLIGHT Logic
                        closest.el.classList.add('snap-highlight');
                        // Add some inline style for the glow if class isn't enough (using imperative for speed)
                        closest.el.style.boxShadow = '0 0 20px rgba(34, 211, 238, 0.6)';
                        closest.el.style.backgroundColor = 'rgba(6, 182, 212, 0.2)';
                        closest.el.style.borderColor = 'rgba(34, 211, 238, 1)';
                    }
                }

                // Update Cursor Loop
                setCursorPos({ x: finalX, y: finalY });

                // Trail Logic: Removed per user request

                // Pinch Detection (Distance between Index and Thumb)
                const distance = Math.sqrt(
                    Math.pow(indexTip.x - thumbTip.x, 2) + Math.pow(indexTip.y - thumbTip.y, 2)
                );

                const isPinchNow = distance < 0.05; // Threshold
                if (isPinchNow && !isPinching) {
                    // Click Triggered
                    console.log("Click triggered at", finalX, finalY);

                    // Ripple Effect: Removed per user request

                    const el = document.elementFromPoint(finalX, finalY);
                    if (el) {
                        // Find closest clickable element (button, input, etc.)
                        const clickable = el.closest('button, input, a, [role="button"]');
                        if (clickable && typeof clickable.click === 'function') {
                            clickable.click();
                        } else if (typeof el.click === 'function') {
                            el.click();
                        }
                    }
                }
                setIsPinching(isPinchNow);

                // Fist Detection for Gesture-Based Dragging (Popup Windows Only)
                // Detects if all fingers are folded (tips closer to wrist than MCPs)
                const isFingerFolded = (tipIdx, mcpIdx) => {
                    const tip = landmarks[tipIdx];
                    const mcp = landmarks[mcpIdx];
                    const wrist = landmarks[0];
                    const distTip = Math.sqrt(Math.pow(tip.x - wrist.x, 2) + Math.pow(tip.y - wrist.y, 2));
                    const distMcp = Math.sqrt(Math.pow(mcp.x - wrist.x, 2) + Math.pow(mcp.y - wrist.y, 2));
                    return distTip < distMcp; // Folded if tip is closer
                };

                const isFist = isFingerFolded(8, 5) && isFingerFolded(12, 9) && isFingerFolded(16, 13) && isFingerFolded(20, 17);

                // Get wrist position in screen coordinates (stable reference for fist gesture)
                const wrist = landmarks[0];
                const wristRawX = isCameraFlippedRef.current ? (1 - wrist.x) : wrist.x;
                const wristNormX = Math.max(0, Math.min(1, (wristRawX - 0.5) * SENSITIVITY + 0.5));
                const wristNormY = Math.max(0, Math.min(1, (wrist.y - 0.5) * SENSITIVITY + 0.5));
                const wristScreenX = (1 - wristNormX) * window.innerWidth;
                const wristScreenY = wristNormY * window.innerHeight;

                if (isFist) {
                    if (!activeDragElementRef.current) {
                        // Only check popup windows (draggable elements)
                        const draggableElements = ['cad', 'browser', 'kasa', 'printer'];

                        for (const id of draggableElements) {
                            const el = document.getElementById(id);
                            if (el) {
                                const rect = el.getBoundingClientRect();
                                // Use the cursor position from before fist was made for hit detection
                                if (finalX >= rect.left && finalX <= rect.right && finalY >= rect.top && finalY <= rect.bottom) {
                                    activeDragElementRef.current = id;
                                    bringToFront(id);
                                    // Lock the initial wrist position when starting drag
                                    lastWristPosRef.current = { x: wristScreenX, y: wristScreenY };
                                    break;
                                }
                            }
                        }
                    }

                    if (activeDragElementRef.current) {
                        // Use WRIST movement (not index finger) for stable dragging
                        // The wrist doesn't move when making a fist
                        const dx = wristScreenX - lastWristPosRef.current.x;
                        const dy = wristScreenY - lastWristPosRef.current.y;

                        // Update position only if there's actual movement
                        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
                            updateElementPosition(activeDragElementRef.current, dx, dy);
                        }

                        // Update last wrist position
                        lastWristPosRef.current = { x: wristScreenX, y: wristScreenY };
                    }
                } else {
                    activeDragElementRef.current = null;
                }

                // Sync state for visual feedback (only on change)
                if (activeDragElementRef.current !== lastActiveDragElementRef.current) {
                    setActiveDragElement(activeDragElementRef.current);
                    lastActiveDragElementRef.current = activeDragElementRef.current;
                }

                lastCursorPosRef.current = { x: finalX, y: finalY };

                // Draw Skeleton
                drawSkeleton(ctx, landmarks);
            }

        }

        // 4. FPS Calculation
        const now = performance.now();
        frameCountRef.current++;
        if (now - lastFrameTimeRef.current >= 1000) {
            setFps(frameCountRef.current);
            frameCountRef.current = 0;
            lastFrameTimeRef.current = now;
        }

        if (isVideoOnRef.current) {
            requestAnimationFrame(predictWebcam);
        }
    };

    const drawSkeleton = (ctx, landmarks) => {
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 2;

        // Connections
        const connections = HandLandmarker.HAND_CONNECTIONS;
        for (const connection of connections) {
            const start = landmarks[connection.start];
            const end = landmarks[connection.end];
            ctx.beginPath();
            ctx.moveTo(start.x * canvasRef.current.width, start.y * canvasRef.current.height);
            ctx.lineTo(end.x * canvasRef.current.width, end.y * canvasRef.current.height);
            ctx.stroke();
        }
    };

    const stopVideo = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            videoRef.current.srcObject.getTracks().forEach(track => track.stop());
            videoRef.current.srcObject = null;
        }
        setIsVideoOn(false);
        isVideoOnRef.current = false; // Update ref
        setFps(0);
    };

    const toggleVideo = () => {
        if (isVideoOn) {
            stopVideo();
        } else {
            startVideo();
        }
    };

    const togglePower = () => {
        if (isConnected) {
            socket.emit('stop_audio');
            setIsConnected(false);
            setIsMuted(false); // Reset mute state
        } else {
            const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
            socket.emit('start_audio', { device_index: index >= 0 ? index : null });
            setIsConnected(true);
            setIsMuted(false); // Start unmuted
        }
    };

    const toggleMute = () => {
        if (!isConnected) return; // Can't mute if not connected

        if (isMuted) {
            socket.emit('resume_audio');
            setIsMuted(false);
        } else {
            socket.emit('pause_audio');
            setIsMuted(true);
        }
    };

    const handleMinimize = () => atlasBridge.send('window-minimize');
    const handleMaximize = () => atlasBridge.send('window-maximize');

    // Close Application - memory is now actively saved to project, no prompt needed
    const handleCloseRequest = () => {
        // Emit shutdown signal to backend for graceful shutdown
        // Use volatile emit with timeout fallback to ensure window closes even if server is unresponsive
        const closeWindow = () => atlasBridge.send('window-close');

        if (socket.connected) {
            console.log('[APP] Sending shutdown signal to backend...');
            socket.emit('shutdown', {}, (ack) => {
                // This callback may not be called if server uses os._exit
                console.log('[APP] Shutdown acknowledged');
                closeWindow();
            });
            // Fallback: close after 500ms if ack doesn't come back
            setTimeout(closeWindow, 500);
        } else {
            // Socket not connected, just close
            closeWindow();
        }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const textContent = event.target.result;
                // Just send the text content directly
                if (typeof textContent === 'string' && textContent.length > 0) {
                    socket.emit('upload_memory', { memory: textContent });
                    addMessage('System', 'Uploading memory...');
                } else {
                    addMessage('System', 'Empty or invalid memory file');
                }
            } catch (err) {
                console.error("Error reading file:", err);
                addMessage('System', 'Error reading memory file');
            }
        };
        reader.readAsText(file);
    };

    // handleCancelClose removed - no longer using memory prompt

    const handleConfirmTool = () => {
        if (confirmationRequest) {
            socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: true });
            setConfirmationRequest(null);
        }
    };

    const handleDenyTool = () => {
        if (confirmationRequest) {
            socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: false });
            setConfirmationRequest(null);
        }
    };

    // Calculate Average Audio Amplitude for Background Pulse
    const audioAmp = aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255;

    const toggleKasaWindow = () => {
        if (!showKasaWindow) {
            // Maybe trigger discover instantly?
            if (kasaDevices.length === 0) socket.emit('discover_kasa');
        }
        setShowKasaWindow(!showKasaWindow);
    };

    const togglePrinterWindow = () => {
        setShowPrinterWindow(!showPrinterWindow);
    };



    return (
        <div className="h-screen w-screen bg-black text-cyan-100 font-mono overflow-hidden flex flex-col relative selection:bg-cyan-900 selection:text-white">

            {/* --- PREMIUM UI LAYER --- */}

            {/* --- PREMIUM UI LAYER --- */}

            {/* --- PREMIUM UI LAYER --- */}

            {/* Logic: Show AuthLock if we are NOT authenticated AND (Lock Screen is visible OR Auth is Enabled) 
                Actually, simpler: isLockScreenVisible is the source of truth for visibility.
                We set isLockScreenVisible = true via socket if auth is required.
             */}

            {isLockScreenVisible && (
                <AuthLock
                    socket={socket}
                    onAuthenticated={() => setIsAuthenticated(true)}
                    onAnimationComplete={() => setIsLockScreenVisible(false)}
                />
            )}

            {/* --- PREMIUM UI LAYER --- */}

            {/* Hand Cursor - Only show if tracking is enabled */}
            {isVideoOn && isHandTrackingEnabled && (
                <div
                    className={`fixed w-6 h-6 border-2 rounded-full pointer-events-none z-[100] transition-transform duration-75 ${isPinching ? 'bg-cyan-400 border-cyan-400 scale-75 shadow-[0_0_15px_rgba(34,211,238,0.8)]' : 'border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.3)]'}`}
                    style={{
                        left: cursorPos.x,
                        top: cursorPos.y,
                        transform: 'translate(-50%, -50%)'
                    }}
                >
                    {/* Center Dot for precision */}
                    <div className="absolute top-1/2 left-1/2 w-1 h-1 bg-white rounded-full -translate-x-1/2 -translate-y-1/2" />
                </div>
            )}

            {/* Background Grid/Effects - ALIVE BACKGROUND (Fixed: Static opacity) */}
            <div
                className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 via-black to-black z-0 pointer-events-none"
                style={{ opacity: 0.6 }}
            ></div>
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 z-0 pointer-events-none mix-blend-overlay"></div>

            {/* Ambient Glow (Fixed: Static) */}
            <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-900/10 rounded-full blur-[120px] pointer-events-none"
            />

            {/* Top Bar (Draggable) */}
            <div className="z-50 flex items-center justify-between p-2 border-b border-white/[0.08] bg-black/30 backdrop-blur-xl shadow-[0_4px_24px_rgba(0,0,0,0.3)] select-none sticky top-0" style={{ WebkitAppRegion: 'drag' }}>
                <div className="flex items-center gap-4 pl-2">
                    <h1 className="font-display text-xl font-semibold tracking-[0.25em] text-cyan-400 drop-shadow-[0_0_12px_rgba(34,211,238,0.5)]">
                        A.T.L.A.S.
                    </h1>
                    <div className="text-[10px] text-cyan-700 border border-cyan-900 px-1 rounded">
                        V2.0.0
                    </div>
                    {/* FPS Counter */}
                    {isVideoOn && (
                        <div className="text-[10px] text-green-500 border border-green-900 px-1 rounded ml-2">
                            FPS: {fps}
                        </div>
                    )}
                    {/* Connected Printers Count */}
                    {printerCount > 0 && (
                        <div className="flex items-center gap-1.5 text-[10px] text-green-400 border border-green-500/30 bg-green-500/10 px-2 py-0.5 rounded ml-2">
                            <Printer size={10} className="text-green-400" />
                            <span>{printerCount} Printer{printerCount !== 1 ? 's' : ''}</span>
                        </div>
                    )}
                    {/* Connected Smart Devices Count */}
                    {kasaDevices.length > 0 && (
                        <div className="flex items-center gap-1.5 text-[10px] text-yellow-400 border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 rounded ml-2">
                            <span>💡</span>
                            <span>{kasaDevices.length} Device{kasaDevices.length !== 1 ? 's' : ''}</span>
                        </div>
                    )}
                </div>

                {/* Top Visualizer (User Mic) */}
                <div className="flex-1 flex justify-center mx-4">
                    <TopAudioBar audioData={micAudioData} />
                </div>

                <div className="flex items-center gap-2 pr-2" style={{ WebkitAppRegion: 'no-drag' }}>
                    {/* Live Clock */}
                    <div className="flex items-center gap-1.5 text-[11px] text-cyan-300/70 font-mono px-2">
                        <Clock size={12} className="text-cyan-500/50" />
                        <span>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <button onClick={handleMinimize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <Minus size={18} />
                    </button>
                    <button onClick={handleMaximize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <div className="w-[14px] h-[14px] border-2 border-current rounded-[2px]" />
                    </button>
                    <button onClick={handleCloseRequest} className="p-1 hover:bg-red-900/50 rounded text-red-500 transition-colors">
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 relative z-10 flex flex-col items-center justify-center">
                {/* Central Visualizer (AI Audio) */}
                <div
                    id="visualizer"
                    className={`absolute flex items-center justify-center transition-all duration-200 glass-panel overflow-visible
                        ${isModularMode ? (activeDragElement === 'visualizer' ? 'ring-2 ring-green-500 bg-green-500/10' : 'ring-1 ring-yellow-500/30 bg-yellow-500/5') + ' rounded-2xl pointer-events-auto' : 'rounded-2xl pointer-events-none'}
                    `}
                    style={{
                        left: elementPositions.visualizer.x,
                        top: elementPositions.visualizer.y,
                        transform: 'translate(-50%, -50%)',
                        width: elementSizes.visualizer.w,
                        height: elementSizes.visualizer.h
                    }}
                    onMouseDown={(e) => handleMouseDown(e, 'visualizer')}
                >
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10"></div>
                    <div className="relative z-20 w-full h-full">
                        <Suspense fallback={<Visualizer audioData={aiAudioData} isListening={isConnected && !isMuted} intensity={audioAmp} width={elementSizes.visualizer.w} height={elementSizes.visualizer.h} />}>
                            <Visualizer3D
                                audioData={aiAudioData}
                                isListening={isConnected && !isMuted}
                                intensity={audioAmp}
                                width={elementSizes.visualizer.w}
                                height={elementSizes.visualizer.h}
                            />
                        </Suspense>
                    </div>
                    {isModularMode && <div className={`absolute top-2 right-2 text-xs font-bold tracking-widest z-20 ${activeDragElement === 'visualizer' ? 'text-green-500' : 'text-yellow-500/50'}`}>VISUALIZER</div>}
                </div>

                {/* Video Feed Overlay */}
                {/* Floating Project Label */}
                <div className="absolute top-[70px] left-1/2 -translate-x-1/2 font-display text-cyan-500 text-xs tracking-widest pointer-events-none z-50 bg-black/50 px-2 py-1 rounded backdrop-blur-sm border border-cyan-500/20">
                    PROJECT: {currentProject?.toUpperCase()}
                </div>

                <div
                    id="video"
                    className={`fixed bottom-4 right-4 transition-all duration-200 
                        ${isVideoOn ? 'opacity-100' : 'opacity-0 pointer-events-none'} 
                        backdrop-blur-md bg-black/40 border border-white/10 shadow-xl rounded-xl
                    `}
                    style={{ zIndex: 20 }}
                >
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay"></div>
                    {/* Compact Display Container (1080p Source) */}
                    <div className="relative border border-cyan-500/30 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(6,182,212,0.1)] w-80 aspect-video bg-black/80">
                        {/* Hidden Video Element (Source) */}
                        <video ref={videoRef} autoPlay muted className="absolute inset-0 w-full h-full object-cover opacity-0" />

                        <div className="absolute top-2 left-2 text-[10px] text-cyan-400 bg-black/60 backdrop-blur px-2 py-0.5 rounded border border-cyan-500/20 z-10 font-bold tracking-wider">CAM_01</div>

                        {/* Canvas for Displaying Video + Skeleton (Ensures overlap) */}
                        <canvas
                            ref={canvasRef}
                            className="absolute inset-0 w-full h-full opacity-80 mirrored-video"
                            style={{ transform: 'scaleX(-1)' }}
                        />
                    </div>
                </div>

                {/* Settings Modal - Moved outside Video so it shows independently */}
                {showSettings && (
                    <SettingsWindow
                        socket={socket}
                        micDevices={micDevices}
                        speakerDevices={speakerDevices}
                        webcamDevices={webcamDevices}
                        selectedMicId={selectedMicId}
                        setSelectedMicId={setSelectedMicId}
                        selectedSpeakerId={selectedSpeakerId}
                        setSelectedSpeakerId={setSelectedSpeakerId}
                        selectedWebcamId={selectedWebcamId}
                        setSelectedWebcamId={setSelectedWebcamId}
                        cursorSensitivity={cursorSensitivity}
                        setCursorSensitivity={setCursorSensitivity}
                        isCameraFlipped={isCameraFlipped}
                        setIsCameraFlipped={setIsCameraFlipped}
                        handleFileUpload={handleFileUpload}
                        onClose={() => setShowSettings(false)}
                    />
                )}

                {/* CAD Window Overlay - Moved outside of Video so it can show independently */}
                {showCadWindow && (
                    <DraggableWindow
                        id="cad"
                        position={elementPositions.cad}
                        size={elementSizes.cad}
                        zIndex={getZIndex('cad')}
                        onMouseDown={handleMouseDown}
                        activeDragElement={activeDragElement}
                        title="CAD PROTOTYPE"
                        onClose={() => setShowCadWindow(false)}
                    >
                        <CadWindow
                            data={cadData}
                            thoughts={cadThoughts}
                            retryInfo={cadRetryInfo}
                            onClose={() => setShowCadWindow(false)}
                            socket={socket}
                        />
                    </DraggableWindow>
                )}


                {/* Browser Window Overlay */}
                {showBrowserWindow && (
                    <DraggableWindow
                        id="browser"
                        position={elementPositions.browser}
                        size={elementSizes.browser}
                        zIndex={getZIndex('browser')}
                        onMouseDown={handleMouseDown}
                        activeDragElement={activeDragElement}
                        onClose={() => setShowBrowserWindow(false)}
                        renderHeader={false}
                    >
                        <BrowserWindow
                            imageSrc={browserData.image}
                            logs={browserData.logs}
                            onClose={() => setShowBrowserWindow(false)}
                            socket={socket}
                        />
                    </DraggableWindow>
                )}


                {/* Chat Module */}
                <ChatModule
                    messages={messages}
                    inputValue={inputValue}
                    setInputValue={setInputValue}
                    handleSend={handleSend}
                    isModularMode={isModularMode}
                    activeDragElement={activeDragElement}
                    position={elementPositions.chat}
                    width={elementSizes.chat.w}
                    height={elementSizes.chat.h}
                    onMouseDown={(e) => handleMouseDown(e, 'chat')}
                    isConnected={isConnected}
                    isMuted={isMuted}
                />

                {/* Footer Controls / Tools Module */}
                <div className="z-20 flex justify-center pb-10 pointer-events-none">
                    <ToolsModule
                        isConnected={isConnected}
                        isMuted={isMuted}
                        isVideoOn={isVideoOn}
                        isHandTrackingEnabled={isHandTrackingEnabled}
                        showSettings={showSettings}
                        onTogglePower={togglePower}
                        onToggleMute={toggleMute}
                        onToggleVideo={toggleVideo}
                        onToggleSettings={() => setShowSettings(!showSettings)}
                        onToggleHand={() => setIsHandTrackingEnabled(!isHandTrackingEnabled)}
                        onToggleKasa={toggleKasaWindow}
                        showKasaWindow={showKasaWindow}
                        onTogglePrinter={togglePrinterWindow}
                        showPrinterWindow={showPrinterWindow}
                        onToggleCad={() => setShowCadWindow(!showCadWindow)}
                        showCadWindow={showCadWindow}
                        onToggleBrowser={() => setShowBrowserWindow(!showBrowserWindow)}
                        showBrowserWindow={showBrowserWindow}
                        activeDragElement={activeDragElement}
                        position={elementPositions.tools}
                        onMouseDown={(e) => handleMouseDown(e, 'tools')}
                    />
                </div>

                {/* Kasa Window */}
                {showKasaWindow && (
                    <KasaWindow
                        socket={socket}
                        position={elementPositions.kasa}
                        activeDragElement={activeDragElement}
                        setActiveDragElement={setActiveDragElement}
                        devices={kasaDevices}
                        onClose={() => setShowKasaWindow(false)}
                        onMouseDown={(e) => handleMouseDown(e, 'kasa')}
                        zIndex={getZIndex('kasa')}
                    />
                )}

                {/* Printer Window */}
                {showPrinterWindow && (
                    <PrinterWindow
                        socket={socket}
                        onClose={() => setShowPrinterWindow(false)}
                        position={elementPositions.printer}
                        onMouseDown={(e) => handleMouseDown(e, 'printer')}
                        activeDragElement={activeDragElement}
                        setActiveDragElement={setActiveDragElement}
                        zIndex={getZIndex('printer')}
                    />
                )}

                {/* Memory Prompt removed - memory is now actively saved to project */}

                {/* Tool Confirmation Modal */}
                <ConfirmationPopup
                    request={confirmationRequest}
                    onConfirm={handleConfirmTool}
                    onDeny={handleDenyTool}
                />
            </div>
        </div>
    );
}

export default App;
