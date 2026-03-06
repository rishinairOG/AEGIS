import { useState, useEffect } from 'react';

/**
 * Auth and lock screen state. Subscribes to auth_status and settings (face_auth_enabled, camera_flipped).
 * @param {object} socket - Socket.IO client
 * @param {{ setCameraFlipped?: function }} opts - Optional callbacks for settings (e.g. camera_flipped for hand tracking)
 */
export function useAuth(socket, opts = {}) {
    const { setCameraFlipped } = opts;
    const [isAuthenticated, setIsAuthenticated] = useState(() => localStorage.getItem('face_auth_enabled') !== 'true');
    const [isLockScreenVisible, setIsLockScreenVisible] = useState(() => localStorage.getItem('face_auth_enabled') === 'true');
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(() => localStorage.getItem('face_auth_enabled') === 'true');

    useEffect(() => {
        if (!socket) return;
        socket.on('auth_status', (data) => {
            setIsAuthenticated(data.authenticated);
            if (!data.authenticated) setIsLockScreenVisible(true);
        });
        socket.on('settings', (settings) => {
            if (settings && typeof settings.face_auth_enabled !== 'undefined') {
                setFaceAuthEnabled(settings.face_auth_enabled);
                localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
            }
            if (typeof settings?.camera_flipped !== 'undefined' && setCameraFlipped) {
                setCameraFlipped(settings.camera_flipped);
            }
        });
        return () => {
            socket.off('auth_status');
            socket.off('settings');
        };
    }, [socket, setCameraFlipped]);

    return { isAuthenticated, setIsAuthenticated, isLockScreenVisible, setIsLockScreenVisible, faceAuthEnabled, setFaceAuthEnabled };
}
