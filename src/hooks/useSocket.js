import { useState, useEffect } from 'react';
import io from 'socket.io-client';

/**
 * Socket connection and connection state.
 * @param {string} url - Backend URL (e.g. 'http://localhost:8000')
 * @returns {{ socket: object, status: string, setStatus: function, socketConnected: boolean }}
 */
export function useSocket(url = 'http://localhost:8000') {
    const [socket] = useState(() => io(url));
    const [status, setStatus] = useState('Disconnected');
    const [socketConnected, setSocketConnected] = useState(socket.connected);

    useEffect(() => {
        socket.on('connect', () => {
            setStatus('Connected');
            setSocketConnected(true);
            socket.emit('get_settings');
        });
        socket.on('disconnect', () => {
            setStatus('Disconnected');
            setSocketConnected(false);
        });
        return () => {
            socket.off('connect');
            socket.off('disconnect');
        };
    }, [socket]);

    return { socket, status, setStatus, socketConnected };
}
