import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

function roleStyles(sender) {
  // Strip non-letters so the dotted "A.T.L.A.S." sender string normalizes to "atlas"
  const s = (sender || '').toLowerCase().replace(/[^a-z]/g, '');
  if (s === 'user' || s === 'you') return { border: 'border-l-cyan-500/60', label: 'text-cyan-400', bg: 'bg-cyan-500/5' };
  if (s === 'atlas' || s === 'model') return { border: 'border-l-accent-magenta/70', label: 'text-accent-magenta', bg: 'bg-accent-magenta/5' };
  return { border: 'border-l-amber-500/50', label: 'text-accent-amber', bg: 'bg-accent-amber/5' };
}

const VOICE_HINTS = [
    '"Generate a small box"',
    '"Turn on the lights"',
    '"What can you do?"',
];

const ChatModule = ({
    messages,
    inputValue,
    setInputValue,
    handleSend,
    isModularMode,
    activeDragElement,
    position,
    width = 672, // default max-w-2xl
    height,
    onMouseDown,
    isConnected = false,
    isMuted = true,
}) => {
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    return (
        <div
            id="chat"
            onMouseDown={onMouseDown}
            className={`absolute px-6 py-4 pointer-events-auto transition-all duration-200 glass-panel rounded-2xl
            ${isModularMode ? (activeDragElement === 'chat' ? 'ring-2 ring-green-500' : 'ring-1 ring-yellow-500/30') : ''}
        `}
            style={{
                left: position.x,
                top: position.y,
                transform: 'translate(-50%, 0)', // Aligned top-center
                width: width,
                height: height
            }}
        >
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay"></div>

            <div
                className="flex flex-col gap-3 overflow-y-auto mb-4 scrollbar-hide mask-image-gradient relative z-10"
                style={{ height: height ? `calc(${height}px - 70px)` : '15rem' }}
            >
                {messages.slice(-5).map((msg, i) => {
                  const style = roleStyles(msg.sender);
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25 }}
                      className={`text-sm border-l-2 pl-3 py-1.5 rounded-r ${style.border} ${style.bg}`}
                    >
                      <span className="font-mono text-xs opacity-60">[{msg.time}]</span>{' '}
                      <span className={`font-display font-semibold text-xs tracking-wider ${style.label}`}>{msg.sender}</span>
                      <div className="text-gray-300 mt-1 leading-relaxed">{msg.text}</div>
                    </motion.div>
                  );
                })}
                <div ref={messagesEndRef} />
            </div>

            <div className="flex flex-col gap-1.5 relative z-10 absolute bottom-4 left-6 right-6">
                {isConnected && (
                    <p className="text-[10px] text-cyan-500/70 font-mono">
                        {isMuted ? 'Unmute the mic (toolbar) to use voice.' : 'Listening — try saying: ' + VOICE_HINTS.join(' · ')}
                    </p>
                )}
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleSend}
                    placeholder={isConnected && !isMuted ? "Or type here and press Enter..." : "Type a command and press Enter..."}
                    className="flex-1 bg-black/40 border border-cyan-700/30 rounded-lg p-3 text-cyan-50 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder-cyan-800/50 backdrop-blur-sm"
                />
            </div>
            {isModularMode && <div className={`absolute -top-6 left-0 text-xs font-bold tracking-widest ${activeDragElement === 'chat' ? 'text-green-500' : 'text-yellow-500/50'}`}>CHAT MODULE</div>}
        </div>
    );
};

export default ChatModule;
