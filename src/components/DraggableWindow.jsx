import React from 'react';

/**
 * Shared draggable overlay window: position, z-index, drag handle header, close button.
 * Used by CAD, Browser, and can wrap Kasa/Printer for consistent behavior.
 */
const DraggableWindow = ({
    id,
    position,
    size,
    zIndex,
    onMouseDown,
    activeDragElement,
    title,
    onClose,
    children,
    className = '',
    headerClassName = 'h-8 bg-gray-900/80 border-b border-cyan-500/20 flex items-center justify-between px-3 cursor-grab active:cursor-grabbing shrink-0',
    showNoiseOverlay = true,
    renderHeader = true
}) => {
    const isActive = activeDragElement === id;
    const defaultPos = id === 'cad' ? { x: typeof window !== 'undefined' ? window.innerWidth / 2 : 400, y: typeof window !== 'undefined' ? window.innerHeight / 2 : 300 } : { x: typeof window !== 'undefined' ? window.innerWidth / 2 - 200 : 300, y: typeof window !== 'undefined' ? window.innerHeight / 2 : 300 };
    const pos = position || defaultPos;
    const sz = size || { w: 400, h: 400 };

    return (
        <div
            id={id}
            className={`absolute flex flex-col transition-all duration-200
                backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl overflow-hidden rounded-2xl
                ${isActive ? 'ring-2 ring-green-500 bg-green-500/10' : ''} ${className}`}
            style={{
                left: pos.x,
                top: pos.y,
                transform: 'translate(-50%, -50%)',
                width: `${sz.w}px`,
                height: `${sz.h}px`,
                pointerEvents: 'auto',
                zIndex: zIndex
            }}
            onMouseDown={(e) => onMouseDown && onMouseDown(e, id)}
        >
            {renderHeader && (
                <div data-drag-handle className={headerClassName}>
                    <span className="text-xs font-bold tracking-widest text-cyan-500/70">{title}</span>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-red-400 hover:bg-red-500/20 p-1 rounded transition-colors"
                    >
                        ✕
                    </button>
                </div>
            )}
            {showNoiseOverlay && (
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10" />
            )}
            <div className={`relative z-20 flex-1 min-h-0 ${!renderHeader ? 'w-full h-full' : ''}`}>
                {children}
            </div>
        </div>
    );
};

export default DraggableWindow;
