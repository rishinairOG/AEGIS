import { useState, useEffect } from 'react';

/**
 * CAD window state and socket handlers for cad_data, cad_status, cad_thought, request_print_window.
 * @param {object} socket - Socket.IO client
 * @param {function} setElementPositions - From layout (optional, for auto-positioning)
 * @param {function} clampToViewport - From layout (optional)
 */
export function useCadState(socket, setElementPositions, clampToViewport) {
    const [cadData, setCadData] = useState(null);
    const [cadThoughts, setCadThoughts] = useState('');
    const [cadRetryInfo, setCadRetryInfo] = useState({ attempt: 1, maxAttempts: 3, error: null });
    const [showCadWindow, setShowCadWindow] = useState(false);

    useEffect(() => {
        if (!socket) return;
        const onCadData = (data) => {
            setCadData(data);
            setCadThoughts('');
            setShowCadWindow(true);
            if (setElementPositions && clampToViewport) {
                const size = { w: 400, h: 400 };
                const clamped = clampToViewport({ x: window.innerWidth / 2 + 300, y: window.innerHeight / 2 }, size);
                setElementPositions(prev => ({ ...prev, cad: clamped }));
            }
        };
        const onCadStatus = (data) => {
            if (data.attempt) {
                setCadRetryInfo({ attempt: data.attempt, maxAttempts: data.max_attempts || 3, error: data.error });
            }
            if (data.status === 'generating' || data.status === 'retrying') {
                setCadData({ format: 'loading' });
                setShowCadWindow(true);
                if (data.status === 'generating' && data.attempt === 1) setCadThoughts('');
                if (setElementPositions && clampToViewport) {
                    const size = { w: 400, h: 400 };
                    const clamped = clampToViewport({ x: window.innerWidth / 2 + 150, y: window.innerHeight / 2 }, size);
                    setElementPositions(prev => ({ ...prev, cad: clamped }));
                }
            } else if (data.status === 'failed') {
                setCadData({ format: 'loading' });
            }
        };
        const onCadThought = (data) => setCadThoughts(prev => prev + data.text);
        socket.on('cad_data', onCadData);
        socket.on('cad_status', onCadStatus);
        socket.on('cad_thought', onCadThought);
        return () => {
            socket.off('cad_data', onCadData);
            socket.off('cad_status', onCadStatus);
            socket.off('cad_thought', onCadThought);
        };
    }, [socket, setElementPositions, clampToViewport]);

    return { cadData, setCadData, cadThoughts, setCadThoughts, cadRetryInfo, setCadRetryInfo, showCadWindow, setShowCadWindow };
}
