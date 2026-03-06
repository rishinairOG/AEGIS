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

    // Status messages that are user-relevant (shown in chat). Others (Kasa/printer discovery, etc.) are not.
    const STATUS_CHAT_WHITELIST = [
        'A.E.G.I.S. Started',
        'A.E.G.I.S. Stopped',
        'Model Connected',
        'Ready for voice',
        'Listening...',
    ];
    const isChatRelevantStatus = (msg) =>
        STATUS_CHAT_WHITELIST.some((t) => msg && msg.includes(t));

    useEffect(() => {
        if (!socket) return;
        socket.on('status', (data) => {
            if (data.msg === 'A.E.G.I.S. Started') setStatus('Model Connected');
            else if (data.msg === 'A.E.G.I.S. Stopped') setStatus('Connected');
            if (isChatRelevantStatus(data.msg)) addMessage('System', data.msg);
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
