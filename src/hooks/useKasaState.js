import { useState, useEffect } from 'react';

/**
 * Kasa devices and window visibility. Subscribes to kasa_devices, kasa_update.
 * @param {object} socket - Socket.IO client
 */
export function useKasaState(socket) {
    const [kasaDevices, setKasaDevices] = useState([]);
    const [showKasaWindow, setShowKasaWindow] = useState(false);

    useEffect(() => {
        if (!socket) return;
        socket.on('kasa_devices', (devices) => setKasaDevices(devices || []));
        socket.on('kasa_update', (data) => {
            setKasaDevices(prev => prev.map(d =>
                d.ip === data.ip
                    ? {
                        ...d,
                        is_on: data.is_on !== null ? data.is_on : d.is_on,
                        brightness: data.brightness !== null ? data.brightness : d.brightness
                    }
                    : d
            ));
        });
        return () => {
            socket.off('kasa_devices');
            socket.off('kasa_update');
        };
    }, [socket]);

    return { kasaDevices, setKasaDevices, showKasaWindow, setShowKasaWindow };
}
