import React, { useEffect, useState, useCallback } from 'react';
import { X, Search, Brain, RefreshCw } from 'lucide-react';

// HippoMem interaction dicts aren't a fixed schema, so pull text defensively
// from the most likely key names and fall back to a JSON preview.
function pickText(obj, keys) {
    for (const k of keys) {
        if (obj && typeof obj[k] === 'string' && obj[k].trim()) return obj[k];
    }
    return null;
}

function InteractionRow({ item }) {
    const user = pickText(item, ['user_message', 'user', 'query', 'input', 'message']);
    const ai = pickText(item, ['assistant_response', 'assistant', 'response', 'output', 'answer']);
    const when = pickText(item, ['timestamp', 'created_at', 'time', 'date']);

    if (!user && !ai) {
        return (
            <div className="text-[11px] text-cyan-700 font-mono border-l-2 border-cyan-900/50 pl-2 py-1 break-words">
                {JSON.stringify(item)}
            </div>
        );
    }
    return (
        <div className="border-l-2 border-accent-magenta/40 pl-2 py-1.5">
            {when && <div className="text-[9px] text-cyan-800 mb-0.5">{String(when)}</div>}
            {user && <div className="text-[12px] text-cyan-300"><span className="text-cyan-600">You: </span>{user}</div>}
            {ai && <div className="text-[12px] text-accent-magenta/90"><span className="text-accent-magenta/60">ATLAS: </span>{ai}</div>}
        </div>
    );
}

const MemoryWindow = ({ socket, onClose, position, onMouseDown, activeDragElement, zIndex = 40 }) => {
    const [data, setData] = useState({ enabled: true, interactions: [], stats: {}, traits: {} });
    const [query, setQuery] = useState('');
    const [searchResult, setSearchResult] = useState(null);
    const [loading, setLoading] = useState(true);
    const [searching, setSearching] = useState(false);

    const fetchMemory = useCallback(() => {
        if (!socket) return;
        setLoading(true);
        socket.emit('memory_fetch');
    }, [socket]);

    useEffect(() => {
        if (!socket) return;
        const onData = (d) => { setData(d || {}); setLoading(false); };
        const onSearch = (r) => { setSearchResult(r); setSearching(false); };
        socket.on('memory_data', onData);
        socket.on('memory_search_result', onSearch);
        fetchMemory();
        return () => {
            socket.off('memory_data', onData);
            socket.off('memory_search_result', onSearch);
        };
    }, [socket, fetchMemory]);

    const runSearch = () => {
        if (!socket || !query.trim()) return;
        setSearching(true);
        setSearchResult(null);
        socket.emit('memory_search', { query: query.trim() });
    };

    const traitEntries = data.traits ? Object.entries(data.traits).filter(([, v]) => v && (Array.isArray(v) ? v.length : true)) : [];

    return (
        <div
            id="memory"
            onMouseDown={onMouseDown}
            className={`absolute flex flex-col rounded-xl backdrop-blur-md bg-black/70 border border-accent-magenta/30 transition-all duration-200 select-none text-cyan-300
                ${activeDragElement === 'memory' ? 'ring-2 ring-accent-magenta shadow-[0_0_30px_rgba(217,70,239,0.3)]' : 'shadow-[0_0_20px_rgba(6,182,212,0.1)]'}`}
            style={{
                left: position?.x ?? 0,
                top: position?.y ?? 0,
                width: '420px',
                height: '440px',
                transform: 'translate(-50%, -50%)',
                zIndex,
                WebkitAppRegion: 'no-drag',
            }}
        >
            {/* Header (drag handle) */}
            <div data-drag-handle className="flex items-center justify-between px-3 py-2 border-b border-white/[0.08] cursor-grab active:cursor-grabbing">
                <div className="flex items-center gap-2 text-accent-magenta">
                    <Brain size={16} />
                    <span className="font-display text-sm tracking-widest">MEMORY</span>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={fetchMemory} title="Refresh" className="text-cyan-600 hover:text-cyan-300">
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button onClick={onClose} className="text-cyan-600 hover:text-red-400"><X size={16} /></button>
                </div>
            </div>

            {data.enabled === false ? (
                <div className="flex-1 flex items-center justify-center text-cyan-700 text-sm p-4 text-center">
                    Long-term memory is disabled. Enable it in settings and restart.
                </div>
            ) : (
                <>
                    {/* Search */}
                    <div className="p-2 border-b border-white/[0.06]">
                        <div className="flex items-center gap-1.5 bg-black/40 border border-cyan-900 rounded px-2 py-1">
                            <Search size={13} className="text-cyan-600" />
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && runSearch()}
                                placeholder="Search memory (e.g. what do you know about me?)"
                                className="flex-1 bg-transparent text-[12px] text-cyan-200 outline-none placeholder-cyan-800"
                            />
                            <button onClick={runSearch} className="text-[10px] text-accent-magenta hover:text-accent-magenta/70 px-1">
                                {searching ? '…' : 'GO'}
                            </button>
                        </div>
                        {searchResult && (
                            <div className="mt-2 text-[12px] text-cyan-200 bg-accent-magenta/5 border border-accent-magenta/20 rounded p-2 whitespace-pre-wrap max-h-40 overflow-y-auto">
                                {searchResult.context || 'No relevant memories found.'}
                            </div>
                        )}
                    </div>

                    {/* Stats + traits */}
                    <div className="px-3 py-2 border-b border-white/[0.06] text-[10px] text-cyan-500 flex flex-wrap gap-x-4 gap-y-1">
                        {data.stats && Object.entries(data.stats).map(([k, v]) => (
                            <span key={k}><span className="text-cyan-700">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                        ))}
                        {traitEntries.length > 0 && (
                            <div className="w-full mt-1 text-accent-amber/80">
                                {traitEntries.map(([k, v]) => (
                                    <div key={k}><span className="text-accent-amber/50">{k}:</span> {Array.isArray(v) ? v.join(', ') : String(v)}</div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Recent interactions */}
                    <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
                        {loading ? (
                            <div className="text-cyan-700 text-[12px]">Loading memories…</div>
                        ) : (data.interactions && data.interactions.length > 0) ? (
                            data.interactions.map((item, i) => <InteractionRow key={i} item={item} />)
                        ) : (
                            <div className="text-cyan-700 text-[12px]">No stored memories yet. Talk to ATLAS and they'll appear here.</div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

export default MemoryWindow;
