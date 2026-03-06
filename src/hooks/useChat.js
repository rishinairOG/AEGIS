import { useState, useCallback, useEffect } from 'react';

/**
 * Chat messages, input, addMessage, handleSend. Subscribes to transcription, status, error.
 * @param {object} socket - Socket.IO client
 * @param {function} setStatus - From useSocket
 */
export function useChat(socket, setStatus) {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');

    const addMessage = useCallback((sender, text) => {
        setMessages(prev => [...prev, { sender, text, time: new Date().toLocaleTimeString() }]);
    }, []);

    useEffect(() => {
        if (!socket) return;
        socket.on('status', (data) => {
            addMessage('System', data.msg);
            if (data.msg === 'A.E.G.I.S. Started') setStatus('Model Connected');
            else if (data.msg === 'A.E.G.I.S. Stopped') setStatus('Connected');
        });
        socket.on('transcription', (data) => {
            setMessages(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.sender === data.sender) {
                    return [
                        ...prev.slice(0, -1),
                        { ...lastMsg, text: lastMsg.text + data.text }
                    ];
                }
                return [...prev, { sender: data.sender, text: data.text, time: new Date().toLocaleTimeString() }];
            });
        });
        socket.on('error', (data) => {
            addMessage('System', `Error: ${data.msg}`);
        });
        return () => {
            socket.off('status');
            socket.off('transcription');
            socket.off('error');
        };
    }, [socket, addMessage, setStatus]);

    const handleSend = useCallback((e) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            socket.emit('user_input', { text: inputValue });
            addMessage('You', inputValue);
            setInputValue('');
        }
    }, [socket, inputValue, addMessage]);

    return { messages, setMessages, inputValue, setInputValue, addMessage, handleSend };
}
