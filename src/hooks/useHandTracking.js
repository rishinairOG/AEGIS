import { useState, useRef, useEffect } from 'react';

/**
 * Hand tracking state and refs for cursor, pinch, sensitivity, camera flip.
 * Does not include predictWebcam/startVideo/stopVideo; those remain in the component for now.
 */
export function useHandTracking() {
    const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
    const [isPinching, setIsPinching] = useState(false);
    const [isHandTrackingEnabled, setIsHandTrackingEnabled] = useState(false);
    const [cursorSensitivity, setCursorSensitivity] = useState(2.0);
    const [isCameraFlipped, setIsCameraFlipped] = useState(false);

    const isHandTrackingEnabledRef = useRef(false);
    const cursorSensitivityRef = useRef(2.0);
    const isCameraFlippedRef = useRef(false);
    const handLandmarkerRef = useRef(null);
    const cursorTrailRef = useRef([]);
    const lastCursorPosRef = useRef({ x: 0, y: 0 });
    const lastWristPosRef = useRef({ x: 0, y: 0 });
    const smoothedCursorPosRef = useRef({ x: 0, y: 0 });
    const snapStateRef = useRef({ isSnapped: false, element: null, snapPos: { x: 0, y: 0 } });

    useEffect(() => {
        isHandTrackingEnabledRef.current = isHandTrackingEnabled;
        cursorSensitivityRef.current = cursorSensitivity;
        isCameraFlippedRef.current = isCameraFlipped;
    }, [isHandTrackingEnabled, cursorSensitivity, isCameraFlipped]);

    return {
        cursorPos,
        setCursorPos,
        isPinching,
        setIsPinching,
        isHandTrackingEnabled,
        setIsHandTrackingEnabled,
        cursorSensitivity,
        setCursorSensitivity,
        isCameraFlipped,
        setIsCameraFlipped,
        handLandmarkerRef,
        cursorTrailRef,
        lastCursorPosRef,
        lastWristPosRef,
        smoothedCursorPosRef,
        snapStateRef,
        isHandTrackingEnabledRef,
        cursorSensitivityRef,
        isCameraFlippedRef
    };
}
