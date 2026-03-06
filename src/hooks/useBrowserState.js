import { useState, useEffect } from 'react';

/**
 * Browser agent frame and logs. Subscribes to browser_frame.
 * @param {object} socket - Socket.IO client
 * @param {function} setElementPositions - From layout (optional)
 * @param {function} clampToViewport - From layout (optional)
 */
export function useBrowserState(socket, setElementPositions, clampToViewport) {
    const [browserData, setBrowserData] = useState({ image: null, logs: [] });
    const [showBrowserWindow, setShowBrowserWindow] = useState(false);

    useEffect(() => {
        if (!socket) return;
        socket.on('browser_frame', (data) => {
            setBrowserData(prev => ({
                image: data.image,
                logs: [...(prev.logs || []), data.log].filter(Boolean).slice(-50)
            }));
            setShowBrowserWindow(true);
            if (setElementPositions && clampToViewport) {
                const size = { w: 550, h: 380 };
                const clamped = clampToViewport({ x: window.innerWidth / 2 - 200, y: window.innerHeight / 2 }, size);
                setElementPositions(prev => ({ ...prev, browser: clamped }));
            }
        });
        return () => socket.off('browser_frame');
    }, [socket, setElementPositions, clampToViewport]);

    return { browserData, setBrowserData, showBrowserWindow, setShowBrowserWindow };
}
